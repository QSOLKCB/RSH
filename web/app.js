import { createGpuScheduleRunner } from "./gpu.js";

const textDecoder = new TextDecoder("utf-8");
const GPU_GRID_SAMPLES = 4096;
const GPU_RESIDUAL_THRESHOLD = 1e-4;

const canvas = document.getElementById("helix");
const gpuCanvas = document.getElementById("gpu-field");
const controls = document.getElementById("controls");
const runButton = document.getElementById("run-button");
const runMessage = document.getElementById("run-message");
const runtimeLight = document.getElementById("runtime-light");
const runtimeStatus = document.getElementById("runtime-status");
const reportStatus = document.getElementById("report-status");
const abiBadge = document.getElementById("abi-badge");
const downloadReport = document.getElementById("download-report");
const downloadTrace = document.getElementById("download-trace");
const gpuStatus = document.getElementById("gpu-status");
const gpuBadge = document.getElementById("gpu-badge");
const gpuMessage = document.getElementById("gpu-message");
const downloadGpu = document.getElementById("download-gpu");

if (!(canvas instanceof HTMLCanvasElement)) {
  throw new Error("RSH canvas is unavailable");
}
if (!(gpuCanvas instanceof HTMLCanvasElement)) {
  throw new Error("RSH WebGPU field canvas is unavailable");
}
if (!(controls instanceof HTMLFormElement)) {
  throw new Error("RSH controls are unavailable");
}

const context = canvas.getContext("2d");
const gpuContext = gpuCanvas.getContext("2d");
if (!context || !gpuContext) {
  throw new Error("RSH requires 2D canvas contexts");
}

const fields = {
  samples: document.getElementById("samples"),
  kappaFraction: document.getElementById("kappa-fraction"),
  tauFloor: document.getElementById("tau-floor"),
  tauAmplitude: document.getElementById("tau-amplitude"),
};

const outputs = {
  samples: document.getElementById("samples-value"),
  kappaFraction: document.getElementById("kappa-value"),
  tauFloor: document.getElementById("tau-floor-value"),
  tauAmplitude: document.getElementById("tau-amplitude-value"),
};

const metrics = {
  samples: document.getElementById("metric-samples"),
  centre: document.getElementById("metric-centre"),
  kappa: document.getElementById("metric-kappa"),
  tau: document.getElementById("metric-tau"),
  frame: document.getElementById("metric-frame"),
  path: document.getElementById("metric-path"),
  receipt: document.getElementById("metric-receipt"),
};

const gpuMetrics = {
  grid: document.getElementById("gpu-grid"),
  workgroup: document.getElementById("gpu-workgroup"),
  precision: document.getElementById("gpu-precision"),
  adapter: document.getElementById("gpu-adapter"),
  kappa: document.getElementById("gpu-kappa-residual"),
  tau: document.getElementById("gpu-tau-residual"),
  maximum: document.getElementById("gpu-max-residual"),
  gate: document.getElementById("gpu-gate"),
};

const state = {
  wasm: null,
  gpu: null,
  payload: null,
  points: [],
  extent: 1,
  pointerX: 0,
  pointerY: 0,
  phase: 0,
  pass: false,
  gpuGeneration: 0,
  gpuField: [],
  gpuSidecar: null,
  gpuKappaBound: 1,
};

function setRuntimeState(kind, message) {
  runtimeLight.className = `runtime-light ${kind}`;
  runtimeStatus.textContent = message;
}

function setRunMessage(message, kind = "") {
  runMessage.textContent = message;
  runMessage.dataset.kind = kind;
}

function setGpuMessage(message, kind = "") {
  gpuMessage.textContent = message;
  gpuMessage.dataset.kind = kind;
}

function resetGpuEvidence(status = "NOT RUN", kind = "") {
  state.gpuGeneration += 1;
  state.gpuField = [];
  state.gpuSidecar = null;
  state.gpuKappaBound = 1;
  gpuStatus.textContent = status;
  gpuStatus.dataset.kind = kind;
  gpuBadge.textContent = "WGSL —";
  for (const metric of Object.values(gpuMetrics)) {
    metric.textContent = "—";
  }
  downloadGpu.disabled = true;
  renderGpuField();
}

