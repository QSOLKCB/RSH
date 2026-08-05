import {
  compactTrajectory,
  compareAttitudeTrajectories,
  integrateDzhanibekov,
  integrateJitterbugAnalogue,
  quaternionDistance,
  quaternionRotate,
} from "./attitude-model.js";

const elements = {
  form: document.querySelector("#attitude-controls"),
  shapePeriod: document.querySelector("#shape-period"),
  shapePeriodValue: document.querySelector("#shape-period-value"),
  tilt: document.querySelector("#tilt"),
  tiltValue: document.querySelector("#tilt-value"),
  omegaY: document.querySelector("#omega-y"),
  omegaYValue: document.querySelector("#omega-y-value"),
  message: document.querySelector("#attitude-message"),
  canvas: document.querySelector("#attitude-canvas"),
  play: document.querySelector("#play"),
  rate: document.querySelector("#rate"),
  time: document.querySelector("#time"),
  timeValue: document.querySelector("#time-value"),
  verdict: document.querySelector("#verdict"),
  download: document.querySelector("#download-attitude"),
  rms: document.querySelector("#metric-rms"),
  correlation: document.querySelector("#metric-correlation"),
  dzFlips: document.querySelector("#metric-dz-flips"),
  jbFlips: document.querySelector("#metric-jb-flips"),
  dzL: document.querySelector("#metric-dz-l"),
  dzE: document.querySelector("#metric-dz-e"),
  jbL: document.querySelector("#metric-jb-l"),
  jbE: document.querySelector("#metric-jb-e"),
  scale: document.querySelector("#metric-scale"),
};

const context = elements.canvas.getContext("2d");
let study = null;
let playing = true;
let sampleIndex = 0;
let lastFrame = performance.now();
let accumulator = 0;

function scientific(value, digits = 3) {
  return Number(value).toExponential(digits);
}

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function rotateView(point, yaw, pitch) {
  const cy = Math.cos(yaw);
  const sy = Math.sin(yaw);
  const cp = Math.cos(pitch);
  const sp = Math.sin(pitch);
  const x = cy * point[0] + sy * point[2];
  const z1 = -sy * point[0] + cy * point[2];
  return [x, cp * point[1] - sp * z1, sp * point[1] + cp * z1];
}

function project(point, viewport, yaw, pitch, scale = 1) {
  const rotated = rotateView(point, yaw, pitch);
  const perspective = 1 / (1 + Math.max(-0.8, rotated[2]) * 0.12);
  return [
    viewport.cx + rotated[0] * viewport.scale * perspective * scale,
    viewport.cy - rotated[1] * viewport.scale * perspective * scale,
    rotated[2],
  ];
}

function drawLine(left, right, viewport, yaw, pitch, stroke, width = 1, alpha = 1) {
  const a = project(left, viewport, yaw, pitch);
  const b = project(right, viewport, yaw, pitch);
  context.save();
  context.globalAlpha = alpha;
  context.strokeStyle = stroke;
  context.lineWidth = width;
  context.beginPath();
  context.moveTo(a[0], a[1]);
  context.lineTo(b[0], b[1]);
  context.stroke();
  context.restore();
}

function bodyPoint(sample, point, tilt = 0) {
  const cosine = Math.cos(tilt);
  const sine = Math.sin(tilt);
  const tilted = [
    cosine * point[0] + sine * point[2],
    point[1],
    -sine * point[0] + cosine * point[2],
  ];
  return quaternionRotate(sample.quaternion, tilted);
}

