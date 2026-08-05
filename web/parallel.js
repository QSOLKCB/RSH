import { createParallelFrenetGpuRunner } from "./parallel-gpu.js";
import {
  PARALLEL_GATES,
  ParallelResidualGateError,
  assertResidualGates,
  createRejectedParallelSidecar,
  residualSnapshot,
} from "./parallel-evidence.js";

const WARMUP_RUNS = 2;
const MEASURED_RUNS = 7;
const MINIMUM_SPEEDUP_SAMPLES = 4097;
const GATES = PARALLEL_GATES;
const decoder = new TextDecoder("utf-8");

function requireElement(id, constructor) {
  const element = document.getElementById(id);
  if (!(element instanceof constructor)) {
    throw new Error(`The parallel laboratory is missing a valid #${id} element`);
  }
  return element;
}

const form = requireElement("controls", HTMLFormElement);
const runButton = requireElement("run", HTMLButtonElement);
const downloadButton = requireElement("download", HTMLButtonElement);
const fields = {
  samples: requireElement("samples", HTMLSelectElement),
  kappaFraction: requireElement("kappa-fraction", HTMLInputElement),
  tauFloor: requireElement("tau-floor", HTMLInputElement),
  tauAmplitude: requireElement("tau-amplitude", HTMLInputElement),
};
const labels = {
  kappaFraction: requireElement("kappa-value", HTMLOutputElement),
  tauFloor: requireElement("tau-floor-value", HTMLOutputElement),
  tauAmplitude: requireElement("tau-amplitude-value", HTMLOutputElement),
};
const output = {
  status: requireElement("status", HTMLElement),
  message: requireElement("message", HTMLElement),
  adapter: requireElement("adapter", HTMLElement),
  scanPasses: requireElement("scan-passes", HTMLElement),
  position: requireElement("res-position", HTMLElement),
  frame: requireElement("res-frame", HTMLElement),
  schedule: requireElement("res-schedule", HTMLElement),
  norm: requireElement("res-norm", HTMLElement),
  orthogonality: requireElement("res-orthogonality", HTMLElement),
  wasmMedian: requireElement("wasm-median", HTMLElement),
  gpuMedian: requireElement("gpu-median", HTMLElement),
  speedup: requireElement("speedup", HTMLElement),
  claim: requireElement("claim", HTMLElement),
};

const state = {
  wasm: null,
  gpu: null,
  sidecar: null,
};

function currentConfig() {
  const samples = Number(fields.samples.value);
  const kappaFraction = Number(fields.kappaFraction.value);
  const tauFloor = Number(fields.tauFloor.value);
  const tauAmplitude = Number(fields.tauAmplitude.value);
  if (!Number.isInteger(samples) || samples < 3 || samples % 2 === 0) {
    throw new Error("Samples must be an odd integer of at least three");
  }
  if (![kappaFraction, tauFloor, tauAmplitude].every(Number.isFinite)) {
    throw new Error("Parallel path controls must be finite");
  }
  if (tauFloor <= 0 || tauFloor + 2 * tauAmplitude >= 1) {
    throw new Error("The complete torsion schedule must remain inside (0, 1)");
  }
  return {
    samples,
    s0: 0,
    s1: 4,
    kappaFraction,
    tauFloor,
    tauAmplitude,
  };
}

function syncLabels() {
  labels.kappaFraction.textContent = Number(fields.kappaFraction.value).toFixed(2);
  labels.tauFloor.textContent = Number(fields.tauFloor.value).toFixed(2);
  labels.tauAmplitude.textContent = Number(fields.tauAmplitude.value).toFixed(2);
}

async function instantiateWasm(url) {
  const response = await fetch(url, { cache: "no-cache" });
  if (!response.ok) throw new Error(`Parallel WASM request failed with HTTP ${response.status}`);
  if (WebAssembly.instantiateStreaming) {
    try {
      return (await WebAssembly.instantiateStreaming(response.clone(), {})).instance;
    } catch (error) {
      console.info("Streaming WASM compilation unavailable; using ArrayBuffer fallback.", error);
    }
  }
  return (await WebAssembly.instantiate(await response.arrayBuffer(), {})).instance;
}

function validateExports(exports) {
  for (const name of [
    "memory",
    "rsh_parallel_abi_version",
    "rsh_parallel_run",
    "rsh_parallel_output_ptr",
    "rsh_parallel_output_len",
  ]) {
    if (!(name in exports)) throw new Error(`Parallel WASM export is missing: ${name}`);
  }
  if (Number(exports.rsh_parallel_abi_version()) !== 1) {
    throw new Error("Unsupported parallel Frenet WASM ABI");
  }
}

function readPayload() {
  const exports = state.wasm.exports;
  const pointer = Number(exports.rsh_parallel_output_ptr());
  const length = Number(exports.rsh_parallel_output_len());
  if (!Number.isSafeInteger(pointer) || pointer < 0 || !Number.isSafeInteger(length) || length < 1) {
    throw new Error("Parallel WASM returned an invalid output buffer");
  }
  const memory = exports.memory.buffer;
  if (pointer > memory.byteLength || length > memory.byteLength - pointer) {
    throw new Error("Parallel WASM output span exceeds linear memory");
  }
  return JSON.parse(decoder.decode(new Uint8Array(memory, pointer, length)));
}

