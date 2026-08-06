import { buildReport, canonicalJson, manifestFor, utf8 } from "./model.js";

const $ = id => document.getElementById(id);
const state = { artifacts: null, audio: null };
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
  canvas.width = Math.max(1, Math.floor(width * dpr)); canvas.height = Math.max(1, Math.floor(height * dpr));
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = "#343434"; ctx.lineWidth = 1;
  for (let y = 28; y < height - 25; y += 54) { ctx.beginPath(); ctx.moveTo(42, y); ctx.lineTo(width - 18, y); ctx.stroke(); }
  if (!windows.length) return;
  const p = windows.map(w => w.period3_exact.total_scaled_power), s = windows.map(w => w.scl_exact.total_energy);
  const maxP = Math.max(1, ...p), maxS = Math.max(1, ...s), x = i => 42 + i * (width - 70) / Math.max(1, windows.length - 1);
  const line = (values, max, stroke) => { ctx.strokeStyle = stroke; ctx.lineWidth = 2.5; ctx.beginPath(); values.forEach((v, i) => { const y = height - 28 - (v / max) * (height - 62); i ? ctx.lineTo(x(i), y) : ctx.moveTo(x(i), y); }); ctx.stroke(); };
  line(p, maxP, "#d6b15f"); line(s, maxS, "#8e8a80");
  ctx.fillStyle = "#aaa69d"; ctx.font = "11px ui-monospace, monospace"; ctx.fillText("0", 18, height - 24); ctx.fillText(String(windows.length - 1), width - 35, height - 8);
}
function render(report) {
  $("sequenceLength").textContent = report.input.sequence_length.toLocaleString();
  $("windowCount").textContent = report.window_count;
  $("variantCount").textContent = report.variant_count;
  $("refget").textContent = report.input.refget_accession;
  $("windowRows").innerHTML = report.windows.map(w => `<tr><td>${w.window_index}</td><td>${w.start_1based}–${w.end_1based_inclusive}</td><td>${fraction(w.gc_fraction)}</td><td>${w.cpg_count}</td><td>${w.period3_exact.total_scaled_power}</td><td>${w.scl_exact.total_energy}</td><td><code>${w.etq_address.event_index}</code></td><td>${w.spectral_receiver.register} / ${w.spectral_receiver.midi_pitch}</td></tr>`).join("") || '<tr><td colspan="8">No windows.</td></tr>';
  $("variantRows").innerHTML = report.variants.map(v => `<tr><td>${v.chrom}:${v.position_1based} ${v.ref}→${v.alt}</td><td>${v.substitution_class}</td><td><code>${v.context_3mer}</code></td><td><code>${v.etq_address.site_index}/${v.etq_address.fibre_label}/${v.etq_address.event_index}</code></td><td>${v.period3_scaled_power_delta}</td><td>${v.scl_energy_delta}</td><td>${v.frame_relative_effect ?? "not evaluated"}</td></tr>`).join("") || '<tr><td colspan="7">No SNVs supplied.</td></tr>';
  drawChart(report.windows);
}
async function analyze() {
  try {
    setStatus("Normalizing FASTA and computing exact evidence…");
    const windowSize = Number($("windowSize").value), stride = Number($("stride").value);
    const frameText = $("frameOrigin").value.trim(), frame = frameText ? Number(frameText) : null;
    const result = await buildReport($("fasta").value, $("vcf").value || null, windowSize, stride, frame);
    const reportBytes = utf8(canonicalJson(result.report));
    const manifest = await manifestFor(reportBytes, result.windowsCsv, result.variantsCsv, result.midi);
    state.artifacts = { report: reportBytes, windows: result.windowsCsv, variants: result.variantsCsv, midi: result.midi, manifest: utf8(canonicalJson(manifest)), reportObject: result.report };
    render(result.report); $("receipt").textContent = JSON.stringify(manifest, null, 2);
    document.querySelectorAll("[data-download]").forEach(button => button.disabled = false); $("play").disabled = false;
    setStatus(`PASS · ${result.report.window_count} window(s), ${result.report.variant_count} SNV(s), canonical artifacts ready.`);
  } catch (error) { console.error(error); setStatus(`REJECTED · ${error.message}`, true); }
}
function download(name, bytes, type) {
  const blob = new Blob([bytes], { type }), url = URL.createObjectURL(blob), a = document.createElement("a");
  a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function play() {
  const report = state.artifacts?.reportObject; if (!report) return;
  state.audio ??= new AudioContext(); await state.audio.resume(); const now = state.audio.currentTime + 0.05;
  report.windows.forEach((w, index) => { const start = now + index * 0.26, osc = state.audio.createOscillator(), gain = state.audio.createGain(); const midi = w.spectral_receiver.midi_pitch; osc.frequency.value = 440 * 2 ** ((midi - 69) / 12); osc.type = "sine"; gain.gain.setValueAtTime(0.0001, start); gain.gain.exponentialRampToValueAtTime(Math.max(.025, w.spectral_receiver.midi_velocity / 1270), start + .015); gain.gain.exponentialRampToValueAtTime(.0001, start + .22); osc.connect(gain).connect(state.audio.destination); osc.start(start); osc.stop(start + .24); });
}

$("analyze").addEventListener("click", analyze);
$("loadFixture").addEventListener("click", () => { $("fasta").value = fixtureFasta; $("vcf").value = fixtureVcf; $("windowSize").value = 303; $("stride").value = 303; $("frameOrigin").value = 1; setStatus("Sealed 606-base fixture loaded."); });
$("play").addEventListener("click", play);
document.querySelectorAll("[data-download]").forEach(button => button.addEventListener("click", () => { const key = button.dataset.download, item = state.artifacts?.[key]; if (!item) return; const names = { report:"report.json", windows:"windows.csv", variants:"variants.csv", midi:"spectrum.mid", manifest:"manifest.json" }; const types = { report:"application/json", windows:"text/csv", variants:"text/csv", midi:"audio/midi", manifest:"application/json" }; download(names[key], item, types[key]); }));
window.addEventListener("resize", () => state.artifacts && drawChart(state.artifacts.reportObject.windows));
if ("serviceWorker" in navigator && location.protocol !== "file:") navigator.serviceWorker.register("./sw.js").catch(console.warn);