function drawInertiaWireframe(sample, viewport, options) {
  const moments = sample.principal_moments;
  const maximum = Math.max(...moments);
  const radii = moments.map((value) => 1.15 * Math.sqrt(maximum / value));
  const tilt = options.tilt ?? 0;
  const rings = 32;
  const yaw = -0.48 + 0.1 * Math.sin(sample.time * 0.07);
  const pitch = 0.35;

  for (const plane of [0, 1, 2]) {
    let previous = null;
    for (let index = 0; index <= rings; index += 1) {
      const angle = index * Math.PI * 2 / rings;
      const point = [0, 0, 0];
      const axes = [0, 1, 2].filter((axis) => axis !== plane);
      point[axes[0]] = radii[axes[0]] * Math.cos(angle);
      point[axes[1]] = radii[axes[1]] * Math.sin(angle);
      const transformed = bodyPoint(sample, point, tilt);
      if (previous) {
        drawLine(previous, transformed, viewport, yaw, pitch, options.stroke, 1, 0.42);
      }
      previous = transformed;
    }
  }

  const axisVectors = [
    [1.7, 0, 0],
    [0, 1.7, 0],
    [0, 0, 1.7],
  ];
  const axisStyles = [options.primary, options.secondary, "#a9b4b8"];
  axisVectors.forEach((axis, index) => {
    drawLine(
      [0, 0, 0],
      bodyPoint(sample, axis, tilt),
      viewport,
      yaw,
      pitch,
      axisStyles[index],
      2.4,
      0.95,
    );
  });
}

function drawGrid(width, height) {
  context.fillStyle = "#070e12";
  context.fillRect(0, 0, width, height);
  context.strokeStyle = "rgba(145,164,170,0.08)";
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
}

function drawText(text, x, y, style = "#e8f0f1", font = "700 13px ui-monospace") {
  context.fillStyle = style;
  context.font = font;
  context.fillText(text, x, y);
}

function drawTimeline(width, height, dzSamples, jbSamples, index) {
  const left = 42;
  const right = width - 32;
  const top = height - 175;
  const bottom = height - 32;
  const chartHeight = bottom - top;
  const duration = Math.min(dzSamples.at(-1).time, jbSamples.at(-1).time);

  context.fillStyle = "rgba(7,14,18,0.9)";
  context.fillRect(left, top, right - left, chartHeight);
  context.strokeStyle = "#24353e";
  context.strokeRect(left, top, right - left, chartHeight);

  const series = [
    { samples: dzSamples, stroke: "#65d9c0", dash: [] },
    { samples: jbSamples, stroke: "#e2a65b", dash: [7, 5] },
  ];
  for (const item of series) {
    context.save();
    context.strokeStyle = item.stroke;
    context.lineWidth = 1.8;
    context.setLineDash(item.dash);
    context.beginPath();
    item.samples.forEach((sample, sampleNumber) => {
      const excursion = quaternionDistance(item.samples[0].quaternion, sample.quaternion);
      const x = left + (sample.time / duration) * (right - left);
      const y = bottom - (excursion / Math.PI) * chartHeight;
      if (sampleNumber === 0) context.moveTo(x, y);
      else context.lineTo(x, y);
    });
    context.stroke();
    context.restore();
  }

  const currentTime = dzSamples[index]?.time ?? 0;
  const cursorX = left + currentTime / duration * (right - left);
  context.strokeStyle = "rgba(232,240,241,0.75)";
  context.beginPath();
  context.moveTo(cursorX, top);
  context.lineTo(cursorX, bottom);
  context.stroke();

  drawText("ATTITUDE EXCURSION FROM INITIAL ORIENTATION", left, top - 10, "#91a4aa", "700 11px ui-monospace");
  drawText("180°", left + 6, top + 16, "#91a4aa", "11px ui-monospace");
  drawText("0°", left + 6, bottom - 7, "#91a4aa", "11px ui-monospace");
  drawText("RIGID", right - 148, top + 17, "#65d9c0", "700 11px ui-monospace");
  drawText("ANALOGUE", right - 82, top + 17, "#e2a65b", "700 11px ui-monospace");
}