function resetEvidence(status = "NOT RUN", kind = "") {
  state.payload = null;
  state.points = [];
  state.extent = 1;
  state.pass = false;

  reportStatus.textContent = status;
  reportStatus.dataset.kind = kind;
  for (const metric of Object.values(metrics)) {
    metric.textContent = "—";
  }
  downloadReport.disabled = true;
  downloadTrace.disabled = true;
  resetGpuEvidence();
}

function syncControlLabels() {
  outputs.samples.textContent = fields.samples.value;
  outputs.kappaFraction.textContent = Number(fields.kappaFraction.value).toFixed(2);
  outputs.tauFloor.textContent = Number(fields.tauFloor.value).toFixed(2);
  outputs.tauAmplitude.textContent = Number(fields.tauAmplitude.value).toFixed(2);
}

function configuration() {
  return {
    samples: Number(fields.samples.value),
    s0: 0,
    s1: 4,
    kappaFraction: Number(fields.kappaFraction.value),
    tauFloor: Number(fields.tauFloor.value),
    tauAmplitude: Number(fields.tauAmplitude.value),
  };
}

async function instantiateWasm(url) {
  const response = await fetch(url, { cache: "no-cache" });
  if (!response.ok) {
    throw new Error(`WASM request failed with HTTP ${response.status}`);
  }

  if (WebAssembly.instantiateStreaming) {
    try {
      const result = await WebAssembly.instantiateStreaming(response.clone(), {});
      return result.instance;
    } catch (error) {
      console.info("Streaming WASM compilation unavailable; using ArrayBuffer fallback.", error);
    }
  }

  const bytes = await response.arrayBuffer();
  const result = await WebAssembly.instantiate(bytes, {});
  return result.instance;
}

function validateExports(exports) {
  const required = [
    "memory",
    "rsh_abi_version",
    "rsh_run",
    "rsh_schedule",
    "rsh_output_ptr",
    "rsh_output_len",
  ];
  for (const name of required) {
    if (!(name in exports)) {
      throw new Error(`WASM export is missing: ${name}`);
    }
  }
}

function readWasmOutput() {
  const exports = state.wasm.exports;
  const pointer = Number(exports.rsh_output_ptr());
  const length = Number(exports.rsh_output_len());
  if (!Number.isInteger(pointer) || pointer < 0 || !Number.isInteger(length) || length < 1) {
    throw new Error("WASM returned an invalid output buffer");
  }
  const bytes = new Uint8Array(exports.memory.buffer, pointer, length);
  return JSON.parse(textDecoder.decode(bytes));
}

function requestScheduleOracle(config) {
  const status = Number(state.wasm.exports.rsh_schedule(
    GPU_GRID_SAMPLES,
    config.s0,
    config.s1,
    config.kappaFraction,
    config.tauFloor,
    config.tauAmplitude,
  ));
  const payload = readWasmOutput();
  if (status !== 0 || payload.schema === "RSH-BROWSER-ERROR-V1") {
    throw new Error(payload.message || "The Rust core rejected the WGSL schedule grid");
  }
  if (payload.schema !== "RSH-SCHEDULE-RUN-V1") {
    throw new Error(`Unexpected schedule schema: ${payload.schema}`);
  }
  return payload;
}

