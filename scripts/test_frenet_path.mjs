#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const wasmPath = process.argv[2]
  ?? "target/wasm32-unknown-unknown/release/rsh_numerics_wasm.wasm";
const profilePath = process.argv[3] ?? "conformance/frenet_path_v1_1025.json";

const profile = JSON.parse(await readFile(profilePath, "utf8"));
const shaderSource = await readFile(profile.shader, "utf8");
const wasmBytes = await readFile(wasmPath);

assert.equal(
  Buffer.from(wasmBytes.subarray(0, 4)).toString("hex"),
  "0061736d",
  "invalid WebAssembly magic header",
);
assert.match(shaderSource, /@compute\s+@workgroup_size\(1\)/u);
assert.match(shaderSource, /fn\s+rotate_body/u);
assert.match(shaderSource, /fn\s+orthonormalize/u);
assert.match(shaderSource, /output_path\[index\]/u);

const { instance } = await WebAssembly.instantiate(wasmBytes, {});
const exports = instance.exports;
for (const name of [
  "memory",
  "rsh_frenet_abi_version",
  "rsh_frenet_run",
  "rsh_frenet_output_ptr",
  "rsh_frenet_output_len",
]) {
  assert.ok(name in exports, `missing numerical WASM export: ${name}`);
}
assert.equal(Number(exports.rsh_frenet_abi_version()), 1);

function readPayload() {
  const pointer = Number(exports.rsh_frenet_output_ptr());
  const length = Number(exports.rsh_frenet_output_len());
  assert.ok(Number.isSafeInteger(pointer) && pointer >= 0, "invalid output pointer");
  assert.ok(Number.isSafeInteger(length) && length > 0, "invalid output length");
  const memory = exports.memory.buffer;
  assert.ok(pointer <= memory.byteLength, "output pointer exceeds WASM memory");
  assert.ok(length <= memory.byteLength - pointer, "output range exceeds WASM memory");
  const bytes = new Uint8Array(memory, pointer, length);
  return JSON.parse(new TextDecoder("utf-8").decode(bytes));
}

const config = profile.configuration;
const status = Number(exports.rsh_frenet_run(
  config.samples,
  config.s0,
  config.s1,
  config.kappa_fraction,
  config.tau_floor,
  config.tau_amplitude,
));
const payload = readPayload();

assert.equal(status, 0, payload.message ?? "numerical WASM path failed");
assert.equal(payload.schema, profile.wasm_schema);
assert.equal(payload.numerical_contract, profile.numerical_contract);
assert.equal(payload.integrator, profile.integrator);
assert.equal(payload.model, profile.model);
assert.equal(payload.model_version, profile.model_version);
assert.equal(payload.points.length, config.samples);
assert.equal(payload.report.pass_all, true);
assert.equal(payload.geometry_receipt_authority, false);
assert.equal(payload.speedup_claim, false);

function vector(point, prefix) {
  return [point[`${prefix}x`], point[`${prefix}y`], point[`${prefix}z`]];
}

function position(point) {
  return [point.x, point.y, point.z];
}

function maxAbs(actual, expected) {
  assert.equal(actual.length, expected.length);
  return Math.max(
    ...actual.map((value, index) => Math.abs(Number(value) - Number(expected[index]))),
  );
}

const midpointIndex = Math.floor(payload.points.length / 2);
const midpoint = payload.points[midpointIndex];
const reference = profile.f64_reference;
const f64Errors = {
  entry: maxAbs(position(payload.points[0]), reference.entry),
  centre: maxAbs(position(midpoint), reference.centre),
  exit: maxAbs(position(payload.points.at(-1)), reference.exit),
  centre_tangent: maxAbs(vector(midpoint, "t"), reference.centre_tangent),
  centre_normal: maxAbs(vector(midpoint, "n"), reference.centre_normal),
  centre_binormal: maxAbs(vector(midpoint, "b"), reference.centre_binormal),
};
assert.ok(f64Errors.entry <= reference.coordinate_absolute_tolerance);
assert.ok(f64Errors.centre <= reference.centre_absolute_tolerance);
assert.ok(f64Errors.exit <= reference.coordinate_absolute_tolerance);
assert.ok(f64Errors.centre_tangent <= reference.frame_absolute_tolerance);
assert.ok(f64Errors.centre_normal <= reference.frame_absolute_tolerance);
assert.ok(f64Errors.centre_binormal <= reference.frame_absolute_tolerance);

