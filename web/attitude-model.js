const TAU = 2 * Math.PI;
const EPSILON = 1e-15;
const MAX_INTEGRATION_STEPS = 2_000_000;
const MAX_OUTPUT_SAMPLES = 200_001;
const MIN_COMPARISON_SAMPLES = 50;
const MAX_COMPARISON_SAMPLES = 10_000;
const MAX_ALIGNMENT_CANDIDATES = 256;

export const ATTITUDE_SCHEMA = "RSH-ATTITUDE-COMPARISON-EXPLORATORY-V1";
export const DEFAULT_DZHANIBEKOV = Object.freeze({
  inertia: [1.0, 2.0, 3.0],
  omega0: [0.05, 1.0, 0.02],
  quaternion0: [0, 0, 0, 1],
  duration: 40,
  dt: 0.002,
  outputStride: 10,
});
export const DEFAULT_JITTERBUG = Object.freeze({
  inertiaClosed: [1.0, 1.2, 2.8],
  inertiaOpen: [1.0, 2.6, 2.9],
  axisTiltAmplitude: 0.4,
  shapePeriod: 8.0,
  omega0: [0.08, 0.95, 0.05],
  quaternion0: [0, 0, 0, 1],
  duration: 40,
  dt: 0.002,
  outputStride: 10,
});
export const CLAIM_BOUNDARIES = Object.freeze({
  jitterbug_is_dzhanibekov: false,
  proves_quantized_spacetime: false,
  visual_similarity_establishes_identical_dynamics: false,
  rsh_contains_validated_jitterbug_dynamics: false,
  geometry_receipt_authority: false,
  universal_scale_invariance_claim: false,
  physical_equivalence_claim: false,
});

function finiteNumber(value, label) {
  if (!Number.isFinite(value)) throw new Error(`${label} must be finite`);
  return value;
}

function positive(value, label) {
  finiteNumber(value, label);
  if (value <= 0) throw new Error(`${label} must be positive`);
  return value;
}

function integerInRange(value, label, minimum, maximum) {
  if (!Number.isFinite(value) || !Number.isInteger(value)) {
    throw new Error(`${label} must be a finite integer`);
  }
  if (value < minimum || value > maximum) {
    throw new Error(`${label} must be in [${minimum}, ${maximum}]`);
  }
  return value;
}

function vector3(value, label) {
  if (!Array.isArray(value) || value.length !== 3) {
    throw new Error(`${label} must contain three numbers`);
  }
  return value.map((entry, index) => finiteNumber(entry, `${label}[${index}]`));
}

function quaternion4(value, label) {
  if (!Array.isArray(value) || value.length !== 4) {
    throw new Error(`${label} must contain four numbers`);
  }
  const result = value.map((entry, index) => finiteNumber(entry, `${label}[${index}]`));
  return normalizeQuaternion(result);
}

function add3(left, right) {
  return [left[0] + right[0], left[1] + right[1], left[2] + right[2]];
}

function scale3(value, scalar) {
  return [value[0] * scalar, value[1] * scalar, value[2] * scalar];
}

function dot3(left, right) {
  return left[0] * right[0] + left[1] * right[1] + left[2] * right[2];
}

function cross3(left, right) {
  return [
    left[1] * right[2] - left[2] * right[1],
    left[2] * right[0] - left[0] * right[2],
    left[0] * right[1] - left[1] * right[0],
  ];
}

function norm3(value) {
  return Math.hypot(value[0], value[1], value[2]);
}

function matVec(matrix, vector) {
  return matrix.map((row) => dot3(row, vector));
}

function matMul(left, right) {
  const transposed = [0, 1, 2].map((column) => right.map((row) => row[column]));
  return left.map((row) => transposed.map((column) => dot3(row, column)));
}

function matTranspose(matrix) {
  return [0, 1, 2].map((column) => matrix.map((row) => row[column]));
}

function matAdd(...matrices) {
  return [0, 1, 2].map((row) => [0, 1, 2].map((column) => (
    matrices.reduce((sum, matrix) => sum + matrix[row][column], 0)
  )));
}

function diagonal(values) {
  return [
    [values[0], 0, 0],
    [0, values[1], 0],
    [0, 0, values[2]],
  ];
}