function draw() {
  const width = elements.canvas.width;
  const height = elements.canvas.height;
  drawGrid(width, height);

  if (!study) {
    drawText("CALCULATING TRAJECTORIES…", 44, 56, "#91a4aa");
    return;
  }

  const dzSample = study.dzhanibekov.samples[sampleIndex];
  const jbSample = study.jitterbug.samples[sampleIndex];
  const bodyHeight = height - 205;
  const dzViewport = { cx: width * 0.25, cy: bodyHeight * 0.53, scale: bodyHeight * 0.13 };
  const jbViewport = { cx: width * 0.75, cy: bodyHeight * 0.53, scale: bodyHeight * 0.13 };

  context.strokeStyle = "#263942";
  context.beginPath();
  context.moveTo(width / 2, 24);
  context.lineTo(width / 2, bodyHeight - 12);
  context.stroke();

  drawInertiaWireframe(dzSample, dzViewport, {
    stroke: "#65d9c0",
    primary: "#65d9c0",
    secondary: "#d6e3e4",
  });
  drawInertiaWireframe(jbSample, jbViewport, {
    stroke: "#e2a65b",
    primary: "#e2a65b",
    secondary: "#d6e3e4",
    tilt: jbSample.principal_axis_tilt,
  });

  drawText("TORQUE-FREE RIGID BODY", 34, 38, "#65d9c0");
  drawText("VARIABLE-INERTIA ANALOGUE", width / 2 + 34, 38, "#e2a65b");
  drawText(`|ω| ${Math.hypot(...dzSample.omega).toFixed(3)}`, 34, 60, "#91a4aa", "12px ui-monospace");
  drawText(`λ ${jbSample.lambda.toFixed(3)} · tilt ${jbSample.principal_axis_tilt.toFixed(3)} rad`, width / 2 + 34, 60, "#91a4aa", "12px ui-monospace");

  const dzExcursion = quaternionDistance(study.dzhanibekov.samples[0].quaternion, dzSample.quaternion) * 180 / Math.PI;
  const jbExcursion = quaternionDistance(study.jitterbug.samples[0].quaternion, jbSample.quaternion) * 180 / Math.PI;
  drawText(`${dzExcursion.toFixed(1)}°`, dzViewport.cx - 30, bodyHeight - 32, "#dce7e8", "800 22px ui-monospace");
  drawText(`${jbExcursion.toFixed(1)}°`, jbViewport.cx - 30, bodyHeight - 32, "#dce7e8", "800 22px ui-monospace");

  drawTimeline(width, height, study.dzhanibekov.samples, study.jitterbug.samples, sampleIndex);
}

function updateMetrics() {
  const comparison = study.comparison;
  const best = comparison.best_alignment;
  const bestExcursion = comparison.best_excursion_alignment;
  elements.verdict.textContent = comparison.verdict;
  elements.verdict.dataset.kind = comparison.verdict.startsWith("PARTIAL")
    ? "partial"
    : comparison.verdict.startsWith("STRONG") ? "strong" : "none";
  elements.rms.textContent = `${best.quaternion_distance.rms_deg.toFixed(2)}°`;
  elements.correlation.textContent = bestExcursion.attitude_excursion_correlation.toFixed(3);
  elements.dzFlips.textContent = String(study.dzhanibekov.attitude_reversals_approx_180deg.length);
  elements.jbFlips.textContent = String(study.jitterbug.attitude_reversals_approx_180deg.length);
  elements.dzL.textContent = scientific(study.dzhanibekov.invariants.angular_momentum.relative_drift);
  elements.dzE.textContent = scientific(study.dzhanibekov.invariants.energy.relative_drift);
  elements.jbL.textContent = scientific(study.jitterbug.invariants.angular_momentum.relative_drift);
  elements.jbE.textContent = scientific(study.jitterbug.invariants.energy.relative_drift);
  elements.scale.textContent = `${best.time_scale_factor.toFixed(2)}× · shift ${best.time_shift.toFixed(1)} s`;
  elements.download.disabled = false;
}