const f = Math.fround;
const add = (left, right) => f(f(left) + f(right));
const subtract = (left, right) => f(f(left) - f(right));
const multiply = (left, right) => f(f(left) * f(right));
const divide = (left, right) => f(f(left) / f(right));
const v = (x, y, z) => [f(x), f(y), f(z)];
const vAdd = (left, right) => v(
  add(left[0], right[0]),
  add(left[1], right[1]),
  add(left[2], right[2]),
);
const vSubtract = (left, right) => v(
  subtract(left[0], right[0]),
  subtract(left[1], right[1]),
  subtract(left[2], right[2]),
);
const vScale = (vectorValue, amount) => v(
  multiply(vectorValue[0], amount),
  multiply(vectorValue[1], amount),
  multiply(vectorValue[2], amount),
);
const dot = (left, right) => add(
  add(multiply(left[0], right[0]), multiply(left[1], right[1])),
  multiply(left[2], right[2]),
);
const cross = (left, right) => v(
  subtract(multiply(left[1], right[2]), multiply(left[2], right[1])),
  subtract(multiply(left[2], right[0]), multiply(left[0], right[2])),
  subtract(multiply(left[0], right[1]), multiply(left[1], right[0])),
);
const magnitude = (vectorValue) => f(Math.sqrt(Math.max(0, dot(vectorValue, vectorValue))));
const normalize = (vectorValue) => {
  const norm = magnitude(vectorValue);
  return vScale(vectorValue, divide(1, Math.max(norm, 1e-10)));
};

function schedule(s) {
  const kappaBase = multiply(config.kappa_fraction, Math.sqrt(2) - 1);
  const kappaAngle = multiply(multiply(0.35, s), Math.sqrt(2 + Math.sqrt(5)));
  const kappaWave = add(0.92, multiply(0.08, f(Math.cos(kappaAngle))));
  const kappa = multiply(kappaBase, kappaWave);
  const tauAngle = multiply(multiply(0.25, s), Math.sqrt(2 + Math.sqrt(5)));
  const tauWave = add(1, f(Math.sin(tauAngle)));
  const tau = add(config.tau_floor, multiply(config.tau_amplitude, tauWave));
  return { kappa, tau };
}

function rotateBody(vectorValue, omega, step) {
  const omegaMagnitude = magnitude(omega);
  if (omegaMagnitude <= 1e-8) return vectorValue;
  const axis = vScale(omega, divide(1, omegaMagnitude));
  const angle = multiply(omegaMagnitude, step);
  const cosine = f(Math.cos(angle));
  const sine = f(Math.sin(angle));
  return vAdd(
    vAdd(vScale(vectorValue, cosine), vScale(cross(axis, vectorValue), sine)),
    vScale(axis, multiply(dot(axis, vectorValue), subtract(1, cosine))),
  );
}

function worldFromBody(frame, body) {
  return vAdd(
    vAdd(vScale(frame.tangent, body[0]), vScale(frame.normal, body[1])),
    vScale(frame.binormal, body[2]),
  );
}

function orthonormalize(tangent, normal) {
  const projectedTangent = normalize(tangent);
  const projectedNormal = normalize(
    vSubtract(normal, vScale(projectedTangent, dot(normal, projectedTangent))),
  );
  return {
    tangent: projectedTangent,
    normal: projectedNormal,
    binormal: normalize(cross(projectedTangent, projectedNormal)),
  };
}