function runVerifiedGeometry() {
  if (!state.wasm) {
    setRunMessage("The Rust/WASM core is still loading. Please wait a moment.", "fail");
    return;
  }

  const config = configuration();
  runButton.disabled = true;
  setRunMessage("Running the verified Rust geometry core…");

  try {
    const status = Number(state.wasm.exports.rsh_run(
      config.samples,
      config.s0,
      config.s1,
      config.kappaFraction,
      config.tauFloor,
      config.tauAmplitude,
    ));
    const payload = readWasmOutput();

    if (status === 2 || payload.schema === "RSH-BROWSER-ERROR-V1") {
      throw new Error(payload.message || "The Rust core rejected this configuration");
    }

    state.payload = payload;
    state.points = payload.points;
    state.pass = Boolean(payload.report.pass_all) && status === 0;
    state.extent = Math.max(
      1e-9,
      ...state.points.flatMap((point) => [Math.abs(point.x), Math.abs(point.y), Math.abs(point.z)]),
    );

    updateEvidence(payload, state.pass);
    downloadReport.disabled = false;
    downloadTrace.disabled = false;
    setRunMessage(
      state.pass
        ? `PASS · ${payload.points.length} samples produced by rsh-core`
        : "FAIL · the report contains a contract violation",
      state.pass ? "pass" : "fail",
    );
    void runGpuConformance(config);
  } catch (error) {
    resetEvidence("REJECTED", "fail");
    setRunMessage(error instanceof Error ? error.message : String(error), "fail");
  } finally {
    runButton.disabled = false;
  }
}

async function runGpuConformance(config) {
  const generation = state.gpuGeneration + 1;
  state.gpuGeneration = generation;
  state.gpuField = [];
  state.gpuSidecar = null;
  downloadGpu.disabled = true;
  gpuStatus.textContent = "RUNNING";
  gpuStatus.dataset.kind = "";
  setGpuMessage("Evaluating 4,096 f32 schedule samples and comparing them with the rsh-core f64 oracle…");

  if (!state.gpu?.available) {
    gpuStatus.textContent = "CPU/WASM FALLBACK";
    gpuStatus.dataset.kind = "fallback";
    gpuBadge.textContent = "NO WEBGPU";
    setGpuMessage(
      state.gpu?.reason || "WebGPU is unavailable; verified geometry remains on the Rust/WASM path.",
      "fallback",
    );
    return;
  }

  try {
    const oracle = requestScheduleOracle(config);
    const result = await state.gpu.run(config, oracle);
    if (generation !== state.gpuGeneration) return;

    const gatePassed = result.maximum <= GPU_RESIDUAL_THRESHOLD;
    state.gpuField = result.rows;
    state.gpuKappaBound = Number(oracle.kappa_bound);
    state.gpuSidecar = {
      schema: "RSH-WEBGPU-RESIDUAL-SIDECAR-V1",
      model: oracle.model,
      model_version: oracle.model_version,
      backend: "webgpu",
      authority: "residual sidecar only",
      configuration: {
        samples: oracle.samples,
        s0: oracle.s0,
        s1: oracle.s1,
        kappa_fraction: oracle.kappa_fraction,
        tau_floor: oracle.tau_floor,
        tau_amplitude: oracle.tau_amplitude,
      },
      metadata: result.metadata,
      residuals: {
        max_abs_kappa_vs_wasm_f64: result.maxKappa,
        max_abs_tau_vs_wasm_f64: result.maxTau,
        residual_max_vs_cpu: result.maximum,
        threshold: GPU_RESIDUAL_THRESHOLD,
      },
      residual_gate_passed: gatePassed,
      verified_subset: gatePassed,
      visual_verified: false,
      evidence_note: "The CPU/WASM report remains authoritative. This sidecar records an f32 WebGPU residual comparison and never replaces the geometry receipt.",
    };

    gpuStatus.textContent = gatePassed ? "RESIDUAL PASS" : "DISPLAY ONLY";
    gpuStatus.dataset.kind = gatePassed ? "pass" : "fail";
    gpuBadge.textContent = `WGSL · ${result.metadata.f_precision}`;
    gpuMetrics.grid.textContent = String(oracle.samples);
    gpuMetrics.workgroup.textContent = String(result.metadata.workgroup_size);
    gpuMetrics.precision.textContent = result.metadata.f_precision;
    gpuMetrics.adapter.textContent = result.metadata.adapter;
    gpuMetrics.kappa.textContent = scientific(result.maxKappa);
    gpuMetrics.tau.textContent = scientific(result.maxTau);
    gpuMetrics.maximum.textContent = scientific(result.maximum);
    gpuMetrics.gate.textContent = gatePassed
      ? `≤ ${GPU_RESIDUAL_THRESHOLD.toExponential(1)}`
      : `> ${GPU_RESIDUAL_THRESHOLD.toExponential(1)}`;
    downloadGpu.disabled = false;
    setGpuMessage(
      gatePassed
        ? "The 4,096-sample f32 field passed the published residual gate. The visual remains display-only."
        : "The field exceeded the published residual gate and has been restricted to display-only mode.",
      gatePassed ? "pass" : "fail",
    );
    renderGpuField();
  } catch (error) {
    if (generation !== state.gpuGeneration) return;
    state.gpuField = [];
    state.gpuSidecar = null;
    gpuStatus.textContent = "CPU/WASM FALLBACK";
    gpuStatus.dataset.kind = "fallback";
    gpuBadge.textContent = "GPU ERROR";
    downloadGpu.disabled = true;
    setGpuMessage(
      `${error instanceof Error ? error.message : String(error)} Verified geometry remains on the Rust/WASM path.`,
      "fallback",
    );
    renderGpuField();
  }
}

