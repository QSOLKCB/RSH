const PARAM_BYTES = 64;
const TRANSFORM_BYTES = 32;
const FLOATS_PER_POINT = 16;
const WORKGROUP_SIZE = 64;

function adapterDescription(info) {
  const parts = [info?.vendor, info?.architecture, info?.device, info?.description]
    .filter((value) => typeof value === "string" && value.trim().length > 0);
  return parts.length > 0 ? parts.join(" · ") : "WebGPU adapter details unavailable";
}

async function readAdapterInfo(adapter) {
  if (adapter.info) return adapter.info;
  if (typeof adapter.requestAdapterInfo === "function") {
    try {
      return await adapter.requestAdapterInfo();
    } catch (error) {
      console.info("WebGPU adapter information was not exposed.", error);
    }
  }
  return {};
}

function makeParams(config, samples, offset) {
  const bytes = new ArrayBuffer(PARAM_BYTES);
  const view = new DataView(bytes);
  view.setUint32(0, samples, true);
  view.setUint32(4, offset, true);
  view.setFloat32(16, config.s0, true);
  view.setFloat32(20, config.s1, true);
  view.setFloat32(24, config.kappaFraction, true);
  view.setFloat32(28, config.tauFloor, true);
  view.setFloat32(32, config.tauAmplitude, true);
  view.setFloat32(36, Math.sqrt(2 + Math.sqrt(5)), true);
  view.setFloat32(40, Math.sqrt(2) - 1, true);
  return bytes;
}

function dot(left, right) {
  return left[0] * right[0] + left[1] * right[1] + left[2] * right[2];
}

function norm(vector) {
  return Math.hypot(vector[0], vector[1], vector[2]);
}

function maxAbs(left, right) {
  return Math.max(
    Math.abs(left[0] - right[0]),
    Math.abs(left[1] - right[1]),
    Math.abs(left[2] - right[2]),
  );
}

function unpack(field, index) {
  const offset = index * FLOATS_PER_POINT;
  return {
    index,
    position: [field[offset], field[offset + 1], field[offset + 2]],
    kappa: field[offset + 3],
    tangent: [field[offset + 4], field[offset + 5], field[offset + 6]],
    tau: field[offset + 7],
    normal: [field[offset + 8], field[offset + 9], field[offset + 10]],
    p: field[offset + 11],
    binormal: [field[offset + 12], field[offset + 13], field[offset + 14]],
    s: field[offset + 15],
  };
}

function referenceVector(point, prefix) {
  return [point[`${prefix}x`], point[`${prefix}y`], point[`${prefix}z`]];
}

function calculateResiduals(field, oracle) {
  let maxPosition = 0;
  let maxFrame = 0;
  let maxSchedule = 0;
  let maxFrameNorm = 0;
  let maxFrameOrthogonality = 0;
  const rows = new Array(oracle.points.length);

  for (let index = 0; index < oracle.points.length; index += 1) {
    const actual = unpack(field, index);
    const expected = oracle.points[index];
    const values = [
      ...actual.position,
      actual.kappa,
      ...actual.tangent,
      actual.tau,
      ...actual.normal,
      actual.p,
      ...actual.binormal,
      actual.s,
    ];
    if (!values.every(Number.isFinite)) {
      throw new Error(`Parallel WebGPU returned a non-finite value at index ${index}`);
    }
    maxPosition = Math.max(
      maxPosition,
      maxAbs(actual.position, [expected.x, expected.y, expected.z]),
    );
    maxFrame = Math.max(
      maxFrame,
      maxAbs(actual.tangent, referenceVector(expected, "t")),
      maxAbs(actual.normal, referenceVector(expected, "n")),
      maxAbs(actual.binormal, referenceVector(expected, "b")),
    );
    maxSchedule = Math.max(
      maxSchedule,
      Math.abs(actual.kappa - Number(expected.kappa)),
      Math.abs(actual.tau - Number(expected.tau)),
    );
    for (const vector of [actual.tangent, actual.normal, actual.binormal]) {
      maxFrameNorm = Math.max(maxFrameNorm, Math.abs(norm(vector) - 1));
    }
    maxFrameOrthogonality = Math.max(
      maxFrameOrthogonality,
      Math.abs(dot(actual.tangent, actual.normal)),
      Math.abs(dot(actual.tangent, actual.binormal)),
      Math.abs(dot(actual.normal, actual.binormal)),
    );
    rows[index] = actual;
  }

  return {
    rows,
    maxPosition,
    maxFrame,
    maxSchedule,
    maxFrameNorm,
    maxFrameOrthogonality,
  };
}