function inverse3(matrix) {
  const [a, b, c] = matrix[0];
  const [d, e, f] = matrix[1];
  const [g, h, i] = matrix[2];
  const A = e * i - f * h;
  const B = c * h - b * i;
  const C = b * f - c * e;
  const D = f * g - d * i;
  const E = a * i - c * g;
  const F = c * d - a * f;
  const G = d * h - e * g;
  const H = b * g - a * h;
  const I = a * e - b * d;
  const determinant = a * A + b * D + c * G;
  if (!Number.isFinite(determinant) || Math.abs(determinant) <= EPSILON) {
    throw new Error("inertia tensor is singular");
  }
  const inverseDeterminant = 1 / determinant;
  return [
    [A * inverseDeterminant, B * inverseDeterminant, C * inverseDeterminant],
    [D * inverseDeterminant, E * inverseDeterminant, F * inverseDeterminant],
    [G * inverseDeterminant, H * inverseDeterminant, I * inverseDeterminant],
  ];
}

function rotationY(angle) {
  const cosine = Math.cos(angle);
  const sine = Math.sin(angle);
  return [
    [cosine, 0, sine],
    [0, 1, 0],
    [-sine, 0, cosine],
  ];
}

function rotationYDerivative(angle, angleRate) {
  const cosine = Math.cos(angle);
  const sine = Math.sin(angle);
  return [
    [-sine * angleRate, 0, cosine * angleRate],
    [0, 0, 0],
    [-cosine * angleRate, 0, -sine * angleRate],
  ];
}

export function quaternionMultiply(left, right) {
  const [lx, ly, lz, lw] = left;
  const [rx, ry, rz, rw] = right;
  return [
    lw * rx + rw * lx + ly * rz - lz * ry,
    lw * ry + rw * ly + lz * rx - lx * rz,
    lw * rz + rw * lz + lx * ry - ly * rx,
    lw * rw - lx * rx - ly * ry - lz * rz,
  ];
}

export function quaternionConjugate(value) {
  return [-value[0], -value[1], -value[2], value[3]];
}

export function normalizeQuaternion(value) {
  const magnitude = Math.hypot(...value);
  if (!Number.isFinite(magnitude) || magnitude <= EPSILON) {
    throw new Error("quaternion norm is zero or non-finite");
  }
  return value.map((component) => component / magnitude);
}

export function quaternionDistance(left, right) {
  const dot = Math.abs(
    left[0] * right[0]
      + left[1] * right[1]
      + left[2] * right[2]
      + left[3] * right[3],
  );
  return 2 * Math.acos(Math.min(1, Math.max(-1, dot)));
}

export function quaternionRotate(quaternion, vector) {
  const pure = [vector[0], vector[1], vector[2], 0];
  const rotated = quaternionMultiply(
    quaternionMultiply(quaternion, pure),
    quaternionConjugate(quaternion),
  );
  return rotated.slice(0, 3);
}

function quaternionDerivative(quaternion, omega) {
  return quaternionMultiply(quaternion, [omega[0], omega[1], omega[2], 0])
    .map((component) => 0.5 * component);
}

function combineState(state, derivative, scale) {
  return state.map((value, index) => value + derivative[index] * scale);
}

function rk4Step(derivative, time, state, dt) {
  const k1 = derivative(time, state);
  const k2 = derivative(time + dt / 2, combineState(state, k1, dt / 2));
  const k3 = derivative(time + dt / 2, combineState(state, k2, dt / 2));
  const k4 = derivative(time + dt, combineState(state, k3, dt));
  const next = state.map((value, index) => value + dt * (
    k1[index] + 2 * k2[index] + 2 * k3[index] + k4[index]
  ) / 6);
  const quaternion = normalizeQuaternion(next.slice(3, 7));
  return [...next.slice(0, 3), ...quaternion];
}

function summarizeSeries(values) {
  if (!Array.isArray(values) || values.length === 0) {
    throw new Error("summary series must contain at least one value");
  }
  let sum = 0;
  let minimum = Infinity;
  let maximum = -Infinity;
  for (const value of values) {
    finiteNumber(value, "summary series value");
    sum += value;
    minimum = Math.min(minimum, value);
    maximum = Math.max(maximum, value);
  }
  const mean = sum / values.length;
  let squaredDeviation = 0;
  for (const value of values) squaredDeviation += (value - mean) ** 2;
  return {
    mean,
    standard_deviation: Math.sqrt(squaredDeviation / values.length),
    minimum,
    maximum,
    relative_drift: Math.abs(maximum - minimum) / Math.max(Math.abs(mean), EPSILON),
  };
}