function scientific(value, digits = 3) {
  return Number(value).toExponential(digits);
}

function updateEvidence(payload, pass) {
  const report = payload.report;
  reportStatus.textContent = pass ? "PASS" : "FAIL";
  reportStatus.dataset.kind = pass ? "pass" : "fail";
  abiBadge.textContent = `ABI ${payload.abi_version} · WASM`;

  metrics.samples.textContent = String(report.samples);
  metrics.centre.textContent = scientific(report.centre_error);
  metrics.kappa.textContent = `${Number(report.max_kappa).toFixed(6)} / ${Number(report.kappa_bound).toFixed(6)}`;
  metrics.tau.textContent = `[${Number(report.min_tau).toFixed(6)}, ${Number(report.max_tau).toFixed(6)}]`;
  metrics.frame.textContent = scientific(Math.max(
    Number(report.max_frame_norm_error),
    Number(report.max_frame_orthogonality_error),
  ));
  metrics.path.textContent = Number(report.path_length).toFixed(6);
  metrics.receipt.textContent = report.receipt;
}

function download(name, type, content) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

function traceCsv(payload) {
  const header = "p,x,y,z,kappa,tau";
  const rows = payload.points.map((point) => [
    point.p,
    point.x,
    point.y,
    point.z,
    point.kappa,
    point.tau,
  ].map((value) => Number(value).toExponential(17)).join(","));
  return `${header}\n${rows.join("\n")}\n`;
}

function resizeCanvas(target, targetContext) {
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const box = target.getBoundingClientRect();
  target.width = Math.max(1, Math.floor(box.width * ratio));
  target.height = Math.max(1, Math.floor(box.height * ratio));
  targetContext.setTransform(ratio, 0, 0, ratio, 0, 0);
}

function resize() {
  resizeCanvas(canvas, context);
  resizeCanvas(gpuCanvas, gpuContext);
  renderGpuField();
}

function rotate(point, yaw, pitch) {
  const cy = Math.cos(yaw);
  const sy = Math.sin(yaw);
  const cp = Math.cos(pitch);
  const sp = Math.sin(pitch);
  const x1 = point.x * cy - point.z * sy;
  const z1 = point.x * sy + point.z * cy;
  return {
    x: x1,
    y: point.y * cp - z1 * sp,
    z: point.y * sp + z1 * cp,
    p: point.p,
    tau: point.tau,
  };
}

function drawGrid(targetContext, width, height, spacing = 48) {
  targetContext.save();
  targetContext.strokeStyle = "rgba(145, 164, 170, 0.11)";
  targetContext.lineWidth = 1;
  for (let x = 0; x <= width; x += spacing) {
    targetContext.beginPath();
    targetContext.moveTo(x, 0);
    targetContext.lineTo(x, height);
    targetContext.stroke();
  }
  for (let y = 0; y <= height; y += spacing) {
    targetContext.beginPath();
    targetContext.moveTo(0, y);
    targetContext.lineTo(width, y);
    targetContext.stroke();
  }
  targetContext.restore();
}

