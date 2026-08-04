import { createFrenetGpuRunner } from "./path-gpu.js";

const SAMPLES = 1025;
const GATES = {
  position: 2e-4,
  frame: 2e-4,
  schedule: 1e-4,
  frameNorm: 2e-6,
  frameOrthogonality: 2e-6,
};
const decoder = new TextDecoder("utf-8");
const canvas = document.getElementById("path-canvas");
const context = canvas.getContext("2d");
const form = document.getElementById("controls");
const runButton = document.getElementById("run");
const downloadButton = document.getElementById("download-sidecar");
const message = document.getElementById("message");
const cpuStatus = document.getElementById("cpu-status");
const gpuStatus = document.getElementById("gpu-status");
const adapterText = document.getElementById("adapter");
const metrics = {
  position: document.getElementById("res-position"),
  frame: document.getElementById("res-frame"),
  schedule: document.getElementById("res-schedule"),
  norm: document.getElementById("res-norm"),
  orthogonality: document.getElementById("res-orthogonality"),
};
const fields = {
  kappaFraction: document.getElementById("kappa-fraction"),
  tauFloor: document.getElementById("tau-floor"),
  tauAmplitude: document.getElementById("tau-amplitude"),
};
const labels = {
  kappaFraction: document.getElementById("kappa-value"),
  tauFloor: document.getElementById("tau-floor-value"),
  tauAmplitude: document.getElementById("tau-amplitude-value"),
};

if (!(canvas instanceof HTMLCanvasElement) || !context || !(form instanceof HTMLFormElement)) {
  throw new Error("The full-path laboratory could not initialize its interface");
}

const state = {
  wasm: null,
  gpu: null,
  payload: null,
  gpuRows: [],
  sidecar: null,
  yaw: -0.65,
  pitch: 0.42,
  dragging: false,
  pointerX: 0,
  pointerY: 0,
};

function config() {
  return {
    samples: SAMPLES,
    s0: 0,
    s1: 4,
    kappaFraction: Number(fields.kappaFraction.value),
    tauFloor: Number(fields.tauFloor.value),
    tauAmplitude: Number(fields.tauAmplitude.value),
  };
}

function syncLabels() {
  labels.kappaFraction.textContent = Number(fields.kappaFraction.value).toFixed(2);
  labels.tauFloor.textContent = Number(fields.tauFloor.value).toFixed(2);
  labels.tauAmplitude.textContent = Number(fields.tauAmplitude.value).toFixed(2);
}

async function instantiateWasm(url) {
  const response = await fetch(url, { cache: "no-cache" });
  if (!response.ok) throw new Error(`WASM request failed with HTTP ${response.status}`);
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
    "rsh_frenet_abi_version",
    "rsh_frenet_run",
    "rsh_frenet_output_ptr",
    "rsh_frenet_output_len",
  ]) {
    if (!(name in exports)) throw new Error(`Numerical WASM export is missing: ${name}`);
  }
  if (Number(exports.rsh_frenet_abi_version()) !== 1) {
    throw new Error("Unsupported Frenet numerical WASM ABI");
  }
}

function readWasmOutput() {
  const exports = state.wasm.exports;
  const pointer = Number(exports.rsh_frenet_output_ptr());
  const length = Number(exports.rsh_frenet_output_len());
  if (!Number.isInteger(pointer) || pointer < 0 || !Number.isInteger(length) || length < 1) {
    throw new Error("Numerical WASM returned an invalid output buffer");
  }
  return JSON.parse(decoder.decode(new Uint8Array(exports.memory.buffer, pointer, length)));
}

function scientific(value) {
  return Number(value).toExponential(3);
}

function clearGpuResult(text = "NOT RUN") {
  state.gpuRows = [];
  state.sidecar = null;
  downloadButton.disabled = true;
  gpuStatus.textContent = text;
  gpuStatus.dataset.kind = "";
  for (const item of Object.values(metrics)) item.textContent = "—";
}

function runCpuPath(current) {
  const status = Number(state.wasm.exports.rsh_frenet_run(
    current.samples,
    current.s0,
    current.s1,
    current.kappaFraction,
    current.tauFloor,
    current.tauAmplitude,
  ));
  const payload = readWasmOutput();
  if (status === 2 || payload.schema === "RSH-FRENET-PATH-ERROR-V1") {
    throw new Error(payload.message || "The numerical path was rejected");
  }
  if (payload.schema !== "RSH-FRENET-PATH-RUN-V1") {
    throw new Error(`Unexpected numerical path schema: ${payload.schema}`);
  }
  if (!payload.report.pass_all || status !== 0) {
    throw new Error("The f64 numerical path did not satisfy its research contract");
  }
  return payload;
}