function detectSignCrossings(samples, axis) {
  const crossings = [];
  let previous = Math.sign(samples[0].omega[axis]);
  for (let index = 1; index < samples.length; index += 1) {
    const current = Math.sign(samples[index].omega[axis]);
    if (current !== 0 && previous !== 0 && current !== previous) {
      crossings.push({ index, time: samples[index].time });
    }
    if (current !== 0) previous = current;
  }
  return crossings;
}

function detectReversals(samples, thresholdDegrees = 170, cooldownSeconds = 2.0) {
  const threshold = thresholdDegrees * Math.PI / 180;
  const initial = samples[0].quaternion;
  const reversals = [];
  let lastTime = -Infinity;
  for (let index = 1; index < samples.length - 1; index += 1) {
    const previous = quaternionDistance(initial, samples[index - 1].quaternion);
    const current = quaternionDistance(initial, samples[index].quaternion);
    const next = quaternionDistance(initial, samples[index + 1].quaternion);
    if (
      current >= threshold
      && current >= previous
      && current >= next
      && samples[index].time - lastTime >= cooldownSeconds
    ) {
      reversals.push({
        index,
        time: samples[index].time,
        distance_rad: current,
        distance_deg: current * 180 / Math.PI,
      });
      lastTime = samples[index].time;
    }
  }
  return reversals;
}

function validateIntegrationConfig(config) {
  positive(config.duration, "duration");
  positive(config.dt, "dt");
  integerInRange(config.outputStride, "outputStride", 1, MAX_INTEGRATION_STEPS);
  const steps = Math.round(config.duration / config.dt);
  if (steps < 2 || steps > MAX_INTEGRATION_STEPS) {
    throw new Error(`integration step count must be in [2, ${MAX_INTEGRATION_STEPS}]`);
  }
  const regularOutputs = Math.floor(steps / config.outputStride) + 1;
  const emittedSamples = regularOutputs + (steps % config.outputStride === 0 ? 0 : 1);
  if (emittedSamples > MAX_OUTPUT_SAMPLES) {
    throw new Error(`emitted sample count must not exceed ${MAX_OUTPUT_SAMPLES}`);
  }
  return steps;
}

function integrateModel({ config, derivative, diagnostics, model, schema }) {
  const steps = validateIntegrationConfig(config);
  let state = [
    ...vector3(config.omega0, "omega0"),
    ...quaternion4(config.quaternion0, "quaternion0"),
  ];
  const samples = [];
  let maximumQuaternionError = 0;

  for (let step = 0; step <= steps; step += 1) {
    const time = step * config.dt;
    if (step % config.outputStride === 0 || step === steps) {
      const omega = state.slice(0, 3);
      const quaternion = state.slice(3, 7);
      const diagnostic = diagnostics(time, omega);
      const quaternionError = Math.abs(Math.hypot(...quaternion) - 1);
      maximumQuaternionError = Math.max(maximumQuaternionError, quaternionError);
      samples.push({
        time,
        quaternion: [...quaternion],
        omega: [...omega],
        ...diagnostic,
      });
    }
    if (step < steps) state = rk4Step(derivative, time, state, config.dt);
  }

  const angularMomentum = samples.map((sample) => sample.angular_momentum_norm);
  const energy = samples.map((sample) => sample.energy);
  return {
    schema,
    model,
    parameters: structuredClone(config),
    samples,
    invariants: {
      angular_momentum: summarizeSeries(angularMomentum),
      energy: summarizeSeries(energy),
      quaternion_normalization_error_max: maximumQuaternionError,
    },
    principal_axis_crossings: {
      x: detectSignCrossings(samples, 0),
      y: detectSignCrossings(samples, 1),
      z: detectSignCrossings(samples, 2),
    },
    attitude_reversals_approx_180deg: detectReversals(samples),
    claims: { ...CLAIM_BOUNDARIES },
  };
}