function renderGpuField() {
  const width = gpuCanvas.clientWidth;
  const height = gpuCanvas.clientHeight;
  if (width < 1 || height < 1) return;

  gpuContext.clearRect(0, 0, width, height);
  drawGrid(gpuContext, width, height, 42);

  if (state.gpuField.length === 0) {
    gpuContext.save();
    gpuContext.fillStyle = "rgba(145, 164, 170, 0.82)";
    gpuContext.font = "700 12px ui-monospace, monospace";
    gpuContext.textAlign = "center";
    gpuContext.fillText("WAITING FOR WGSL FIELD OR CPU/WASM FALLBACK", width / 2, height / 2);
    gpuContext.restore();
    return;
  }

  const padding = 28;
  const plotWidth = Math.max(1, width - padding * 2);
  const plotHeight = Math.max(1, height - padding * 2);
  const drawSeries = (selector, maximum, strokeStyle) => {
    gpuContext.beginPath();
    state.gpuField.forEach((row, index) => {
      const x = padding + row.p * plotWidth;
      const y = padding + (1 - Math.min(1, Math.max(0, selector(row) / maximum))) * plotHeight;
      if (index === 0) gpuContext.moveTo(x, y);
      else gpuContext.lineTo(x, y);
    });
    gpuContext.lineJoin = "round";
    gpuContext.lineCap = "round";
    gpuContext.lineWidth = 1.8;
    gpuContext.strokeStyle = strokeStyle;
    gpuContext.stroke();
  };

  drawSeries((row) => row.kappa, state.gpuKappaBound, "rgba(101, 217, 192, 0.95)");
  drawSeries((row) => row.tau, 1, "rgba(226, 166, 91, 0.90)");
}

function render() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;

  context.save();
  context.setTransform(1, 0, 0, 1, 0, 0);
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.restore();
  drawGrid(context, width, height);

  if (state.points.length === 0) {
    context.save();
    context.fillStyle = "rgba(145, 164, 170, 0.82)";
    context.font = "700 13px ui-monospace, monospace";
    context.textAlign = "center";
    context.fillText("WAITING FOR VERIFIED WASM SAMPLES", width / 2, height / 2);
    context.restore();
    requestAnimationFrame(render);
    return;
  }

  const yaw = state.phase * 0.20 + state.pointerX * 0.52;
  const pitch = -0.28 + state.pointerY * 0.28;
  const scale = Math.min(width, height) * 0.38 / state.extent;
  const projected = state.points.map((point) => {
    const rotated = rotate(point, yaw, pitch);
    const perspective = 1 / (1.35 + rotated.z / (state.extent * 8));
    return {
      x: width * 0.5 + rotated.x * scale * perspective,
      y: height * 0.5 - rotated.y * scale * perspective,
      z: rotated.z,
      p: rotated.p,
      tau: rotated.tau,
    };
  });

  context.beginPath();
  projected.forEach((point, index) => {
    if (index === 0) context.moveTo(point.x, point.y);
    else context.lineTo(point.x, point.y);
  });
  context.lineJoin = "round";
  context.lineCap = "round";
  context.lineWidth = 12;
  context.strokeStyle = state.pass
    ? "rgba(101, 217, 192, 0.08)"
    : "rgba(226, 166, 91, 0.10)";
  context.stroke();

  context.beginPath();
  projected.forEach((point, index) => {
    if (index === 0) context.moveTo(point.x, point.y);
    else context.lineTo(point.x, point.y);
  });
  context.lineWidth = 2.4;
  context.strokeStyle = state.pass
    ? "rgba(101, 217, 192, 0.90)"
    : "rgba(226, 166, 91, 0.92)";
  context.stroke();

  const stride = Math.max(1, Math.floor(projected.length / 32));
  projected.forEach((point, index) => {
    if (index % stride !== 0) return;
    const alpha = 0.22 + Math.min(0.55, Number(point.tau) * 0.55);
    context.beginPath();
    context.arc(point.x, point.y, 1.4 + alpha * 1.7, 0, Math.PI * 2);
    context.fillStyle = `rgba(226, 166, 91, ${alpha})`;
    context.fill();
  });

  const centre = projected[Math.floor(projected.length / 2)];
  context.beginPath();
  context.arc(centre.x, centre.y, 20, 0, Math.PI * 2);
  context.strokeStyle = "rgba(232, 240, 241, 0.38)";
  context.lineWidth = 1;
  context.stroke();
  context.beginPath();
  context.arc(centre.x, centre.y, 4, 0, Math.PI * 2);
  context.fillStyle = "rgba(232, 240, 241, 0.96)";
  context.fill();

  state.phase += 0.0035;
  requestAnimationFrame(render);
}

