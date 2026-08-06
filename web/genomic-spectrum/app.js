import {
  MAX_FASTA_CHARACTERS,
  MAX_VCF_CHARACTERS,
  MIDI_PPQ,
  MIDI_TEMPO_BPM,
  buildReport,
  canonicalJson,
  manifestFor,
  utf8,
} from "./model.js";

const $ = id => document.getElementById(id);
const state = { artifacts: null, audio: null, nodes: [], timeout: null };
const unit = "ATGGAACTGCCTGGCTTTAACGCGTAG";
const fixtureSequence = (unit.repeat(11) + "ACGTNN").repeat(2);
const fixtureFasta = `>synthetic_chr sealed genomic spectral fixture\n${fixtureSequence}\n`;
const fixtureVcf = "##fileformat=VCFv4.5\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\nsynthetic_chr\t4\tstop_gain\tG\tT\t.\tPASS\t.\nsynthetic_chr\t307\ttransition\tG\tA\t.\tPASS\t.\n";

function setStatus(text, error = false) {
  $("status").textContent = text;
  $("status").classList.toggle("error", error);
}
function fraction(value) {
  if (!value.denominator) return "n/a";
  return `${(100 * value.numerator / value.denominator).toFixed(1)}%`;
}
function drawChart(windows) {
  const canvas = $("chart"), ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1, width = canvas.clientWidth, height = canvas.clientHeight;
  canvas.width = Math.max(1, Math.floor(width * dpr));
  canvas.height = Math.max(1, Math.floor(height * dpr));
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = "#343434";
  ctx.lineWidth = 1;
  for (let y = 28; y < height - 25; y += 54) {
    ctx.beginPath();
    ctx.moveTo(42, y);
    ctx.lineTo(width - 18, y);
    ctx.stroke();
  }
  if (!windows.length) return;
  const period = windows.map(window => window.period3_exact.total_scaled_power);
  const scl = windows.map(window => window.scl_exact.total_energy);
  const maxPeriod = Math.max(1, ...period), maxScl = Math.max(1, ...scl);
  const x = index => 42 + index * (width - 70) / Math.max(1, windows.length - 1);
  const line = (values, maximum, stroke) => {
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    values.forEach((value, index) => {
      const y = height - 28 - (value / maximum) * (height - 62);
      if (index) ctx.lineTo(x(index), y);
      else ctx.moveTo(x(index), y);
    });
    ctx.stroke();
  };
  line(period, maxPeriod, "#d6b15f");
  line(scl, maxScl, "#8e8a80");
  ctx.fillStyle = "#aaa69d";
  ctx.font = "11px ui-monospace, monospace";
  ctx.fillText("0", 18, height - 24);
  ctx.fillText(String(windows.length - 1), width - 35, height - 8);
}
function replaceRows(tbody, rows, columnCount, emptyText) {
  tbody.replaceChildren();
  if (!rows.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = columnCount;
    cell.textContent = emptyText;
    row.append(cell);
    tbody.append(row);
    return;
  }
  for (const values of rows) {
    const row = document.createElement("tr");
    for (const value of values) {
      const cell = document.createElement("td");
      const payload = value && typeof value === "object" ? value : { text: value };
      if (payload.code) {
        const code = document.createElement("code");
        code.textContent = String(payload.text ?? "");
        cell.append(code);
      } else {
        cell.textContent = String(payload.text ?? "");
      }
      row.append(cell);
    }
    tbody.append(row);
  }
}
function render(report) {
  $("sequenceLength").textContent = report.input.sequence_length.toLocaleString();
  $("windowCount").textContent = report.window_count;
  $("variantCount").textContent = report.variant_count;
  $("refget").textContent = report.input.refget_accession;
  replaceRows(
    $("windowRows"),
    report.windows.map(window => [
      window.window_index,
      `${window.start_1based}–${window.end_1based_inclusive}`,
      fraction(window.gc_fraction),
      window.cpg_count,
      window.period3_exact.total_scaled_power,
      window.scl_exact.total_energy,
      { text: window.etq_address.event_index, code: true },
      `${window.spectral_receiver.register} / ${window.spectral_receiver.midi_pitch}`,
    ]),
    8,
    "No windows.",
  );
  replaceRows(
    $("variantRows"),
    report.variants.map(variant => [
      `${variant.chrom}:${variant.position_1based} ${variant.ref}→${variant.alt}`,
      variant.substitution_class,
      { text: variant.context_3mer, code: true },
      { text: `${variant.etq_address.site_index}/${variant.etq_address.fibre_label}/${variant.etq_address.event_index}`, code: true },
      variant.period3_scaled_power_delta,
      variant.scl_energy_delta,
      variant.frame_relative_effect ?? "not evaluated",
    ]),
    7,
    "No SNVs supplied.",
  );
  drawChart(report.windows);
}
function setOutputEnabled(enabled) {
  document.querySelectorAll("[data-download]").forEach(button => { button.disabled = !enabled; });
  $("play").disabled = !enabled;
  $("stop").disabled = !enabled;
}
function stopAudio() {
  if (state.timeout !== null) {
    window.clearTimeout(state.timeout);
    state.timeout = null;
  }
  for (const node of state.nodes) {
    try { node.stop(); } catch { /* already stopped */ }
  }
  state.nodes = [];
  $("stop").disabled = !state.artifacts;
}
function clearArtifacts() {
  stopAudio();
  state.artifacts = null;
  setOutputEnabled(false);
  $("receipt").textContent = "No receipt generated.";
}
async function analyze() {
  clearArtifacts();
  try {
    setStatus("Normalizing FASTA and computing exact evidence…");
    const windowSize = Number($("windowSize").value);
    const stride = Number($("stride").value);
    const frameText = $("frameOrigin").value.trim();
    const frame = frameText ? Number(frameText) : null;
    const result = await buildReport($("fasta").value, $("vcf").value || null, windowSize, stride, frame);
    const reportBytes = utf8(canonicalJson(result.report));
    const manifest = await manifestFor(reportBytes, result.windowsCsv, result.variantsCsv, result.midi);
    state.artifacts = {
      report: reportBytes,
      windows: result.windowsCsv,
      variants: result.variantsCsv,
      midi: result.midi,
      manifest: utf8(`${canonicalJson(manifest)}\n`),
      reportObject: result.report,
    };
    render(result.report);
    $("receipt").textContent = JSON.stringify(manifest, null, 2);
    setOutputEnabled(true);
    setStatus(`PASS · ${result.report.window_count} window(s), ${result.report.variant_count} SNV(s), canonical artifacts ready.`);
  } catch (error) {
    console.error(error);
    setStatus(`REJECTED · ${error instanceof Error ? error.message : String(error)}`, true);
  }
}
function download(name, bytes, type) {
  const blob = new Blob([bytes], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function play() {
  const report = state.artifacts?.reportObject;
  if (!report) return;
  stopAudio();
  state.audio ??= new AudioContext();
  await state.audio.resume();
  const now = state.audio.currentTime + 0.05;
  const secondsPerTick = 60 / (MIDI_TEMPO_BPM * MIDI_PPQ);
  let finalTime = now;
  report.windows.forEach(windowRecord => {
    const receiver = windowRecord.spectral_receiver;
    const start = now + windowRecord.window_index * MIDI_PPQ * secondsPerTick;
    const duration = receiver.duration_ticks * secondsPerTick;
    const oscillator = state.audio.createOscillator();
    const gain = state.audio.createGain();
    oscillator.frequency.value = 440 * 2 ** ((receiver.midi_pitch - 69) / 12);
    oscillator.type = "sine";
    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.exponentialRampToValueAtTime(Math.max(0.025, receiver.midi_velocity / 1270), start + Math.min(0.015, duration / 4));
    gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
    oscillator.connect(gain).connect(state.audio.destination);
    oscillator.start(start);
    oscillator.stop(start + duration + 0.02);
    state.nodes.push(oscillator);
    finalTime = Math.max(finalTime, start + duration + 0.02);
  });
  state.timeout = window.setTimeout(stopAudio, Math.ceil((finalTime - state.audio.currentTime + 0.1) * 1000));
}

$("fasta").maxLength = MAX_FASTA_CHARACTERS;
$("vcf").maxLength = MAX_VCF_CHARACTERS;
$("analyze").addEventListener("click", analyze);
$("loadFixture").addEventListener("click", () => {
  $("fasta").value = fixtureFasta;
  $("vcf").value = fixtureVcf;
  $("windowSize").value = 303;
  $("stride").value = 303;
  $("frameOrigin").value = 1;
  setStatus("Sealed 606-base fixture loaded.");
});
$("play").addEventListener("click", play);
$("stop").addEventListener("click", stopAudio);
document.querySelectorAll("[data-download]").forEach(button => button.addEventListener("click", () => {
  const key = button.dataset.download;
  const item = state.artifacts?.[key];
  if (!item) return;
  const names = { report:"report.json", windows:"windows.csv", variants:"variants.csv", midi:"spectrum.mid", manifest:"manifest.json" };
  const types = { report:"application/json", windows:"text/csv", variants:"text/csv", midi:"audio/midi", manifest:"application/json" };
  download(names[key], item, types[key]);
}));
window.addEventListener("resize", () => state.artifacts && drawChart(state.artifacts.reportObject.windows));
if ("serviceWorker" in navigator && location.protocol !== "file:") {
  navigator.serviceWorker.register("./sw.js").catch(error => console.info("Genomic spectrum offline cache unavailable.", error));
}