export function integrateDzhanibekov(overrides = {}) {
  const config = { ...DEFAULT_DZHANIBEKOV, ...overrides };
  const inertia = vector3(config.inertia, "inertia");
  inertia.forEach((value, index) => positive(value, `inertia[${index}]`));
  if (!(inertia[0] < inertia[1] && inertia[1] < inertia[2])) {
    throw new Error("Dzhanibekov profile requires I1 < I2 < I3");
  }

  const derivative = (_time, state) => {
    const [wx, wy, wz] = state;
    const [i1, i2, i3] = inertia;
    const omegaDerivative = [
      ((i2 - i3) / i1) * wy * wz,
      ((i3 - i1) / i2) * wz * wx,
      ((i1 - i2) / i3) * wx * wy,
    ];
    return [...omegaDerivative, ...quaternionDerivative(state.slice(3, 7), [wx, wy, wz])];
  };

  const diagnostics = (_time, omega) => {
    const angularMomentum = inertia.map((value, index) => value * omega[index]);
    return {
      angular_momentum_norm: norm3(angularMomentum),
      energy: 0.5 * dot3(omega, angularMomentum),
      principal_moments: [...inertia],
    };
  };

  return integrateModel({
    config,
    derivative,
    diagnostics,
    model: "torque-free rigid body intermediate-axis instability",
    schema: "RSH-EXPLORATORY-DZHANIBEKOV-RIGID-V1",
  });
}

export function jitterbugInertiaState(time, config) {
  const closed = vector3(config.inertiaClosed, "inertiaClosed");
  const open = vector3(config.inertiaOpen, "inertiaOpen");
  closed.forEach((value, index) => positive(value, `inertiaClosed[${index}]`));
  open.forEach((value, index) => positive(value, `inertiaOpen[${index}]`));
  positive(config.shapePeriod, "shapePeriod");
  finiteNumber(config.axisTiltAmplitude, "axisTiltAmplitude");

  const phase = TAU * time / config.shapePeriod;
  const lambda = 0.5 * (1 - Math.cos(phase));
  const lambdaRate = Math.PI * Math.sin(phase) / config.shapePeriod;
  const moments = closed.map((value, index) => value + lambda * (open[index] - value));
  const momentsRate = closed.map((_value, index) => lambdaRate * (open[index] - closed[index]));
  const angle = config.axisTiltAmplitude * Math.sin(Math.PI * lambda);
  const angleRate = config.axisTiltAmplitude * Math.PI * Math.cos(Math.PI * lambda) * lambdaRate;
  const rotation = rotationY(angle);
  const rotationRate = rotationYDerivative(angle, angleRate);
  const momentMatrix = diagonal(moments);
  const momentRateMatrix = diagonal(momentsRate);
  const transpose = matTranspose(rotation);
  const rotationRateTranspose = matTranspose(rotationRate);
  const inertia = matMul(matMul(rotation, momentMatrix), transpose);
  const inertiaRate = matAdd(
    matMul(matMul(rotationRate, momentMatrix), transpose),
    matMul(matMul(rotation, momentRateMatrix), transpose),
    matMul(matMul(rotation, momentMatrix), rotationRateTranspose),
  );
  return {
    lambda,
    lambda_rate: lambdaRate,
    principal_moments: moments,
    principal_axis_tilt: angle,
    inertia,
    inertia_rate: inertiaRate,
  };
}

export function integrateJitterbugAnalogue(overrides = {}) {
  const config = { ...DEFAULT_JITTERBUG, ...overrides };
  const derivative = (time, state) => {
    const omega = state.slice(0, 3);
    const inertiaState = jitterbugInertiaState(time, config);
    const angularMomentum = matVec(inertiaState.inertia, omega);
    const rightHandSide = scale3(
      add3(
        matVec(inertiaState.inertia_rate, omega),
        cross3(omega, angularMomentum),
      ),
      -1,
    );
    const omegaDerivative = matVec(inverse3(inertiaState.inertia), rightHandSide);
    return [...omegaDerivative, ...quaternionDerivative(state.slice(3, 7), omega)];
  };

  const diagnostics = (time, omega) => {
    const inertiaState = jitterbugInertiaState(time, config);
    const angularMomentum = matVec(inertiaState.inertia, omega);
    return {
      angular_momentum_norm: norm3(angularMomentum),
      energy: 0.5 * dot3(omega, angularMomentum),
      principal_moments: inertiaState.principal_moments,
      lambda: inertiaState.lambda,
      lambda_rate: inertiaState.lambda_rate,
      principal_axis_tilt: inertiaState.principal_axis_tilt,
    };
  };

  return integrateModel({
    config,
    derivative,
    diagnostics,
    model: "reduced variable-inertia Jitterbug analogue",
    schema: "RSH-EXPLORATORY-JITTERBUG-VARIABLE-INERTIA-V1",
  });
}