for (const input of Object.values(fields)) {
  input.addEventListener("input", syncControlLabels);
}

controls.addEventListener("submit", (event) => {
  event.preventDefault();
  runVerifiedGeometry();
});

canvas.addEventListener("pointermove", (event) => {
  const box = canvas.getBoundingClientRect();
  state.pointerX = ((event.clientX - box.left) / box.width - 0.5) * 2;
  state.pointerY = ((event.clientY - box.top) / box.height - 0.5) * 2;
});

canvas.addEventListener("pointerleave", () => {
  state.pointerX = 0;
  state.pointerY = 0;
});

window.addEventListener("resize", resize);

downloadReport.addEventListener("click", () => {
  if (!state.payload) return;
  download(
    `rsh_wasm_report_${state.payload.report.samples}.json`,
    "application/json",
    `${JSON.stringify(state.payload, null, 2)}\n`,
  );
});

downloadTrace.addEventListener("click", () => {
  if (!state.payload) return;
  download(
    `rsh_wasm_trace_${state.payload.report.samples}.csv`,
    "text/csv",
    traceCsv(state.payload),
  );
});

downloadGpu.addEventListener("click", () => {
  if (!state.gpuSidecar) return;
  download(
    "rsh_webgpu_residual_4096.json",
    "application/json",
    `${JSON.stringify(state.gpuSidecar, null, 2)}\n`,
  );
});

async function start() {
  syncControlLabels();
  resetEvidence();
  runButton.disabled = true;
  resize();
  render();

  try {
    const instance = await instantiateWasm("./pkg/rsh_wasm.wasm");
    validateExports(instance.exports);
    state.wasm = instance;

    const abiVersion = Number(instance.exports.rsh_abi_version());
    if (abiVersion !== 1) {
      throw new Error(`Unsupported RSH WASM ABI ${abiVersion}`);
    }

    abiBadge.textContent = `ABI ${abiVersion} · WASM`;
    setRuntimeState("pass", "Rust/WASM core loaded · WebGPU residual layer probing");

    try {
      state.gpu = await createGpuScheduleRunner("./wgsl/kappa_tau_field.wgsl", (lost) => {
        state.gpu = {
          available: false,
          reason: `WebGPU device lost: ${lost.message || lost.reason || "unknown reason"}`,
        };
        resetGpuEvidence("CPU/WASM FALLBACK", "fallback");
        setGpuMessage(state.gpu.reason, "fallback");
      });
    } catch (error) {
      state.gpu = {
        available: false,
        reason: error instanceof Error ? error.message : String(error),
      };
    }

    if (state.gpu.available) {
      gpuStatus.textContent = "READY";
      gpuStatus.dataset.kind = "pass";
      gpuBadge.textContent = "WGSL · f32";
      setGpuMessage("WebGPU adapter ready. The next verified run will produce a residual sidecar.", "pass");
    } else {
      gpuStatus.textContent = "CPU/WASM FALLBACK";
      gpuStatus.dataset.kind = "fallback";
      gpuBadge.textContent = "NO WEBGPU";
      setGpuMessage(state.gpu.reason, "fallback");
    }

    setRunMessage("Ready. Running the default verified configuration…", "pass");
    runButton.disabled = false;
    runVerifiedGeometry();
  } catch (error) {
    resetEvidence("UNAVAILABLE", "fail");
    setRuntimeState("fail", "Rust/WASM core failed to load");
    setRunMessage(error instanceof Error ? error.message : String(error), "fail");
    runButton.disabled = true;
  }

  if ("serviceWorker" in navigator && window.isSecureContext) {
    navigator.serviceWorker.register("./sw.js").catch((error) => {
      console.info("Offline cache registration was skipped.", error);
    });
  }
}

start();
