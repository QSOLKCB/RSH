import {
  CLAIMS,
  canonicalJson,
  validateWitness,
  wordToWitness,
} from "./model.js";

const $ = id => document.getElementById(id);
const state = { witness: null };
const triangle = [
  [0, 0],
  [1, 0],
  [0.5, Math.sqrt(3) / 2],
];
const centre = [0.5, Math.sqrt(3) / 6];
const circumradius = 1 / Math.sqrt(3);

function parseWord(text) {
  const compact = text.trim().toLowerCase().replace(/^0x/u, "");
  if (!/^[0-9a-f]{1,8}$/u.test(compact)) {
    throw new Error("word must contain one to eight hexadecimal digits");
  }
  return Number.parseInt(compact, 16) >>> 0;
}

function barycentricPoint(value) {
  const denominator = Number(value.denominator);
  const weights = value.numerators.map(item => Number(item) / denominator);
  return [
    weights.reduce((sum, weight, index) => sum + weight * triangle[index][0], 0),
    weights.reduce((sum, weight, index) => sum + weight * triangle[index][1], 0),
  ];
}

function rationalText(value) {
  return `[${value.numerators.join(", ")}] / ${value.denominator}`;
}

function renderClaims() {
  const container = $("claims");
  container.replaceChildren(...Object.entries(CLAIMS).map(([name, value]) => {
    const row = document.createElement("div");
    row.className = "claim";
    const label = document.createElement("span");
    label.textContent = name;
    const stateValue = document.createElement("strong");
    stateValue.textContent = String(value).toUpperCase();
    row.append(label, stateValue);
    return row;
  }));
}

function setStatus(message, kind = "") {
  $("status").textContent = message;
  $("status").className = kind;
}

function renderWitness(witness) {
  $("metric-word").textContent = `0x${witness.word_hex}`;
  $("metric-axis").textContent = `${witness.fibre_label} · ${witness.reflection_axis}`;
  $("metric-product").textContent = `${witness.squared_radius_product.numerator}/${witness.squared_radius_product.denominator}`;
  $("metric-double").textContent = witness.double_conjugation_verified ? "PASS" : "FAIL";
  $("cell-hash").textContent = witness.source_cell_canonical_sha256;
  $("source-rational").textContent = rationalText(witness.source_centroid_barycentric);
  $("conjugate-rational").textContent = rationalText(witness.conjugate_barycentric);
  $("recovered-rational").textContent = rationalText(witness.double_application_barycentric);
  $("receipt").textContent = JSON.stringify(witness, null, 2);
  $("badge").textContent = "EXACT PASS";
  $("download").disabled = false;
}

function fittedTransform(points, width, height) {
  const padding = 64;
  const xs = points.map(point => point[0]);
  const ys = points.map(point => point[1]);
  let minX = Math.min(...xs);
  let maxX = Math.max(...xs);
  let minY = Math.min(...ys);
  let maxY = Math.max(...ys);
  const spanX = Math.max(0.25, maxX - minX);
  const spanY = Math.max(0.25, maxY - minY);
  minX -= spanX * 0.12;
  maxX += spanX * 0.12;
  minY -= spanY * 0.12;
  maxY += spanY * 0.12;
  const scale = Math.min(
    (width - 2 * padding) / (maxX - minX),
    (height - 2 * padding) / (maxY - minY),
  );
  return point => [
    padding + (point[0] - minX) * scale,
    height - padding - (point[1] - minY) * scale,
  ];
}

