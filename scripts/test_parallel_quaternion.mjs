#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const profilePath = process.argv[2] ?? "conformance/frenet_parallel_v1_1025.json";
const profile = JSON.parse(await readFile(profilePath, "utf8"));
const config = { ...profile.configuration, samples: 4097 };
const gates = profile.webgpu;
const f = Math.fround;
const psi = Math.sqrt(2 + Math.sqrt(5));
const kappaBound = Math.sqrt(2) - 1;

assert.equal(profile.parallel_contract, "RSH-FRENET-PARALLEL-V1");
assert.equal(gates.transform_bytes, 32);
assert.equal(gates.rotation_representation, "normalized-quaternion-xyzw-f32-v1");

function cross(left, right) {
  return [
    left[1] * right[2] - left[2] * right[1],
    left[2] * right[0] - left[0] * right[2],
    left[0] * right[1] - left[1] * right[0],
  ];
}

function dot(left, right) {
  return left.reduce((sum, value, index) => sum + value * right[index], 0);
}

function add(left, right) {
  return left.map((value, index) => value + right[index]);
}

function scale(vector, scalar) {
  return vector.map((value) => value * scalar);
}

function norm(vector) {
  return Math.hypot(...vector);
}

function schedule64(s) {
  return {
    kappa: config.kappa_fraction * kappaBound
      * (0.92 + 0.08 * Math.cos(0.35 * s * psi)),
    tau: config.tau_floor
      + config.tau_amplitude * (1 + Math.sin(0.25 * s * psi)),
  };
}

function schedule32(s) {
  const sample = f(s);
  const base = f(f(config.kappa_fraction) * f(kappaBound));
  const kappaAngle = f(f(f(0.35) * sample) * f(psi));
  const tauAngle = f(f(f(0.25) * sample) * f(psi));
  return {
    kappa: f(base * f(f(0.92) + f(f(0.08) * f(Math.cos(kappaAngle))))),
    tau: f(
      f(config.tau_floor)
        + f(f(config.tau_amplitude) * f(f(1) + f(Math.sin(tauAngle)))),
    ),
  };
}

function rotation64(omega, step) {
  const magnitude = norm(omega);
  if (magnitude <= 1e-12) return [[1, 0, 0], [0, 1, 0], [0, 0, 1]];
  const axis = scale(omega, 1 / magnitude);
  const angle = magnitude * step;
  const cosine = Math.cos(angle);
  const sine = Math.sin(angle);
  return [[1, 0, 0], [0, 1, 0], [0, 0, 1]].map((basis) => add(
    add(scale(basis, cosine), scale(cross(axis, basis), sine)),
    scale(axis, dot(axis, basis) * (1 - cosine)),
  ));
}

function applyMatrix(rotation, vector) {
  return add(
    add(scale(rotation[0], vector[0]), scale(rotation[1], vector[1])),
    scale(rotation[2], vector[2]),
  );
}

function compose64(left, right) {
  return {
    rotation: right.rotation.map((column) => applyMatrix(left.rotation, column)),
    translation: add(left.translation, applyMatrix(left.rotation, right.translation)),
  };
}

function normalizeQuaternion32(value) {
  const magnitudeSquared = f(value.reduce((sum, component) => f(sum + f(component * component)), f(0)));
  if (magnitudeSquared <= f(1e-12)) return [f(0), f(0), f(0), f(1)];
  const inverse = f(1 / Math.sqrt(magnitudeSquared));
  return value.map((component) => f(component * inverse));
}

function quaternionMultiply32(left, right) {
  const [lx, ly, lz, lw] = left;
  const [rx, ry, rz, rw] = right;
  return [
    f(f(f(f(lw * rx) + f(lx * rw)) + f(ly * rz)) - f(lz * ry)),
    f(f(f(f(lw * ry) - f(lx * rz)) + f(ly * rw)) + f(lz * rx)),
    f(f(f(f(lw * rz) + f(lx * ry)) - f(ly * rx)) + f(lz * rw)),
    f(f(f(f(lw * rw) - f(lx * rx)) - f(ly * ry)) - f(lz * rz)),
  ];
}

function cross32(left, right) {
  return [
    f(f(left[1] * right[2]) - f(left[2] * right[1])),
    f(f(left[2] * right[0]) - f(left[0] * right[2])),
    f(f(left[0] * right[1]) - f(left[1] * right[0])),
  ];
}

function rotateQuaternion32(rotation, vector) {
  const unit = normalizeQuaternion32(rotation);
  const doubled = cross32(unit.slice(0, 3), vector).map((value) => f(f(2) * value));
  const second = cross32(unit.slice(0, 3), doubled);
  return vector.map((value, index) => f(f(value + f(unit[3] * doubled[index])) + second[index]));
}

function quaternionFromOmega32(omega, step) {
  const magnitude = f(Math.hypot(...omega));
  if (magnitude <= f(1e-8)) return [f(0), f(0), f(0), f(1)];
  const halfAngle = f(f(f(0.5) * magnitude) * f(step));
  const sine = f(Math.sin(halfAngle));
  const inverseMagnitude = f(1 / magnitude);
  return normalizeQuaternion32([
    f(f(omega[0] * inverseMagnitude) * sine),
    f(f(omega[1] * inverseMagnitude) * sine),
    f(f(omega[2] * inverseMagnitude) * sine),
    f(Math.cos(halfAngle)),
  ]);
}

function compose32(left, right) {
  const leftRotation = normalizeQuaternion32(left.rotation);
  const rightRotation = normalizeQuaternion32(right.rotation);
  const rotatedTranslation = rotateQuaternion32(leftRotation, right.translation);
  return {
    rotation: normalizeQuaternion32(quaternionMultiply32(leftRotation, rightRotation)),
    translation: left.translation.map((value, index) => f(value + rotatedTranslation[index])),
  };
}