function emulatePath() {
  const bodyTangent = v(1, 0, 0);
  const bodyNormal = v(0, 1, 0);
  const bodyBinormal = v(0, 0, 1);
  let frame = {
    tangent: bodyTangent,
    normal: bodyNormal,
    binormal: bodyBinormal,
  };
  let currentPosition = v(0, 0, 0);
  const points = [];
  const denominator = config.samples - 1;
  const ds = divide(subtract(config.s1, config.s0), denominator);

  for (let index = 0; index < config.samples; index += 1) {
    const p = divide(index, denominator);
    const s = add(config.s0, multiply(index, ds));
    const values = schedule(s);
    points.push({
      position: currentPosition,
      tangent: frame.tangent,
      normal: frame.normal,
      binormal: frame.binormal,
      kappa: values.kappa,
      tau: values.tau,
    });
    if (index + 1 >= config.samples) break;

    const midpoint = add(s, multiply(0.5, ds));
    const midpointValues = schedule(midpoint);
    const bodyOmega = v(midpointValues.tau, 0, midpointValues.kappa);
    const midpointBodyTangent = rotateBody(bodyTangent, bodyOmega, multiply(0.5, ds));
    currentPosition = vAdd(
      currentPosition,
      vScale(worldFromBody(frame, midpointBodyTangent), ds),
    );
    frame = orthonormalize(
      worldFromBody(frame, rotateBody(bodyTangent, bodyOmega, ds)),
      worldFromBody(frame, rotateBody(bodyNormal, bodyOmega, ds)),
    );
  }

  const centre = points[midpointIndex].position;
  for (const point of points) {
    point.position = vSubtract(point.position, centre);
  }
  return points;
}

const approximate = emulatePath();
let maxPosition = 0;
let maxFrame = 0;
let maxSchedule = 0;
let maxNorm = 0;
let maxOrthogonality = 0;

for (let index = 0; index < payload.points.length; index += 1) {
  const expected = payload.points[index];
  const actual = approximate[index];
  maxPosition = Math.max(maxPosition, maxAbs(actual.position, position(expected)));
  maxFrame = Math.max(
    maxFrame,
    maxAbs(actual.tangent, vector(expected, "t")),
    maxAbs(actual.normal, vector(expected, "n")),
    maxAbs(actual.binormal, vector(expected, "b")),
  );
  maxSchedule = Math.max(
    maxSchedule,
    Math.abs(actual.kappa - Number(expected.kappa)),
    Math.abs(actual.tau - Number(expected.tau)),
  );
  for (const frameVector of [actual.tangent, actual.normal, actual.binormal]) {
    maxNorm = Math.max(maxNorm, Math.abs(magnitude(frameVector) - 1));
  }
  maxOrthogonality = Math.max(
    maxOrthogonality,
    Math.abs(dot(actual.tangent, actual.normal)),
    Math.abs(dot(actual.tangent, actual.binormal)),
    Math.abs(dot(actual.normal, actual.binormal)),
  );
}

const gates = profile.f32_accelerator_gates;
assert.ok(maxPosition <= gates.max_position_component_vs_wasm_f64);
assert.ok(maxFrame <= gates.max_frame_component_vs_wasm_f64);
assert.ok(maxSchedule <= gates.max_schedule_component_vs_wasm_f64);
assert.ok(maxNorm <= gates.max_frame_norm_error);
assert.ok(maxOrthogonality <= gates.max_frame_orthogonality_error);

console.log(JSON.stringify({
  schema: "RSH-FRENET-PATH-CONFORMANCE-RESULT-V1",
  status: "PASS",
  wasm_path: wasmPath,
  numerical_contract: payload.numerical_contract,
  integrator: payload.integrator,
  samples: payload.points.length,
  f64_reference_errors: f64Errors,
  f32_reference_residuals: {
    max_position_component_vs_wasm_f64: maxPosition,
    max_frame_component_vs_wasm_f64: maxFrame,
    max_schedule_component_vs_wasm_f64: maxSchedule,
    max_frame_norm_error: maxNorm,
    max_frame_orthogonality_error: maxOrthogonality,
  },
  gates,
  actual_gpu_execution: false,
  full_path_arithmetic_reference: true,
  geometry_receipt_authority: false,
  speedup_claim: false,
}, null, 2));
