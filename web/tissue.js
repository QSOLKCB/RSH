const decoder = new TextDecoder("utf-8");
const canvas = document.getElementById("tissue-canvas");
const context = canvas.getContext("2d");
const form = document.getElementById("controls");
const runButton = document.getElementById("run");
const downloadButton = document.getElementById("download");
const fields = {
  cells: document.getElementById("cells"),
  ticks: document.getElementById("ticks"),
  phaseCoupling: document.getElementById("phase-coupling"),
  bindingDiffusion: document.getElementById("binding-diffusion"),
};
const labels = {
  phaseCoupling: document.getElementById("phase-value"),
  bindingDiffusion: document.getElementById("binding-value"),
};
const output = {
  status: document.getElementById("status"),
  finalQf: document.getElementById("final-qf"),
  qfRange: document.getElementById("qf-range"),
  audit: document.getElementById("audit"),
  message: document.getElementById("message"),
  seedReceipt: document.getElementById("seed-receipt"),
  tissueReceipt: document.getElementById("tissue-receipt"),
  constitutionHash: document.getElementById("constitution-hash"),
};

if (!(canvas instanceof HTMLCanvasElement) || !context || !(form instanceof HTMLFormElement)) {
  throw new Error("The tissue laboratory could not initialize its interface");
}

const state = { wasm: null, report: null };

function syncLabels() {
  labels.phaseCoupling.textContent = Number(fields.phaseCoupling.value).toFixed(2);
  labels.bindingDiffusion.textContent = Number(fields.bindingDiffusion.value).toFixed(2);
}

async function instantiateWasm(url) {
  const response = await fetch(url, { cache: "no-cache" });
  if (!response.ok) throw new Error(`Tissue WASM request failed with HTTP ${response.status}`);
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
    "rsh_tissue_abi_version",
    "rsh_tissue_run",
    "rsh_tissue_output_ptr",
    "rsh_tissue_output_len",
  ]) {
    if (!(name in exports)) throw new Error(`Tissue WASM export is missing: ${name}`);
  }
  if (Number(exports.rsh_tissue_abi_version()) !== 1) {
    throw new Error("Unsupported tissue WASM ABI");
  }
}

function readPayload() {
  const exports = state.wasm.exports;
  const pointer = Number(exports.rsh_tissue_output_ptr());
  const length = Number(exports.rsh_tissue_output_len());
  if (!Number.isSafeInteger(pointer) || pointer < 0 || !Number.isSafeInteger(length) || length < 1) {
    throw new Error("Tissue WASM returned an invalid output buffer");
  }
  const bytes = exports.memory.buffer.byteLength;
  if (pointer > bytes || length > bytes - pointer) {
    throw new Error("Tissue WASM output span exceeds linear memory");
  }
  return JSON.parse(decoder.decode(new Uint8Array(exports.memory.buffer, pointer, length)));
}

function currentConfig() {
  const cells = Number(fields.cells.value);
  const ticks = Number(fields.ticks.value);
  if (!Number.isInteger(cells) || cells < 3 || cells > 128) throw new Error("Cells must be an integer in [3, 128]");
  if (!Number.isInteger(ticks) || ticks < 1 || ticks > 1000) throw new Error("Ticks must be an integer in [1, 1000]");
  return {
    cells,
    ticks,
    geometrySamples: 129,
    ds: 0.05,
    phaseCoupling: Number(fields.phaseCoupling.value),
    bindingDiffusion: Number(fields.bindingDiffusion.value),
  };
}

function scientific(value) {
  return Number(value).toExponential(4);
}