function gatePassed(result) {
  return result.maxPosition <= GATES.position
    && result.maxFrame <= GATES.frame
    && result.maxSchedule <= GATES.schedule
    && result.maxFrameNorm <= GATES.frameNorm
    && result.maxFrameOrthogonality <= GATES.frameOrthogonality;
}

async function runLaboratory() {
  if (!state.wasm) {
    message.textContent = "The numerical WASM module is still loading.";
    return;
  }
  const current = config();
  runButton.disabled = true;
  cpuStatus.textContent = "RUNNING";
  cpuStatus.dataset.kind = "";
  clearGpuResult("WAITING");
  message.textContent = "Building the f64 Lie-midpoint path…";

  try {
    state.payload = runCpuPath(current);
    cpuStatus.textContent = "f64 PATH PASS";
    cpuStatus.dataset.kind = "pass";
    message.textContent = `The separately versioned f64 path produced ${SAMPLES} samples. Starting WebGPU readback…`;

    if (!state.gpu?.available) {
      clearGpuResult("WASM FALLBACK");
      gpuStatus.dataset.kind = "fallback";
      adapterText.textContent = state.gpu?.reason || "WebGPU unavailable";
      message.textContent = "The f64 path passed. WebGPU is unavailable, so no GPU claim is made.";
      return;
    }

    gpuStatus.textContent = "RUNNING";
    const result = await state.gpu.run(current, state.payload);
    state.gpuRows = result.rows;
    adapterText.textContent = result.metadata.adapter;
    metrics.position.textContent = scientific(result.maxPosition);
    metrics.frame.textContent = scientific(result.maxFrame);
    metrics.schedule.textContent = scientific(result.maxSchedule);
    metrics.norm.textContent = scientific(result.maxFrameNorm);
    metrics.orthogonality.textContent = scientific(result.maxFrameOrthogonality);

    const passed = gatePassed(result);
    gpuStatus.textContent = passed ? "FULL PATH RESIDUAL PASS" : "DISPLAY ONLY";
    gpuStatus.dataset.kind = passed ? "pass" : "fail";
    state.sidecar = passed ? {
      schema: "RSH-WEBGPU-FRENET-PATH-SIDECAR-V1",
      status: "PASS",
      numerical_contract: state.payload.numerical_contract,
      integrator: state.payload.integrator,
      model: state.payload.model,
      model_version: state.payload.model_version,
      configuration: current,
      metadata: result.metadata,
      residuals: {
        max_position_component_vs_wasm_f64: result.maxPosition,
        max_frame_component_vs_wasm_f64: result.maxFrame,
        max_schedule_component_vs_wasm_f64: result.maxSchedule,
        max_frame_norm_error: result.maxFrameNorm,
        max_frame_orthogonality_error: result.maxFrameOrthogonality,
      },
      gates: GATES,
      actual_gpu_execution: true,
      full_path_execution: true,
      execution_model: "single-invocation sequential path recurrence",
      speedup_claim: false,
      geometry_receipt_authority: false,
      evidence_note: "The adapter executed the complete f32 path recurrence and read it back. The separately versioned f64 Rust/WASM path remains the numerical reference, and the canonical rsh-core geometry receipt remains unchanged.",
    } : null;
    downloadButton.disabled = !passed;
    message.textContent = passed
      ? "The adapter executed and returned the complete f32 path inside every published residual gate. This is correctness evidence, not a speedup claim."
      : "The adapter executed the full path but exceeded at least one gate. No sidecar may be exported.";
  } catch (error) {
    cpuStatus.textContent = "REJECTED";
    cpuStatus.dataset.kind = "fail";
    clearGpuResult("BLOCKED");
    gpuStatus.dataset.kind = "fail";
    message.textContent = error instanceof Error ? error.message : String(error);
  } finally {
    runButton.disabled = false;
  }
}

function project(point, extent) {
  const [x, y, z] = point;
  const cy = Math.cos(state.yaw);
  const sy = Math.sin(state.yaw);
  const cp = Math.cos(state.pitch);
  const sp = Math.sin(state.pitch);
  const rx = cy * x - sy * z;
  const rz = sy * x + cy * z;
  const ry = cp * y - sp * rz;
  const scale = Math.min(canvas.width, canvas.height) * 0.39 / extent;
  return [canvas.width / 2 + rx * scale, canvas.height / 2 - ry * scale];
}

