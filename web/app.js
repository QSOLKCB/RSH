const textDecoder = new TextDecoder("utf-8");

const canvas = document.getElementById("helix");
const controls = document.getElementById("controls");
const runButton = document.getElementById("run-button");
const runMessage = document.getElementById("run-message");
const runtimeLight = document.getElementById("runtime-light");
const runtimeStatus = document.getElementById("runtime-status");
const reportStatus = document.getElementById("report-status");
const abiBadge = document.getElementById("abi-badge");
const downloadReport = document.getElementById("download-report");
const downloadTrace = document.getElementById("download-trace");

if (!(canvas instanceof HTMLCanvasElement)) {
  throw new Error("RSH canvas is unavailable");
}
if (!(controls instanceof HTMLFormElement)) {
  throw new Error("RSH controls are unavailable");
}

const context = canvas.getContext("2d");
if (!context) {
  throw new Error("RSH requires a 2D canvas context");
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

const state = {
  wasm: null,
  payload: null,
  points: [],
  extent: 1,
  pointerX: 0,
  pointerY: 0,
  phase: 0,
  pass: false,
};

function setRuntimeState(kind, message) {
  runtimeLight.className = `runtime-light ${kind}`;
  runtimeStatus.textContent = message;
}

function setRunMessage(message, kind = "") {
  runMessage.textContent = message;
  runMessage.dataset.kind = kind;
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
  if (!Number.isInteger(pointer) || !Number.isInteger(length) || length < 1) {
    throw new Error("WASM returned an invalid output buffer");
  }
  const bytes = new Uint8Array(exports.memory.buffer, pointer, length);
  return JSON.parse(textDecoder.decode(bytes));
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
  } catch (error) {
    resetEvidence("REJECTED", "fail");
    setRunMessage(error instanceof Error ? error.message : String(error), "fail");
  } finally {
    runButton.disabled = false;
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

function resize() {
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const box = canvas.getBoundingClientRect();
  canvas.width = Math.max(1, Math.floor(box.width * ratio));
  canvas.height = Math.max(1, Math.floor(box.height * ratio));
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
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

function drawGrid(width, height) {
  context.save();
  context.strokeStyle = "rgba(145, 164, 170, 0.11)";
  context.lineWidth = 1;
  for (let x = 0; x <= width; x += 48) {
    context.beginPath();
    context.moveTo(x, 0);
    context.lineTo(x, height);
    context.stroke();
  }
  for (let y = 0; y <= height; y += 48) {
    context.beginPath();
    context.moveTo(0, y);
    context.lineTo(width, y);
    context.stroke();
  }
  context.restore();
}

function render() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;

  context.save();
  context.setTransform(1, 0, 0, 1, 0, 0);
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.restore();
  drawGrid(width, height);

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
    setRuntimeState("pass", "Rust/WASM core loaded · no JavaScript geometry model");
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