function draw(report) {
  context.clearRect(0, 0, canvas.width, canvas.height);
  const gradient = context.createLinearGradient(0, 0, 0, canvas.height);
  gradient.addColorStop(0, "#111923");
  gradient.addColorStop(1, "#070a0e");
  context.fillStyle = gradient;
  context.fillRect(0, 0, canvas.width, canvas.height);

  const cells = report.final_cells;
  const extent = Math.max(1e-9, ...cells.flatMap((cell) => [Math.abs(cell.x), Math.abs(cell.y)]));
  const scale = Math.min(canvas.width, canvas.height) * 0.40 / extent;
  const point = (cell) => [canvas.width / 2 + cell.x * scale, canvas.height / 2 - cell.y * scale];

  context.strokeStyle = "#384653";
  context.lineWidth = 1.2;
  for (const [left, right] of report.edges) {
    const [x1, y1] = point(cells[left]);
    const [x2, y2] = point(cells[right]);
    context.beginPath();
    context.moveTo(x1, y1);
    context.lineTo(x2, y2);
    context.stroke();
  }

  const roleStroke = { R: "#f4b860", W: "#7ad8cf", P: "#d8dde7" };
  for (const cell of cells) {
    const [x, y] = point(cell);
    const radius = 4 + 7 * Math.min(1, cell.binding);
    context.beginPath();
    context.arc(x, y, radius, 0, Math.PI * 2);
    context.fillStyle = "#0b1117";
    context.fill();
    context.strokeStyle = roleStroke[cell.role] || "#d8dde7";
    context.lineWidth = 2;
    context.stroke();
  }

  const qValues = report.ticks.map((tick) => tick.metrics.q_f);
  const left = 32;
  const top = 32;
  const width = 250;
  const height = 80;
  context.strokeStyle = "#2c3945";
  context.strokeRect(left, top, width, height);
  context.beginPath();
  qValues.forEach((value, index) => {
    const x = left + (index / Math.max(1, qValues.length - 1)) * width;
    const y = top + height - value * height;
    if (index === 0) context.moveTo(x, y);
    else context.lineTo(x, y);
  });
  context.strokeStyle = "#f4b860";
  context.lineWidth = 2;
  context.stroke();
  context.fillStyle = "#aeb7c4";
  context.font = "13px ui-monospace, monospace";
  context.fillText("Q_f over ticks", left, top + height + 18);
}

async function runTissue() {
  if (!state.wasm) return;
  runButton.disabled = true;
  downloadButton.disabled = true;
  output.status.textContent = "RUNNING";
  output.message.textContent = "Executing the shared Rust tissue runtime in WebAssembly…";
  try {
    const config = currentConfig();
    const status = Number(state.wasm.exports.rsh_tissue_run(
      config.cells,
      config.ticks,
      config.geometrySamples,
      config.ds,
      config.phaseCoupling,
      config.bindingDiffusion,
      0,
      0.0,
      1.0e-4,
      0.0,
    ));
    const payload = readPayload();
    if (status === 2 || payload.schema === "RSH-TISSUE-WASM-ERROR-V1") {
      throw new Error(payload.message || "The tissue configuration was rejected");
    }
    if (payload.schema !== "RSH-TISSUE-WASM-PAYLOAD-V1") {
      throw new Error(`Unexpected tissue payload schema: ${payload.schema}`);
    }
    if (status !== 0 || !payload.report.pass_all) {
      throw new Error("The tissue report did not satisfy contract 1.0.0");
    }

    state.report = payload.report;
    output.status.textContent = "PASS";
    output.finalQf.textContent = scientific(state.report.final_q_f);
    output.qfRange.textContent = `${scientific(state.report.min_q_f)} — ${scientific(state.report.max_q_f)}`;
    output.audit.textContent = state.report.audit_chain_valid ? "VALID" : "INVALID";
    output.seedReceipt.textContent = state.report.seed_geometry_receipt;
    output.tissueReceipt.textContent = state.report.receipt;
    output.constitutionHash.textContent = state.report.constitution_hash;
    output.message.textContent = `Executed ${config.cells} cells for ${config.ticks} ticks. The report is Rust/WASM evidence, not a geometry-authority claim.`;
    downloadButton.disabled = false;
    draw(state.report);
  } catch (error) {
    state.report = null;
    output.status.textContent = "REJECTED";
    output.message.textContent = error instanceof Error ? error.message : String(error);
  } finally {
    runButton.disabled = false;
  }
}

function downloadReport() {
  if (!state.report) return;
  const blob = new Blob([`${JSON.stringify(state.report, null, 2)}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "rsh-rust-wasm-tissue-report.json";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

form.addEventListener("input", syncLabels);
form.addEventListener("submit", (event) => {
  event.preventDefault();
  void runTissue();
});
downloadButton.addEventListener("click", downloadReport);
syncLabels();

try {
  state.wasm = await instantiateWasm("./pkg/rsh_tissue_wasm.wasm");
  validateExports(state.wasm.exports);
  output.status.textContent = "READY";
  void runTissue();
} catch (error) {
  output.status.textContent = "LOAD FAILED";
  output.message.textContent = error instanceof Error ? error.message : String(error);
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("./sw.js").catch((error) => {
    console.info("Offline cache registration failed.", error);
  });
}