function runWasm(config) {
  const started = performance.now();
  const status = Number(state.wasm.exports.rsh_parallel_run(
    config.samples,
    config.s0,
    config.s1,
    config.kappaFraction,
    config.tauFloor,
    config.tauAmplitude,
  ));
  const payload = readPayload();
  const elapsedMilliseconds = performance.now() - started;
  if (status === 2 || payload.schema === "RSH-FRENET-PARALLEL-ERROR-V1") {
    throw new Error(payload.message || "The parallel path configuration was rejected");
  }
  if (payload.schema !== "RSH-FRENET-PARALLEL-RUN-V1") {
    throw new Error(`Unexpected parallel path schema: ${payload.schema}`);
  }
  if (status !== 0 || !payload.report.pass_all) {
    throw new Error("The f64 parallel-prefix report did not satisfy its contract");
  }
  return { payload, elapsedMilliseconds };
}

function median(values) {
  const sorted = [...values].sort((left, right) => left - right);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0
    ? 0.5 * (sorted[middle - 1] + sorted[middle])
    : sorted[middle];
}

function scientific(value) {
  return Number(value).toExponential(3);
}

function milliseconds(value) {
  return `${Number(value).toFixed(3)} ms`;
}

function clearEvidence() {
  state.sidecar = null;
  downloadButton.disabled = true;
  output.scanPasses.textContent = "—";
  output.position.textContent = "—";
  output.frame.textContent = "—";
  output.schedule.textContent = "—";
  output.norm.textContent = "—";
  output.orthogonality.textContent = "—";
  output.wasmMedian.textContent = "—";
  output.gpuMedian.textContent = "—";
  output.speedup.textContent = "—";
  output.claim.textContent = "NONE";
}

function renderResiduals(result) {
  output.position.textContent = scientific(result.maxPosition);
  output.frame.textContent = scientific(result.maxFrame);
  output.schedule.textContent = scientific(result.maxSchedule);
  output.norm.textContent = scientific(result.maxFrameNorm);
  output.orthogonality.textContent = scientific(result.maxFrameOrthogonality);
  output.scanPasses.textContent = String(result.metadata.scan_passes);
}

