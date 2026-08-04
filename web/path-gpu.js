const PARAM_BYTES = 48;
const FLOATS_PER_POINT = 16;

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

function makeParams(config, oracle) {
  const bytes = new ArrayBuffer(PARAM_BYTES);
  const view = new DataView(bytes);
  view.setUint32(0, oracle.points.length, true);
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

function residuals(field, oracle) {
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
      throw new Error(`WebGPU returned a non-finite path value at index ${index}`);
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

export async function createFrenetGpuRunner(shaderUrl, onDeviceLost = () => {}) {
  if (!("gpu" in navigator)) {
    return {
      available: false,
      reason: "WebGPU is unavailable; the f64 Rust/WASM research path remains active.",
    };
  }

  const adapter = await navigator.gpu.requestAdapter({ powerPreference: "high-performance" });
  if (!adapter) {
    return {
      available: false,
      reason: "No WebGPU adapter was granted; the f64 Rust/WASM research path remains active.",
    };
  }

  const info = await readAdapterInfo(adapter);
  const device = await adapter.requestDevice();
  device.lost.then(onDeviceLost);

  const response = await fetch(shaderUrl, { cache: "no-cache" });
  if (!response.ok) {
    throw new Error(`WGSL request failed with HTTP ${response.status}`);
  }
  const source = await response.text();
  const module = device.createShaderModule({
    label: "RSH full Frenet path research",
    code: source,
  });
  const compilation = await module.getCompilationInfo();
  const errors = compilation.messages.filter((message) => message.type === "error");
  if (errors.length > 0) {
    throw new Error(errors.map((message) => message.message).join("; "));
  }

  const pipeline = await device.createComputePipelineAsync({
    label: "RSH full Frenet path pipeline",
    layout: "auto",
    compute: { module, entryPoint: "main" },
  });

  const metadata = {
    backend: "webgpu",
    adapter: adapterDescription(info),
    device: device.label || "WebGPU logical device",
    wgsl_entry: "main",
    workgroup_size: 1,
    dispatch_workgroups: 1,
    execution_model: "single-invocation sequential path recurrence",
    full_path_execution: true,
    f_precision: "f32",
    speedup_claim: false,
    geometry_receipt_authority: false,
  };

  return {
    available: true,
    metadata,
    async run(config, oracle) {
      if (!oracle || oracle.schema !== "RSH-FRENET-PATH-RUN-V1") {
        throw new Error("WebGPU requires the separately versioned f64 Frenet path oracle");
      }
      const samples = oracle.points?.length;
      if (!Number.isInteger(samples) || samples < 3 || samples % 2 === 0) {
        throw new Error("The f64 path oracle returned an invalid sample count");
      }

      const outputBytes = samples * FLOATS_PER_POINT * Float32Array.BYTES_PER_ELEMENT;
      const paramsBuffer = device.createBuffer({
        label: "RSH full-path parameters",
        size: PARAM_BYTES,
        usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
      });
      const outputBuffer = device.createBuffer({
        label: "RSH full-path output",
        size: outputBytes,
        usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC,
      });
      const readbackBuffer = device.createBuffer({
        label: "RSH full-path readback",
        size: outputBytes,
        usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ,
      });

      try {
        device.queue.writeBuffer(paramsBuffer, 0, makeParams(config, oracle));
        const bindGroup = device.createBindGroup({
          label: "RSH full-path bindings",
          layout: pipeline.getBindGroupLayout(0),
          entries: [
            { binding: 0, resource: { buffer: paramsBuffer } },
            { binding: 1, resource: { buffer: outputBuffer } },
          ],
        });
        const encoder = device.createCommandEncoder({ label: "RSH full-path encoder" });
        const pass = encoder.beginComputePass({ label: "RSH full-path compute" });
        pass.setPipeline(pipeline);
        pass.setBindGroup(0, bindGroup);
        pass.dispatchWorkgroups(1);
        pass.end();
        encoder.copyBufferToBuffer(outputBuffer, 0, readbackBuffer, 0, outputBytes);
        device.queue.submit([encoder.finish()]);

        await readbackBuffer.mapAsync(GPUMapMode.READ);
        const snapshot = readbackBuffer.getMappedRange().slice(0);
        const result = residuals(new Float32Array(snapshot), oracle);
        readbackBuffer.unmap();
        return {
          ...result,
          metadata: { ...metadata, grid_samples: samples },
        };
      } finally {
        paramsBuffer.destroy();
        outputBuffer.destroy();
        readbackBuffer.destroy();
      }
    },
  };
}