function nlerpQuaternion(left, right, amount) {
  let adjusted = right;
  const dot = left.reduce((sum, value, index) => sum + value * right[index], 0);
  if (dot < 0) adjusted = right.map((value) => -value);
  return normalizeQuaternion(left.map((value, index) => (
    value + amount * (adjusted[index] - value)
  )));
}

function interpolateSample(samples, time) {
  if (time < samples[0].time || time > samples.at(-1).time) return null;
  const dt = samples[1].time - samples[0].time;
  const raw = (time - samples[0].time) / dt;
  const lowerIndex = Math.max(0, Math.min(samples.length - 2, Math.floor(raw)));
  const amount = Math.max(0, Math.min(1, raw - lowerIndex));
  const lower = samples[lowerIndex];
  const upper = samples[lowerIndex + 1];
  return {
    time,
    quaternion: nlerpQuaternion(lower.quaternion, upper.quaternion, amount),
  };
}

function correlation(left, right) {
  if (left.length !== right.length || left.length < 2) return 0;
  const leftMean = left.reduce((sum, value) => sum + value, 0) / left.length;
  const rightMean = right.reduce((sum, value) => sum + value, 0) / right.length;
  let covariance = 0;
  let leftVariance = 0;
  let rightVariance = 0;
  for (let index = 0; index < left.length; index += 1) {
    const leftDelta = left[index] - leftMean;
    const rightDelta = right[index] - rightMean;
    covariance += leftDelta * rightDelta;
    leftVariance += leftDelta ** 2;
    rightVariance += rightDelta ** 2;
  }
  const denominator = Math.sqrt(leftVariance * rightVariance);
  return denominator <= EPSILON ? 0 : covariance / denominator;
}

function percentile(values, fraction) {
  const sorted = [...values].sort((left, right) => left - right);
  const index = Math.min(sorted.length - 1, Math.max(0, Math.ceil(fraction * sorted.length) - 1));
  return sorted[index];
}

function alignOne(dzhanibekov, jitterbug, timeScale, timeShift, sampleCount) {
  const dzSamples = dzhanibekov.samples;
  const jbSamples = jitterbug.samples;
  const align = quaternionMultiply(
    jbSamples[0].quaternion,
    quaternionConjugate(dzSamples[0].quaternion),
  );
  const duration = Math.min(
    dzSamples.at(-1).time,
    Math.max(0, (jbSamples.at(-1).time - timeShift) / timeScale),
  );
  const distances = [];
  const dzExcursions = [];
  const jbExcursions = [];
  for (let index = 0; index < sampleCount; index += 1) {
    const dzTime = duration * index / Math.max(1, sampleCount - 1);
    const jbTime = dzTime * timeScale + timeShift;
    const dz = interpolateSample(dzSamples, dzTime);
    const jb = interpolateSample(jbSamples, jbTime);
    if (!dz || !jb) continue;
    const alignedQuaternion = normalizeQuaternion(quaternionMultiply(align, dz.quaternion));
    distances.push(quaternionDistance(alignedQuaternion, jb.quaternion));
    dzExcursions.push(quaternionDistance(dzSamples[0].quaternion, dz.quaternion));
    jbExcursions.push(quaternionDistance(jbSamples[0].quaternion, jb.quaternion));
  }
  if (distances.length < MIN_COMPARISON_SAMPLES) return null;
  const mean = distances.reduce((sum, value) => sum + value, 0) / distances.length;
  const rms = Math.sqrt(distances.reduce((sum, value) => sum + value ** 2, 0) / distances.length);
  const excursionCorrelation = correlation(dzExcursions, jbExcursions);
  const distanceSummary = summarizeSeries(distances);
  const dzExcursionSummary = summarizeSeries(dzExcursions);
  const jbExcursionSummary = summarizeSeries(jbExcursions);
  return {
    time_scale_factor: timeScale,
    time_shift: timeShift,
    overlap_samples: distances.length,
    quaternion_distance: {
      mean_rad: mean,
      rms_rad: rms,
      max_rad: distanceSummary.maximum,
      median_rad: percentile(distances, 0.5),
      mean_deg: mean * 180 / Math.PI,
      rms_deg: rms * 180 / Math.PI,
      max_deg: distanceSummary.maximum * 180 / Math.PI,
      p95_deg: percentile(distances, 0.95) * 180 / Math.PI,
    },
    attitude_excursion_correlation: excursionCorrelation,
    max_attitude_excursion_dz_deg: dzExcursionSummary.maximum * 180 / Math.PI,
    max_attitude_excursion_jb_deg: jbExcursionSummary.maximum * 180 / Math.PI,
    score: rms - 0.15 * excursionCorrelation,
  };
}