function createParamsBuffer(device, config, samples, offset, label) {
  const buffer = device.createBuffer({
    label,
    size: PARAM_BYTES,
    usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
  });
  device.queue.writeBuffer(buffer, 0, makeParams(config, samples, offset));
  return buffer;
}

export async function createParallelFrenetGpuRunner(shaderUrl, onDeviceLost = () => {}) {
  if (!("gpu" in navigator)) {
    return {
      available: false,
      reason: "WebGPU is unavailable; the f64 Rust/WASM parallel reference remains active.",
    };
  }

  const adapter = await navigator.gpu.requestAdapter({ powerPreference: "high-performance" });
  if (!adapter) {
    return {
      available: false,
      reason: "No WebGPU adapter was granted; the f64 Rust/WASM parallel reference remains active.",
    };
  }

  const info = await readAdapterInfo(adapter);
  const device = await adapter.requestDevice();
  device.lost.then(onDeviceLost);

  const response = await fetch(shaderUrl, { cache: "no-cache" });
  if (!response.ok) throw new Error(`Parallel WGSL request failed with HTTP ${response.status}`);
  const module = device.createShaderModule({
    label: "RSH parallel Frenet scan module",
    code: await response.text(),
  });
  const compilation = await module.getCompilationInfo();
  const errors = compilation.messages.filter((message) => message.type === "error");
  if (errors.length > 0) {
    throw new Error(errors.map((message) => message.message).join("; "));
  }

  const bindGroupLayout = device.createBindGroupLayout({
    label: "RSH parallel Frenet bindings",
    entries: [
      { binding: 0, visibility: GPUShaderStage.COMPUTE, buffer: { type: "uniform" } },
      { binding: 1, visibility: GPUShaderStage.COMPUTE, buffer: { type: "read-only-storage" } },
      { binding: 2, visibility: GPUShaderStage.COMPUTE, buffer: { type: "storage" } },
      { binding: 3, visibility: GPUShaderStage.COMPUTE, buffer: { type: "storage" } },
      { binding: 4, visibility: GPUShaderStage.COMPUTE, buffer: { type: "storage" } },
    ],
  });
  const layout = device.createPipelineLayout({ bindGroupLayouts: [bindGroupLayout] });
  const pipeline = async (entryPoint) => device.createComputePipelineAsync({
    label: `RSH parallel Frenet ${entryPoint}`,
    layout,
    compute: { module, entryPoint },
  });
  const [buildPipeline, scanPipeline, centrePipeline, emitPipeline] = await Promise.all([
    pipeline("build_local"),
    pipeline("scan_step"),
    pipeline("capture_centre"),
    pipeline("emit_path"),
  ]);

  const metadata = {
    backend: "webgpu",
    adapter: adapterDescription(info),
    device: device.label || "WebGPU logical device",
    browser: navigator.userAgent,
    workgroup_size: WORKGROUP_SIZE,
    transform_bytes: TRANSFORM_BYTES,
    rotation_representation: "normalized-quaternion-xyzw-f32-v1",
    execution_model: "multi-pass inclusive SE(3) prefix scan",
    parallel_contract: "RSH-FRENET-PARALLEL-V1",
    scan_policy: "hillis-steele-inclusive-se3-v1",
    actual_gpu_execution: true,
    distributed_execution: false,
    geometry_receipt_authority: false,
  };

  function bind(params, source, target, centre, output, label) {
    return device.createBindGroup({
      label,
      layout: bindGroupLayout,
      entries: [
        { binding: 0, resource: { buffer: params } },
        { binding: 1, resource: { buffer: source } },
        { binding: 2, resource: { buffer: target } },
        { binding: 3, resource: { buffer: centre } },
        { binding: 4, resource: { buffer: output } },
      ],
    });
  }

  return {
    available: true,
    metadata,
    async run(config, oracle) {
      if (!oracle || oracle.schema !== "RSH-FRENET-PARALLEL-RUN-V1") {
        throw new Error("Parallel WebGPU requires the f64 parallel-prefix oracle");
      }
      const samples = oracle.points?.length;
      if (!Number.isInteger(samples) || samples < 3 || samples % 2 === 0) {
        throw new Error("The parallel oracle returned an invalid sample count");
      }
      if (!Number.isInteger(config.samples) || config.samples !== samples) {
        throw new Error(
          `Parallel WebGPU samples (${config.samples}) do not match the oracle (${samples})`,
        );
      }

      const started = performance.now();
      const transformBytes = samples * TRANSFORM_BYTES;
      const outputBytes = samples * FLOATS_PER_POINT * Float32Array.BYTES_PER_ELEMENT;
      const transformA = device.createBuffer({
        label: "RSH parallel transforms A",
        size: transformBytes,
        usage: GPUBufferUsage.STORAGE,
      });
      const transformB = device.createBuffer({
        label: "RSH parallel transforms B",
        size: transformBytes,
        usage: GPUBufferUsage.STORAGE,
      });
      const centreBuffer = device.createBuffer({
        label: "RSH parallel centre",
        size: 16,
        usage: GPUBufferUsage.STORAGE,
      });
      const outputBuffer = device.createBuffer({
        label: "RSH parallel path output",
        size: outputBytes,
        usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC,
      });
      const readbackBuffer = device.createBuffer({
        label: "RSH parallel path readback",
        size: outputBytes,
        usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ,
      });
      const paramsBuffers = [];
      let mapped = false;

      try {
        const workgroups = Math.ceil(samples / WORKGROUP_SIZE);
        const encoder = device.createCommandEncoder({ label: "RSH parallel Frenet encoder" });

        const buildParams = createParamsBuffer(
          device,
          config,
          samples,
          0,
          "RSH parallel build parameters",
        );
        paramsBuffers.push(buildParams);
        {
          const pass = encoder.beginComputePass({ label: "RSH parallel interval construction" });
          pass.setPipeline(buildPipeline);
          pass.setBindGroup(
            0,
            bind(buildParams, transformB, transformA, centreBuffer, outputBuffer, "build bindings"),
          );
          pass.dispatchWorkgroups(workgroups);
          pass.end();
        }

        let current = transformA;
        let spare = transformB;
        let offset = 1;
        let scanPasses = 0;
        while (offset < samples) {
          const scanParams = createParamsBuffer(
            device,
            config,
            samples,
            offset,
            `RSH parallel scan parameters ${offset}`,
          );
          paramsBuffers.push(scanParams);
          const pass = encoder.beginComputePass({ label: `RSH parallel scan offset ${offset}` });
          pass.setPipeline(scanPipeline);
          pass.setBindGroup(
            0,
            bind(scanParams, current, spare, centreBuffer, outputBuffer, `scan bindings ${offset}`),
          );
          pass.dispatchWorkgroups(workgroups);
          pass.end();
          [current, spare] = [spare, current];
          offset *= 2;
          scanPasses += 1;
        }

        const finishParams = createParamsBuffer(
          device,
          config,
          samples,
          0,
          "RSH parallel emit parameters",
        );
        paramsBuffers.push(finishParams);
        {
          const pass = encoder.beginComputePass({ label: "RSH parallel capture midpoint" });
          pass.setPipeline(centrePipeline);
          pass.setBindGroup(
            0,
            bind(finishParams, current, spare, centreBuffer, outputBuffer, "centre bindings"),
          );
          pass.dispatchWorkgroups(1);
          pass.end();
        }
        {
          const pass = encoder.beginComputePass({ label: "RSH parallel path emission" });
          pass.setPipeline(emitPipeline);
          pass.setBindGroup(
            0,
            bind(finishParams, current, spare, centreBuffer, outputBuffer, "emit bindings"),
          );
          pass.dispatchWorkgroups(workgroups);
          pass.end();
        }

        encoder.copyBufferToBuffer(outputBuffer, 0, readbackBuffer, 0, outputBytes);
        device.queue.submit([encoder.finish()]);
        await readbackBuffer.mapAsync(GPUMapMode.READ);
        mapped = true;
        const snapshot = readbackBuffer.getMappedRange().slice(0);
        const result = calculateResiduals(new Float32Array(snapshot), oracle);
        const elapsedMilliseconds = performance.now() - started;
        return {
          ...result,
          elapsedMilliseconds,
          metadata: {
            ...metadata,
            grid_samples: samples,
            intervals: samples - 1,
            scan_passes: scanPasses,
            dispatch_workgroups_per_pass: workgroups,
            command_passes: scanPasses + 3,
            timing_scope: "buffer-allocation-command-encoding-submit-readback",
          },
        };
      } finally {
        if (mapped) readbackBuffer.unmap();
        for (const buffer of paramsBuffers) buffer.destroy();
        transformA.destroy();
        transformB.destroy();
        centreBuffer.destroy();
        outputBuffer.destroy();
        readbackBuffer.destroy();
      }
    },
  };
}