function updateControlLabels() {
  elements.shapePeriodValue.textContent = Number(elements.shapePeriod.value).toFixed(2);
  elements.tiltValue.textContent = Number(elements.tilt.value).toFixed(2);
  elements.omegaYValue.textContent = Number(elements.omegaY.value).toFixed(2);
}

function recompute() {
  updateControlLabels();
  elements.message.textContent = "Integrating two 40-second quaternion trajectories…";
  elements.message.dataset.kind = "";
  elements.download.disabled = true;
  try {
    const dzhanibekov = integrateDzhanibekov();
    const jitterbug = integrateJitterbugAnalogue({
      shapePeriod: Number(elements.shapePeriod.value),
      axisTiltAmplitude: Number(elements.tilt.value),
      omega0: [0.08, Number(elements.omegaY.value), 0.05],
    });
    const comparison = compareAttitudeTrajectories(dzhanibekov, jitterbug);
    study = { dzhanibekov, jitterbug, comparison };
    sampleIndex = 0;
    elements.time.max = String(Math.min(dzhanibekov.samples.length, jitterbug.samples.length) - 1);
    elements.time.value = "0";
    elements.message.textContent = `Complete: ${comparison.verdict.toLowerCase()}.`;
    elements.message.dataset.kind = "pass";
    updateMetrics();
    draw();
  } catch (error) {
    elements.message.textContent = `Rejected: ${error.message}`;
    elements.message.dataset.kind = "fail";
    elements.verdict.textContent = "REJECTED";
    elements.verdict.dataset.kind = "none";
    console.error(error);
  }
}

function downloadStudy() {
  if (!study) return;
  const payload = {
    schema: "RSH-ATTITUDE-EXPLORATORY-BROWSER-SIDECAR-V1",
    generated_at: new Date().toISOString(),
    verdict: study.comparison.verdict,
    dzhanibekov: compactTrajectory(study.dzhanibekov),
    jitterbug_analogue: compactTrajectory(study.jitterbug),
    comparison: study.comparison,
    display_only_visualization: true,
    actual_fuller_jitterbug_mechanism: false,
    geometry_receipt_authority: false,
    physical_equivalence_claim: false,
    universal_scale_invariance_claim: false,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "rsh-jitterbug-dzhanibekov-exploratory.json";
  anchor.click();
  URL.revokeObjectURL(url);
}

function animate(now) {
  if (study && playing) {
    const elapsed = Math.min(0.1, (now - lastFrame) / 1000);
    accumulator += elapsed * Number(elements.rate.value);
    const sampleStep = study.dzhanibekov.samples[1].time - study.dzhanibekov.samples[0].time;
    while (accumulator >= sampleStep) {
      accumulator -= sampleStep;
      sampleIndex = (sampleIndex + 1) % Math.min(
        study.dzhanibekov.samples.length,
        study.jitterbug.samples.length,
      );
    }
    elements.time.value = String(sampleIndex);
    elements.timeValue.textContent = `${study.dzhanibekov.samples[sampleIndex].time.toFixed(2)} s`;
    draw();
  }
  lastFrame = now;
  requestAnimationFrame(animate);
}

elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  recompute();
});
for (const control of [elements.shapePeriod, elements.tilt, elements.omegaY]) {
  control.addEventListener("input", updateControlLabels);
}
elements.play.addEventListener("click", () => {
  playing = !playing;
  elements.play.textContent = playing ? "Pause" : "Play";
});
elements.time.addEventListener("input", () => {
  if (!study) return;
  sampleIndex = clamp(Number(elements.time.value), 0, study.dzhanibekov.samples.length - 1);
  elements.timeValue.textContent = `${study.dzhanibekov.samples[sampleIndex].time.toFixed(2)} s`;
  draw();
});
elements.download.addEventListener("click", downloadStudy);

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("./sw.js").catch(() => undefined);
}

updateControlLabels();
setTimeout(recompute, 0);
requestAnimationFrame(animate);