async function runBenchmark() {
  if (!state.wasm) {
    output.message.textContent = "The parallel WASM module is still loading.";
    return;
  }

  clearEvidence();
  runButton.disabled = true;
  output.status.textContent = "RUNNING";
  output.status.dataset.kind = "";
  output.message.textContent = "Validating controls and warming the f64 Rust/WASM parallel reference…";

  let rejectionConfig = null;
  let oracle = null;
  const wasmTimings = [];
  const gpuTimings = [];
  let wasmMedian = null;

  try {
    const config = currentConfig();
    rejectionConfig = config;
    for (let index = 0; index < WARMUP_RUNS; index += 1) {
      oracle = runWasm(config).payload;
    }
    for (let index = 0; index < MEASURED_RUNS; index += 1) {
      const result = runWasm(config);
      oracle = result.payload;
      wasmTimings.push(result.elapsedMilliseconds);
    }
    wasmMedian = median(wasmTimings);
    output.wasmMedian.textContent = milliseconds(wasmMedian);
    output.scanPasses.textContent = String(oracle.report.scan_passes);

    if (!state.gpu?.available) {
      output.status.textContent = "WASM FALLBACK";
      output.status.dataset.kind = "fallback";
      output.adapter.textContent = state.gpu?.reason || "WebGPU unavailable";
      output.message.textContent = "The f64 parallel contract passed, but no real GPU benchmark can be claimed.";
      return;
    }

    output.adapter.textContent = state.gpu.metadata.adapter;
    output.message.textContent = "Warming the real WebGPU prefix scan and readback path…";
    for (let index = 0; index < WARMUP_RUNS; index += 1) {
      const result = await state.gpu.run(config, oracle);
      assertResidualGates(result, "warm-up", index + 1, GATES);
    }

    let gpuResult = null;
    for (let index = 0; index < MEASURED_RUNS; index += 1) {
      gpuResult = await state.gpu.run(config, oracle);
      assertResidualGates(gpuResult, "measured", index + 1, GATES);
      gpuTimings.push(gpuResult.elapsedMilliseconds);
    }

    const gpuMedian = median(gpuTimings);
    const observedSpeedup = wasmMedian / gpuMedian;
    const speedupClaim = config.samples >= MINIMUM_SPEEDUP_SAMPLES && observedSpeedup > 1;

    renderResiduals(gpuResult);
    output.gpuMedian.textContent = milliseconds(gpuMedian);
    output.speedup.textContent = `${observedSpeedup.toFixed(3)}×`;
    output.claim.textContent = speedupClaim ? "OBSERVED DEVICE SPEEDUP" : "NO SPEEDUP CLAIM";
    output.status.textContent = "PARALLEL PATH PASS";
    output.status.dataset.kind = "pass";

    state.sidecar = {
      schema: "RSH-WEBGPU-FRENET-PARALLEL-BENCHMARK-V1",
      status: "PASS",
      parallel_contract: oracle.parallel_contract,
      interval_policy: oracle.interval_policy,
      scan_policy: oracle.scan_policy,
      model: oracle.model,
      model_version: oracle.model_version,
      configuration: config,
      metadata: gpuResult.metadata,
      residuals: residualSnapshot(gpuResult),
      gates: GATES,
      benchmark: {
        warmup_runs: WARMUP_RUNS,
        measured_runs: MEASURED_RUNS,
        wasm_end_to_end_milliseconds: wasmTimings,
        gpu_end_to_end_readback_milliseconds: gpuTimings,
        wasm_median_milliseconds: wasmMedian,
        gpu_median_milliseconds: gpuMedian,
        observed_speedup: observedSpeedup,
        minimum_samples_for_speedup_statement: MINIMUM_SPEEDUP_SAMPLES,
        statistic: "median",
        timing_scope: {
          wasm: "ABI-call-JSON-serialization-memory-read-and-JSON-parse",
          webgpu: gpuResult.metadata.timing_scope,
        },
      },
      actual_gpu_execution: true,
      parallel_scan_execution: true,
      complete_path_readback: true,
      actual_multi_device_execution: false,
      distributed_execution: false,
      speedup_claim: speedupClaim,
      speedup_claim_scope: speedupClaim
        ? "observed adapter, browser runtime, sample count, and end-to-end timing method only"
        : "none",
      universal_speedup_claim: false,
      geometry_receipt_authority: false,
      evidence_note: "The adapter executed the normalized-quaternion f32 SE(3) prefix scan and passed full-path readback gates. Any speedup statement is a local observation, not a universal performance claim or geometry receipt.",
    };
    downloadButton.disabled = false;
    output.message.textContent = speedupClaim
      ? `Conformance passed and this adapter produced an observed ${observedSpeedup.toFixed(3)}× median end-to-end speedup.`
      : "Conformance passed. The timing result does not satisfy the policy for an observed speedup statement.";
  } catch (error) {
    if (
      error instanceof ParallelResidualGateError
      && rejectionConfig
      && oracle
      && Number.isFinite(wasmMedian)
    ) {
      renderResiduals(error.result);
      output.gpuMedian.textContent = gpuTimings.length > 0
        ? milliseconds(median(gpuTimings))
        : `failed ${error.stage} ${error.runIndex}`;
      output.speedup.textContent = "—";
      output.claim.textContent = "REJECTED · NO CLAIM";
      state.sidecar = createRejectedParallelSidecar({
        oracle,
        config: rejectionConfig,
        error,
        gates: GATES,
        warmupRuns: WARMUP_RUNS,
        measuredRuns: MEASURED_RUNS,
        wasmTimings,
        gpuTimings,
        wasmMedian,
        minimumSpeedupSamples: MINIMUM_SPEEDUP_SAMPLES,
      });
      downloadButton.disabled = false;
    } else {
      clearEvidence();
    }
    output.status.textContent = "REJECTED";
    output.status.dataset.kind = "fail";
    output.message.textContent = error instanceof Error ? error.message : String(error);
  } finally {
    runButton.disabled = false;
  }
}

function downloadSidecar() {
  if (!state.sidecar) return;
  const blob = new Blob([`${JSON.stringify(state.sidecar, null, 2)}\n`], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = state.sidecar.status === "PASS"
    ? "rsh-webgpu-frenet-parallel-benchmark.json"
    : "rsh-webgpu-frenet-parallel-rejection.json";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

form.addEventListener("input", syncLabels);
form.addEventListener("submit", (event) => {
  event.preventDefault();
  void runBenchmark();
});
downloadButton.addEventListener("click", downloadSidecar);
syncLabels();

try {
  state.wasm = await instantiateWasm("./pkg/rsh_parallel_wasm.wasm");
  validateExports(state.wasm.exports);
  state.gpu = await createParallelFrenetGpuRunner(
    "./wgsl/frenet_parallel_scan.wgsl",
    () => {
      state.gpu = {
        available: false,
        reason: "The WebGPU device was lost; the f64 Rust/WASM parallel reference remains active.",
      };
      clearEvidence();
      output.status.textContent = "DEVICE LOST";
      output.status.dataset.kind = "fallback";
    },
  );
  output.adapter.textContent = state.gpu.available ? state.gpu.metadata.adapter : state.gpu.reason;
  output.status.textContent = "READY";
  output.message.textContent = "The parallel Rust/WASM reference is ready. Run the benchmark to request WebGPU execution.";
} catch (error) {
  clearEvidence();
  output.status.textContent = "LOAD FAILED";
  output.status.dataset.kind = "fail";
  output.message.textContent = error instanceof Error ? error.message : String(error);
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("./sw.js").catch((error) => {
    console.info("Offline cache registration failed.", error);
  });
}