function draw() {
  const canvas = $("diagram");
  const context = canvas.getContext("2d");
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(1, Math.round(rect.width * ratio));
  const height = Math.max(1, Math.round(rect.height * ratio));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  context.clearRect(0, 0, width, height);
  context.fillStyle = "#060b0e";
  context.fillRect(0, 0, width, height);

  const witness = state.witness;
  const source = witness ? barycentricPoint(witness.source_centroid_barycentric) : triangle[0];
  const conjugate = witness ? barycentricPoint(witness.conjugate_barycentric) : triangle[1];
  const recovered = witness ? barycentricPoint(witness.double_application_barycentric) : source;
  const circleBounds = [
    [centre[0] - circumradius, centre[1]],
    [centre[0] + circumradius, centre[1]],
    [centre[0], centre[1] - circumradius],
    [centre[0], centre[1] + circumradius],
  ];
  const project = fittedTransform([...triangle, ...circleBounds, source, conjugate, recovered], width, height);
  const projectedTriangle = triangle.map(project);
  const projectedCentre = project(centre);

  context.lineJoin = "round";
  context.lineCap = "round";
  context.strokeStyle = "rgba(103,203,209,.45)";
  context.lineWidth = 1.5 * ratio;
  context.beginPath();
  context.moveTo(...projectedTriangle[0]);
  context.lineTo(...projectedTriangle[1]);
  context.lineTo(...projectedTriangle[2]);
  context.closePath();
  context.stroke();

  const radiusPixels = Math.hypot(
    project([centre[0] + circumradius, centre[1]])[0] - projectedCentre[0],
    project([centre[0] + circumradius, centre[1]])[1] - projectedCentre[1],
  );
  context.strokeStyle = "rgba(229,184,93,.35)";
  context.setLineDash([7 * ratio, 7 * ratio]);
  context.beginPath();
  context.arc(projectedCentre[0], projectedCentre[1], radiusPixels, 0, Math.PI * 2);
  context.stroke();
  context.setLineDash([]);

  const fibre = witness?.fibre_label ?? 0;
  const axisVertex = triangle[fibre];
  const axisDirection = [axisVertex[0] - centre[0], axisVertex[1] - centre[1]];
  const axisStart = project([centre[0] - axisDirection[0] * 3, centre[1] - axisDirection[1] * 3]);
  const axisEnd = project([centre[0] + axisDirection[0] * 3, centre[1] + axisDirection[1] * 3]);
  context.strokeStyle = "rgba(134,208,154,.55)";
  context.lineWidth = 1.2 * ratio;
  context.beginPath();
  context.moveTo(...axisStart);
  context.lineTo(...axisEnd);
  context.stroke();

  if (witness) {
    const sourceProjected = project(source);
    const conjugateProjected = project(conjugate);
    const recoveredProjected = project(recovered);
    context.strokeStyle = "rgba(236,242,243,.35)";
    context.beginPath();
    context.moveTo(...projectedCentre);
    context.lineTo(...sourceProjected);
    context.moveTo(...projectedCentre);
    context.lineTo(...conjugateProjected);
    context.stroke();

    const point = (coordinates, fill, radius) => {
      context.fillStyle = fill;
      context.beginPath();
      context.arc(coordinates[0], coordinates[1], radius * ratio, 0, Math.PI * 2);
      context.fill();
    };
    point(sourceProjected, "#67cbd1", 5);
    point(conjugateProjected, "#e5b85d", 5);
    context.strokeStyle = "#86d09a";
    context.lineWidth = 2 * ratio;
    context.beginPath();
    context.arc(recoveredProjected[0], recoveredProjected[1], 9 * ratio, 0, Math.PI * 2);
    context.stroke();
  }

  context.fillStyle = "#e5b85d";
  context.beginPath();
  context.arc(projectedCentre[0], projectedCentre[1], 3.5 * ratio, 0, Math.PI * 2);
  context.fill();
}

async function run(event) {
  event?.preventDefault();
  $("download").disabled = true;
  setStatus("Computing exact rational witness…");
  try {
    const word = parseWord($("word").value);
    const fibre = Number($("fibre").value);
    const witness = await wordToWitness(word, fibre);
    await validateWitness(witness);
    state.witness = witness;
    renderWitness(witness);
    draw();
    setStatus("PASS · radius product 1/9 · second application recovered the source", "pass");
  } catch (error) {
    state.witness = null;
    $("badge").textContent = "REJECTED";
    $("receipt").textContent = "No valid witness generated.";
    setStatus(`REJECTED · ${error instanceof Error ? error.message : String(error)}`, "fail");
    draw();
  }
}

function downloadWitness() {
  if (!state.witness) return;
  const blob = new Blob([`${canonicalJson(state.witness)}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `rsh-f32-inversive-${state.witness.word_hex}-f${state.witness.fibre_label}.json`;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

$("witness-form").addEventListener("submit", run);
$("download").addEventListener("click", downloadWitness);
window.addEventListener("resize", draw);
renderClaims();
draw();
run();

if ("serviceWorker" in navigator && location.protocol !== "file:") {
  navigator.serviceWorker.register("./sw.js").catch(error => {
    console.info("Inversive witness offline cache unavailable.", error);
  });
}