function inclusiveScan(values, compose) {
  let current = values;
  for (let offset = 1; offset < values.length; offset *= 2) {
    current = current.map((value, index) => (
      index < offset ? value : compose(current[index - offset], value)
    ));
  }
  return current;
}

function build64() {
  const ds = (config.s1 - config.s0) / (config.samples - 1);
  return Array.from({ length: config.samples }, (_, index) => {
    if (index === 0) {
      return { rotation: [[1, 0, 0], [0, 1, 0], [0, 0, 1]], translation: [0, 0, 0] };
    }
    const midpoint = config.s0 + (index - 0.5) * ds;
    const { kappa, tau } = schedule64(midpoint);
    const omega = [tau, 0, kappa];
    return {
      rotation: rotation64(omega, ds),
      translation: scale(rotation64(omega, 0.5 * ds)[0], ds),
    };
  });
}

function build32() {
  const ds = f(f(config.s1 - config.s0) / f(config.samples - 1));
  return Array.from({ length: config.samples }, (_, index) => {
    if (index === 0) {
      return { rotation: [f(0), f(0), f(0), f(1)], translation: [f(0), f(0), f(0)] };
    }
    const midpoint = f(f(config.s0) + f(f(f(index - 1) + f(0.5)) * ds));
    const { kappa, tau } = schedule32(midpoint);
    const omega = [tau, f(0), kappa];
    const halfRotation = quaternionFromOmega32(omega, f(f(0.5) * ds));
    return {
      rotation: quaternionFromOmega32(omega, ds),
      translation: rotateQuaternion32(halfRotation, [f(1), f(0), f(0)])
        .map((value) => f(value * ds)),
    };
  });
}

const reference = inclusiveScan(build64(), compose64);
const candidate = inclusiveScan(build32(), compose32);
const centreIndex = Math.floor(config.samples / 2);
const centre64 = reference[centreIndex].translation;
const centre32 = candidate[centreIndex].translation;
let maxPosition = 0;
let maxFrame = 0;
let maxSchedule = 0;
let maxFrameNorm = 0;
let maxFrameOrthogonality = 0;

for (let index = 0; index < config.samples; index += 1) {
  const expectedPosition = reference[index].translation.map((value, axis) => value - centre64[axis]);
  const actualPosition = candidate[index].translation.map((value, axis) => f(value - centre32[axis]));
  maxPosition = Math.max(
    maxPosition,
    ...actualPosition.map((value, axis) => Math.abs(value - expectedPosition[axis])),
  );

  const actualFrame = [
    rotateQuaternion32(candidate[index].rotation, [f(1), f(0), f(0)]),
    rotateQuaternion32(candidate[index].rotation, [f(0), f(1), f(0)]),
    rotateQuaternion32(candidate[index].rotation, [f(0), f(0), f(1)]),
  ];
  const expectedFrame = reference[index].rotation;
  maxFrame = Math.max(
    maxFrame,
    ...actualFrame.flatMap((vector, column) => (
      vector.map((value, axis) => Math.abs(value - expectedFrame[column][axis]))
    )),
  );
  maxFrameNorm = Math.max(
    maxFrameNorm,
    ...actualFrame.map((vector) => Math.abs(norm(vector) - 1)),
  );
  maxFrameOrthogonality = Math.max(
    maxFrameOrthogonality,
    Math.abs(dot(actualFrame[0], actualFrame[1])),
    Math.abs(dot(actualFrame[0], actualFrame[2])),
    Math.abs(dot(actualFrame[1], actualFrame[2])),
  );

  const p64 = index / (config.samples - 1);
  const s64 = config.s0 + p64 * (config.s1 - config.s0);
  const p32 = f(f(index) / f(config.samples - 1));
  const s32 = f(f(config.s0) + f(p32 * f(config.s1 - config.s0)));
  const expectedSchedule = schedule64(s64);
  const actualSchedule = schedule32(s32);
  maxSchedule = Math.max(
    maxSchedule,
    Math.abs(actualSchedule.kappa - expectedSchedule.kappa),
    Math.abs(actualSchedule.tau - expectedSchedule.tau),
  );
}

assert.ok(maxPosition <= gates.position_component_gate, `position residual ${maxPosition}`);
assert.ok(maxFrame <= gates.frame_component_gate, `frame residual ${maxFrame}`);
assert.ok(maxSchedule <= gates.schedule_component_gate, `schedule residual ${maxSchedule}`);
assert.ok(maxFrameNorm <= gates.frame_norm_gate, `frame norm residual ${maxFrameNorm}`);
assert.ok(
  maxFrameOrthogonality <= gates.frame_orthogonality_gate,
  `frame orthogonality residual ${maxFrameOrthogonality}`,
);

console.log(JSON.stringify({
  schema: "RSH-FRENET-PARALLEL-QUATERNION-F32-REGRESSION-V1",
  status: "PASS",
  samples: config.samples,
  scan_passes: Math.ceil(Math.log2(config.samples)),
  rotation_representation: gates.rotation_representation,
  transform_bytes: gates.transform_bytes,
  residuals: {
    max_position_component_vs_f64: maxPosition,
    max_frame_component_vs_f64: maxFrame,
    max_schedule_component_vs_f64: maxSchedule,
    max_frame_norm_error: maxFrameNorm,
    max_frame_orthogonality_error: maxFrameOrthogonality,
  },
  actual_gpu_execution: false,
  speedup_claim: false,
  geometry_receipt_authority: false,
}, null, 2));
