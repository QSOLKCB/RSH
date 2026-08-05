import { CLAIMS, TETRAHEDRON_VERTICES, buildArtifacts } from "./model.js";

const form = document.querySelector("#codec-form");
const sequenceInput = document.querySelector("#sequence");
const status = document.querySelector("#status");
const tableBody = document.querySelector("#records");
const canvas = document.querySelector("#lattice");
const context = canvas.getContext("2d");
const playButton = document.querySelector("#play");
const stopButton = document.querySelector("#stop");
const downloads = {
  report: document.querySelector("#download-report"),
  csv: document.querySelector("#download-csv"),
  midi: document.querySelector("#download-midi"),
  manifest: document.querySelector("#download-manifest"),
};

let artifacts = null;
let rotation = -0.7;
const pitchAngle = 0.35;
let dragging = false;
let dragX = 0;
let audioContext = null;
let activeNodes = [];

function setStatus(message, kind = "") {
  status.textContent = message;
  status.className = `status ${kind}`.trim();
}

function download(name, payload, type) {
  const blob = payload instanceof Blob ? payload : new Blob([payload], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

function renderClaims() {
  const grid = document.querySelector("#claims-grid");
  grid.replaceChildren(...Object.entries(CLAIMS).map(([name, value]) => {
    const row = document.createElement("div");
    row.className = "claim";
    const label = document.createElement("span");
    label.textContent = name;
    const state = document.createElement("strong");
    state.textContent = String(value).toUpperCase();
    row.append(label, state);
    return row;
  }));
}

function updateEvidence(current) {
  document.querySelector("#metric-bases").textContent = current.sequence.length;
  document.querySelector("#metric-codons").textContent = current.sequence.length / 3;
  document.querySelector("#metric-events").textContent = current.records.length;
  document.querySelector("#metric-roundtrip").textContent = current.manifest.round_trip_verified ? "PASS" : "FAIL";
  document.querySelector("#metric-report-hash").textContent = current.manifest.report_canonical_sha256;
  document.querySelector("#metric-midi-hash").textContent = current.manifest.midi_sha256;
  document.querySelector("#visual-count").textContent = `${current.records.length} BASES`;
  tableBody.replaceChildren(...current.records.map((record) => {
    const row = document.createElement("tr");
    const values = [
      record.base_index,
      record.codon,
      record.base,
      record.site_index,
      record.fibre_label,
      record.event_index,
      record.midi_pitch,
      `${record.x}, ${record.y}, ${record.z}`,
    ];
    row.replaceChildren(...values.map((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      return cell;
    }));
    return row;
  }));
}

function project(point, width, height) {
  const centred = point.map((value) => value - 0.5);
  const cosY = Math.cos(rotation);
  const sinY = Math.sin(rotation);
  const x1 = centred[0] * cosY - centred[2] * sinY;
  const z1 = centred[0] * sinY + centred[2] * cosY;
  const cosX = Math.cos(pitchAngle);
  const sinX = Math.sin(pitchAngle);
  const y2 = centred[1] * cosX - z1 * sinX;
  const z2 = centred[1] * sinX + z1 * cosX;
  const scale = Math.min(width, height) * 0.72 / (1.35 + z2 * 0.25);
  return [width / 2 + x1 * scale, height / 2 - y2 * scale, z2];
}

function draw() {
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(1, Math.round(rect.width * ratio));
  const height = Math.max(1, Math.round(rect.height * ratio));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  context.clearRect(0, 0, width, height);
  context.fillStyle = "#071014";
  context.fillRect(0, 0, width, height);
  context.lineCap = "round";
  context.lineJoin = "round";

  const vertices = Object.entries(TETRAHEDRON_VERTICES)
    .map(([base, point]) => ({ base, projected: project(point, width, height) }));
  const edges = [[0, 1], [0, 2], [0, 3], [1, 2], [1, 3], [2, 3]];
  context.strokeStyle = "rgba(111,212,219,.32)";
  context.lineWidth = 1.2 * ratio;
  for (const [left, right] of edges) {
    context.beginPath();
    context.moveTo(vertices[left].projected[0], vertices[left].projected[1]);
    context.lineTo(vertices[right].projected[0], vertices[right].projected[1]);
    context.stroke();
  }
  context.font = `${12 * ratio}px ui-monospace, monospace`;
  context.fillStyle = "#e8bd67";
  for (const vertex of vertices) {
    context.beginPath();
    context.arc(vertex.projected[0], vertex.projected[1], 4 * ratio, 0, Math.PI * 2);
    context.fill();
    context.fillText(vertex.base, vertex.projected[0] + 8 * ratio, vertex.projected[1] - 8 * ratio);
  }

  if (artifacts) {
    const projected = artifacts.records.map((record) => project(
      [Number(record.x), Number(record.y), Number(record.z)], width, height,
    ));
    context.strokeStyle = "rgba(232,189,103,.72)";
    context.lineWidth = 1.8 * ratio;
    context.beginPath();
    projected.forEach((point, index) => {
      if (index === 0) context.moveTo(point[0], point[1]);
      else context.lineTo(point[0], point[1]);
    });
    context.stroke();
    const order = projected.map((point, index) => ({ point, index }))
      .sort((left, right) => left.point[2] - right.point[2]);
    for (const { point, index } of order) {
      const fibre = artifacts.records[index].fibre_label;
      context.fillStyle = ["#6fd4db", "#e8bd67", "#8fd19e"][fibre];
      context.beginPath();
      context.arc(point[0], point[1], (3.2 + fibre * 0.4) * ratio, 0, Math.PI * 2);
      context.fill();
    }
  }
  requestAnimationFrame(draw);
}

function stopAudio() {
  for (const node of activeNodes) {
    try { node.stop(); } catch { /* already stopped */ }
  }
  activeNodes = [];
  stopButton.disabled = true;
}

async function play() {
  if (!artifacts) return;
  stopAudio();
  audioContext ??= new AudioContext();
  await audioContext.resume();
  const now = audioContext.currentTime + 0.05;
  for (const record of artifacts.records) {
    const start = now + record.base_index * 0.12;
    const duration = record.scl_value < 0 ? 0.24 : 0.18;
    const oscillator = audioContext.createOscillator();
    const gain = audioContext.createGain();
    oscillator.type = ["sine", "triangle", "sawtooth"][record.fibre_label];
    oscillator.frequency.value = 440 * (2 ** ((record.midi_pitch - 69) / 12));
    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.exponentialRampToValueAtTime(0.11, start + 0.012);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
    oscillator.connect(gain).connect(audioContext.destination);
    oscillator.start(start);
    oscillator.stop(start + duration + 0.02);
    activeNodes.push(oscillator);
  }
  stopButton.disabled = false;
  window.setTimeout(stopAudio, artifacts.records.length * 120 + 500);
}

async function run(event) {
  event?.preventDefault();
  setStatus("Encoding, hashing, and verifying the MIDI round trip…");
  try {
    artifacts = await buildArtifacts(sequenceInput.value);
    updateEvidence(artifacts);
    for (const button of [playButton, ...Object.values(downloads)]) button.disabled = false;
    setStatus(`PASS · ${artifacts.records.length} bases · exact DNA → MIDI → DNA round trip`, "pass");
  } catch (error) {
    artifacts = null;
    tableBody.replaceChildren();
    for (const button of [playButton, stopButton, ...Object.values(downloads)]) button.disabled = true;
    setStatus(error instanceof Error ? error.message : String(error), "fail");
  }
}

form.addEventListener("submit", run);
playButton.addEventListener("click", play);
stopButton.addEventListener("click", stopAudio);
downloads.report.addEventListener("click", () => download("rsh-dna-midi-report.json", `${JSON.stringify(artifacts.report, null, 2)}\n`, "application/json"));
downloads.csv.addEventListener("click", () => download("rsh-dna-midi-mapping.csv", artifacts.csv, "text/csv"));
downloads.midi.addEventListener("click", () => download("rsh-dna-midi.mid", artifacts.midi, "audio/midi"));
downloads.manifest.addEventListener("click", () => download("rsh-dna-midi-manifest.json", `${JSON.stringify(artifacts.manifest, null, 2)}\n`, "application/json"));
canvas.addEventListener("pointerdown", (event) => { dragging = true; dragX = event.clientX; canvas.setPointerCapture(event.pointerId); });
canvas.addEventListener("pointermove", (event) => {
  if (!dragging) return;
  rotation += (event.clientX - dragX) * 0.008;
  dragX = event.clientX;
});
canvas.addEventListener("pointerup", () => { dragging = false; });
canvas.addEventListener("pointercancel", () => { dragging = false; });

renderClaims();
draw();
run();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("./sw.js").catch((error) => {
    console.info("DNA-MIDI offline cache registration was unavailable.", error);
  }));
}