export function compareAttitudeTrajectories(
  dzhanibekov,
  jitterbug,
  options = {},
) {
  const timeScales = options.timeScales ?? [0.5, 1, 2, 10];
  const timeShifts = options.timeShifts ?? [-10, -5, 0, 5, 10];
  const sampleCount = integerInRange(
    options.sampleCount ?? 800,
    "sampleCount",
    MIN_COMPARISON_SAMPLES,
    MAX_COMPARISON_SAMPLES,
  );
  if (!Array.isArray(timeScales) || timeScales.length === 0) {
    throw new Error("timeScales must be a non-empty array");
  }
  if (!Array.isArray(timeShifts) || timeShifts.length === 0) {
    throw new Error("timeShifts must be a non-empty array");
  }
  if (timeScales.length * timeShifts.length > MAX_ALIGNMENT_CANDIDATES) {
    throw new Error(`alignment candidate count must not exceed ${MAX_ALIGNMENT_CANDIDATES}`);
  }

  const results = [];
  for (const timeScale of timeScales) {
    positive(timeScale, "time scale");
    for (const timeShift of timeShifts) {
      finiteNumber(timeShift, "time shift");
      const result = alignOne(dzhanibekov, jitterbug, timeScale, timeShift, sampleCount);
      if (result) results.push(result);
    }
  }
  if (results.length === 0) throw new Error("no overlapping trajectory samples");
  results.sort((left, right) => left.score - right.score);
  const best = results[0];
  const bestExcursion = [...results].sort((left, right) => (
    right.attitude_excursion_correlation - left.attitude_excursion_correlation
  ))[0];
  let verdict = "NO MATERIAL RESEMBLANCE";
  if (
    best.quaternion_distance.rms_deg < 30
    && best.attitude_excursion_correlation > 0.7
  ) {
    verdict = "STRONG TRAJECTORY RESEMBLANCE";
  } else if (
    bestExcursion.max_attitude_excursion_dz_deg > 150
    && bestExcursion.max_attitude_excursion_jb_deg > 150
    && bestExcursion.attitude_excursion_correlation > 0.2
  ) {
    verdict = "PARTIAL TRAJECTORY RESEMBLANCE";
  }
  return {
    schema: ATTITUDE_SCHEMA,
    verdict,
    comparison_sample_count: sampleCount,
    best_alignment: best,
    best_excursion_alignment: bestExcursion,
    verdict_alignment: verdict === "PARTIAL TRAJECTORY RESEMBLANCE" ? bestExcursion : best,
    results_by_scale: timeScales.map((scale) => (
      results.filter((result) => result.time_scale_factor === scale)
        .sort((left, right) => left.score - right.score)[0]
    )),
    scale_invariance_analysis: {
      tested_time_rescaling_factors: [...timeScales],
      uniform_geometric_scaling_is_not_automatically_time_rescaling: true,
      universal_scale_invariance_claim: false,
    },
    claims: { ...CLAIM_BOUNDARIES },
  };
}

export function runDefaultAttitudeStudy(overrides = {}) {
  const dzhanibekov = integrateDzhanibekov(overrides.dzhanibekov);
  const jitterbug = integrateJitterbugAnalogue(overrides.jitterbug);
  const comparison = compareAttitudeTrajectories(
    dzhanibekov,
    jitterbug,
    overrides.comparison,
  );
  return { dzhanibekov, jitterbug, comparison };
}

export function compactTrajectory(result, maximumSamples = 1001) {
  integerInRange(maximumSamples, "maximumSamples", 1, MAX_OUTPUT_SAMPLES);
  const stride = Math.max(1, Math.ceil(result.samples.length / maximumSamples));
  return {
    schema: result.schema,
    model: result.model,
    parameters: result.parameters,
    invariants: result.invariants,
    principal_axis_crossings: result.principal_axis_crossings,
    attitude_reversals_approx_180deg: result.attitude_reversals_approx_180deg,
    samples: result.samples.filter((_sample, index) => index % stride === 0 || index === result.samples.length - 1),
    source_sample_count: result.samples.length,
    sample_stride: stride,
    claims: result.claims,
  };
}
