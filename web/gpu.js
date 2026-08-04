const WORKGROUP_SIZE = 64;
const PARAM_BYTES = 48;
const FLOATS_PER_SAMPLE = 2;

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
  view.setUint32(0, oracle.samples, true);
  view.setFloat32(16, config.s0, true);
  view.setFloat32(20, config.s1, true);
  view.setFloat32(24, config.kappaFraction, true);
  view.setFloat32(28, config.tauFloor, true);
  view.setFloat32(32, config.tauAmplitude, true);
  view.setFloat32(36, Number(oracle.psi), true);
  view.setFloat32(40, Number(oracle.kappa_bound), true);
  return bytes;
}

function residuals(field, oracle) {
  let maxKappa = 0;
  let maxTau = 0;
  const rows = new Array(oracle.points.length);

  for (let index = 0; index < oracle.points.length; index += 1) {
    const gpuKappa = Number(field[index * FLOATS_PER_SAMPLE]);
    const gpuTau = Number(field[index * FLOATS_PER_SAMPLE + 1]);
    const reference = oracle.points[index];
    if (!Number.isFinite(gpuKappa) || !Number.isFinite(gpuTau)) {
      throw new Error(`WebGPU returned a non-finite schedule value at index ${index}`);
    }
    maxKappa = Math.max(maxKappa, Math.abs(gpuKappa - Number(reference.kappa)));
    maxTau = Math.max(maxTau, Math.abs(gpuTau - Number(reference.tau)));
    rows[index] = {
      index,
      p: Number(reference.p),
      s: Number(reference.s),
      kappa: gpuKappa,
      tau: gpuTau,
    };
  }

  return {
    rows,
    maxKappa,
    maxTau,
    maximum: Math.max(maxKappa, maxTau),
  };
}

export async function createGpuScheduleRunner(shaderUrl, onDeviceLost = () => {}) {
  if (!("gpu" in navigator)) {
    return {
      available: false,
      reason: "WebGPU is unavailable; the verified Rust/WASM path remains active.",
    };
  }

  const adapter = await navigator.gpu.requestAdapter({ powerPreference: "high-performance" });
  if (!adapter) {
    return {
      available: false,
      reason: "No WebGPU adapter was granted; the verified Rust/WASM path remains active.",
    };
  }

  const info = await readAdapterInfo(adapter);
  const device = await adapter.requestDevice();
  device.lost.then((lost) => {
    onDeviceLost(lost);
  });

  const response = await fetch(shaderUrl, { cache: "no-cache" });
  if (!response.ok) {
    throw new Error(`WGSL request failed with HTTP ${response.status}`);
  }
  const source = await response.text();
  const module = device.createShaderModule({
    label: "RSH κ/τ schedule field",
    code: source,
  });
  const compilation = await module.getCompilationInfo();
  const errors = compilation.messages.filter((message) => message.type === "error");
  if (errors.length > 0) {
    throw new Error(errors.map((message) => message.message).join("; "));
  }

  const pipeline = await device.createComputePipelineAsync({
    label: "RSH Phase 4 schedule pipeline",
    layout: "auto",
    compute: {
      module,
      entryPoint: "main",
    },
  });

  const metadata = {
    backend: "webgpu",
    adapter: adapterDescription(info),
    device: device.label || "WebGPU logical device",
    wgsl_entry: "main",
    workgroup_size: WORKGROUP_SIZE,
    f_precision: "f32",
    max_compute_workgroups_per_dimension: device.limits.maxComputeWorkgroupsPerDimension,
    feature_count: device.features.size,
  };

  return {
    available: true,
    metadata,
    async run(config, oracle) {
      if (!oracle || oracle.schema !== "RSH-SCHEDULE-RUN-V1") {
        throw new Error("WebGPU requires the rsh-core f64 schedule oracle");
      }
      if (!Number.isInteger(oracle.samples) || oracle.samples < 2) {
        throw new Error("The schedule oracle returned an invalid sample count");
      }

      const outputBytes = oracle.samples * FLOATS_PER_SAMPLE * Float32Array.BYTES_PER_ELEMENT;
      const paramsBuffer = device.createBuffer({
        label: "RSH schedule parameters",
        size: PARAM_BYTES,
        usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
      });
      const outputBuffer = device.createBuffer({
        label: "RSH schedule output",
        size: outputBytes,
        usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC,
      });
      const readbackBuffer = device.createBuffer({
        label: "RSH schedule readback",
        size: outputBytes,
        usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ,
      });

      try {
        device.queue.writeBuffer(paramsBuffer, 0, makeParams(config, oracle));
        const bindGroup = device.createBindGroup({
          label: "RSH schedule bindings",
          layout: pipeline.getBindGroupLayout(0),
          entries: [
            { binding: 0, resource: { buffer: paramsBuffer } },
            { binding: 1, resource: { buffer: outputBuffer } },
          ],
        });

        const encoder = device.createCommandEncoder({ label: "RSH schedule encoder" });
        const pass = encoder.beginComputePass({ label: "RSH schedule compute" });
        pass.setPipeline(pipeline);
        pass.setBindGroup(0, bindGroup);
        pass.dispatchWorkgroups(Math.ceil(oracle.samples / WORKGROUP_SIZE));
        pass.end();
        encoder.copyBufferToBuffer(outputBuffer, 0, readbackBuffer, 0, outputBytes);
        device.queue.submit([encoder.finish()]);

        await readbackBuffer.mapAsync(GPUMapMode.READ);
        const snapshot = readbackBuffer.getMappedRange().slice(0);
        const result = residuals(new Float32Array(snapshot), oracle);
        readbackBuffer.unmap();
        return {
          ...result,
          metadata: {
            ...metadata,
            grid_samples: oracle.samples,
          },
        };
      } finally {
        paramsBuffer.destroy();
        outputBuffer.destroy();
        readbackBuffer.destroy();
      }
    },
  };
}