function drawCurve(points, positionOf, stroke, width, dash = []) {
  if (!points.length) return;
  const extent = Math.max(
    1e-9,
    ...points.flatMap((point) => positionOf(point).map(Math.abs)),
  );
  context.beginPath();
  context.setLineDash(dash);
  for (let index = 0; index < points.length; index += 1) {
    const [x, y] = project(positionOf(points[index]), extent);
    if (index === 0) context.moveTo(x, y);
    else context.lineTo(x, y);
  }
  context.strokeStyle = stroke;
  context.lineWidth = width;
  context.stroke();
  context.setLineDash([]);
}

function drawFrame() {
  if (!state.payload?.points?.length) return;
  const midpoint = state.payload.points[Math.floor(state.payload.points.length / 2)];
  const extent = Math.max(
    1e-9,
    ...state.payload.points.flatMap((point) => [Math.abs(point.x), Math.abs(point.y), Math.abs(point.z)]),
  );
  const origin = [midpoint.x, midpoint.y, midpoint.z];
  const vectors = [
    [[midpoint.tx, midpoint.ty, midpoint.tz], "#f4b860", "T"],
    [[midpoint.nx, midpoint.ny, midpoint.nz], "#5fd1c8", "N"],
    [[midpoint.bx, midpoint.by, midpoint.bz], "#d8dde7", "B"],
  ];
  const [ox, oy] = project(origin, extent);
  context.font = "13px ui-monospace, monospace";
  for (const [vector, stroke, label] of vectors) {
    const endpoint = origin.map((value, index) => value + vector[index] * extent * 0.28);
    const [ex, ey] = project(endpoint, extent);
    context.beginPath();
    context.moveTo(ox, oy);
    context.lineTo(ex, ey);
    context.strokeStyle = stroke;
    context.lineWidth = 2;
    context.stroke();
    context.fillStyle = stroke;
    context.fillText(label, ex + 4, ey - 4);
  }
}

function render() {
  context.clearRect(0, 0, canvas.width, canvas.height);
  const gradient = context.createLinearGradient(0, 0, 0, canvas.height);
  gradient.addColorStop(0, "#10151c");
  gradient.addColorStop(1, "#080b0f");
  context.fillStyle = gradient;
  context.fillRect(0, 0, canvas.width, canvas.height);

  if (state.payload?.points) {
    drawCurve(
      state.payload.points,
      (point) => [point.x, point.y, point.z],
      "#f4b860",
      2.4,
    );
  }
  if (state.gpuRows.length) {
    drawCurve(state.gpuRows, (point) => point.position, "#5fd1c8", 1.5, [5, 5]);
  }
  drawFrame();
  requestAnimationFrame(render);
}

function downloadSidecar() {
  if (!state.sidecar) return;
  const blob = new Blob([`${JSON.stringify(state.sidecar, null, 2)}\n`], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "rsh-webgpu-frenet-path-sidecar.json";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

canvas.addEventListener("pointerdown", (event) => {
  state.dragging = true;
  state.pointerX = event.clientX;
  state.pointerY = event.clientY;
  canvas.setPointerCapture(event.pointerId);
});
canvas.addEventListener("pointermove", (event) => {
  if (!state.dragging) return;
  state.yaw += (event.clientX - state.pointerX) * 0.008;
  state.pitch += (event.clientY - state.pointerY) * 0.008;
  state.pointerX = event.clientX;
  state.pointerY = event.clientY;
});
canvas.addEventListener("pointerup", (event) => {
  state.dragging = false;
  canvas.releasePointerCapture(event.pointerId);
});

form.addEventListener("input", syncLabels);
form.addEventListener("submit", (event) => {
  event.preventDefault();
  void runLaboratory();
});
downloadButton.addEventListener("click", downloadSidecar);
syncLabels();
requestAnimationFrame(render);

try {
  state.wasm = await instantiateWasm("./pkg/rsh_numerics_wasm.wasm");
  validateExports(state.wasm.exports);
  cpuStatus.textContent = "READY";
  state.gpu = await createFrenetGpuRunner("./wgsl/frenet_path.wgsl", () => {
    state.gpu = {
      available: false,
      reason: "The WebGPU device was lost; the f64 Rust/WASM path remains active.",
    };
    clearGpuResult("DEVICE LOST");
  });
  adapterText.textContent = state.gpu.available ? state.gpu.metadata.adapter : state.gpu.reason;
  void runLaboratory();
} catch (error) {
  cpuStatus.textContent = "LOAD FAILED";
  cpuStatus.dataset.kind = "fail";
  message.textContent = error instanceof Error ? error.message : String(error);
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("./sw.js").catch((error) => {
    console.info("Offline cache registration failed.", error);
  });
}
