#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const wasmPath = process.argv[2] ?? "target/wasm32-unknown-unknown/release/rsh_wasm.wasm";
const profilePath = process.argv[3] ?? "conformance/wasm_v2_129.json";
const nativeReportPath = process.argv[4] || null;
const wgslProfilePath = process.argv[5] ?? "conformance/wgsl_v1_4096.json";

const [wasmBytes, profileText, wgslProfileText] = await Promise.all([
  readFile(wasmPath),
  readFile(profilePath, "utf8"),
  readFile(wgslProfilePath, "utf8"),
]);
const profile = JSON.parse(profileText);
const wgslProfile = JSON.parse(wgslProfileText);
const shaderSource = await readFile(wgslProfile.shader, "utf8");

assert.equal(
  Buffer.from(wasmBytes.subarray(0, 4)).toString("hex"),
  "0061736d",
  "invalid WebAssembly magic header",
);

const { instance } = await WebAssembly.instantiate(wasmBytes, {});
const exports = instance.exports;
for (const name of [
  "memory",
  "rsh_abi_version",
  "rsh_run",
  "rsh_schedule",
  "rsh_output_ptr",
  "rsh_output_len",
]) {
  assert.ok(name in exports, `missing WebAssembly export: ${name}`);
}

assert.equal(Number(exports.rsh_abi_version()), profile.abi_version);
assert.match(shaderSource, /@compute\s+@workgroup_size\(64\)/u);
assert.match(shaderSource, /fn\s+kappa_schedule/u);
assert.match(shaderSource, /fn\s+tau_schedule/u);
assert.match(shaderSource, /output_field\[index\]/u);

function readPayload() {
  const pointer = Number(exports.rsh_output_ptr());
  const length = Number(exports.rsh_output_len());
  assert.ok(Number.isInteger(pointer) && pointer >= 0, "invalid output pointer");
  assert.ok(Number.isInteger(length) && length > 0, "invalid output length");
  const bytes = new Uint8Array(exports.memory.buffer, pointer, length);
  return JSON.parse(new TextDecoder("utf-8").decode(bytes));
}

const config = profile.configuration;
const status = Number(exports.rsh_run(
  config.samples,
  config.s0,
  config.s1,
  config.kappa_fraction,
  config.tau_floor,
  config.tau_amplitude,
));
const payload = readPayload();

assert.equal(status, 0, payload.message ?? "WebAssembly verification failed");
assert.equal(payload.schema, "RSH-BROWSER-RUN-V1");
assert.equal(payload.abi_version, profile.abi_version);
assert.equal(payload.model, profile.model);
assert.equal(payload.model_version, profile.model_version);
assert.equal(payload.report.pass_all, profile.required.pass_all);
assert.equal(payload.points.length, profile.required.point_count);
assert.equal(payload.report.samples, profile.required.point_count);

function maxAbsError(actual, expected) {
  assert.equal(actual.length, expected.length);
  return Math.max(...actual.map((value, index) => Math.abs(Number(value) - Number(expected[index]))));
}

function coordinates(point) {
  return [point.x, point.y, point.z];
}

const entryError = maxAbsError(coordinates(payload.points[0]), profile.entry);
const exitError = maxAbsError(coordinates(payload.points.at(-1)), profile.exit);
const midpoint = payload.points[Math.floor(payload.points.length / 2)];
const centreError = Math.hypot(midpoint.x, midpoint.y, midpoint.z);

assert.ok(
  entryError <= profile.coordinate_tolerance,
  `entry coordinate residual ${entryError} exceeds ${profile.coordinate_tolerance}`,
);
assert.ok(
  exitError <= profile.coordinate_tolerance,
  `exit coordinate residual ${exitError} exceeds ${profile.coordinate_tolerance}`,
);
assert.ok(
  centreError <= profile.centre_tolerance,
  `centre residual ${centreError} exceeds ${profile.centre_tolerance}`,
);
assert.match(payload.report.receipt, /^[0-9a-f]{64}$/u);
assert.equal(
  payload.report.receipt,
  profile.canonical_receipt,
  "WebAssembly receipt differs from the sealed Phase 3 profile",
);

for (const point of payload.points) {
  for (const field of ["p", "x", "y", "z", "kappa", "tau"]) {
    assert.ok(Number.isFinite(Number(point[field])), `non-finite point field: ${field}`);
  }
}

let nativeReceipt = null;
let receiptIdenticalToNative = null;
if (nativeReportPath) {
  const nativeReport = JSON.parse(await readFile(nativeReportPath, "utf8"));
  nativeReceipt = nativeReport.receipt;
  receiptIdenticalToNative = nativeReceipt === payload.report.receipt;
  if (profile.receipt_policy.native_identity_required) {
    assert.equal(
      payload.report.receipt,
      nativeReceipt,
      "WebAssembly receipt differs from the native Rust receipt",
    );
  }
}

const gpuConfig = wgslProfile.configuration;
const scheduleStatus = Number(exports.rsh_schedule(
  gpuConfig.samples,
  gpuConfig.s0,
  gpuConfig.s1,
  gpuConfig.kappa_fraction,
  gpuConfig.tau_floor,
  gpuConfig.tau_amplitude,
));
const schedule = readPayload();
assert.equal(scheduleStatus, 0, schedule.message ?? "WASM schedule oracle failed");
assert.equal(schedule.schema, wgslProfile.wasm_schedule_schema);
assert.equal(schedule.model, wgslProfile.model);
assert.equal(schedule.model_version, wgslProfile.model_version);
assert.equal(schedule.samples, gpuConfig.samples);
assert.equal(schedule.points.length, gpuConfig.samples);

const f = Math.fround;
const add = (left, right) => f(f(left) + f(right));
const subtract = (left, right) => f(f(left) - f(right));
const multiply = (left, right) => f(f(left) * f(right));
const divide = (left, right) => f(f(left) / f(right));

function emulateWgslPoint(index) {
  const p = divide(index, gpuConfig.samples - 1);
  const s = add(gpuConfig.s0, multiply(p, subtract(gpuConfig.s1, gpuConfig.s0)));
  const kappaBase = multiply(gpuConfig.kappa_fraction, schedule.kappa_bound);
  const kappaAngle = multiply(multiply(0.35, s), schedule.psi);
  const kappaWave = add(0.92, multiply(0.08, f(Math.cos(kappaAngle))));
  const kappa = multiply(kappaBase, kappaWave);
  const tauAngle = multiply(multiply(0.25, s), schedule.psi);
  const tauWave = add(1.0, f(Math.sin(tauAngle)));
  const tau = add(gpuConfig.tau_floor, multiply(gpuConfig.tau_amplitude, tauWave));
  return { kappa, tau };
}

let maxKappaF32Residual = 0;
let maxTauF32Residual = 0;
for (let index = 0; index < schedule.points.length; index += 1) {
  const reference = schedule.points[index];
  const approximate = emulateWgslPoint(index);
  maxKappaF32Residual = Math.max(
    maxKappaF32Residual,
    Math.abs(approximate.kappa - Number(reference.kappa)),
  );
  maxTauF32Residual = Math.max(
    maxTauF32Residual,
    Math.abs(approximate.tau - Number(reference.tau)),
  );
}
const maxF32ReferenceResidual = Math.max(maxKappaF32Residual, maxTauF32Residual);
assert.ok(
  maxF32ReferenceResidual <= wgslProfile.residual_threshold,
  `f32 schedule reference residual ${maxF32ReferenceResidual} exceeds ${wgslProfile.residual_threshold}`,
);

console.log(JSON.stringify({
  schema: "RSH-WASM-WGSL-CONFORMANCE-RESULT-V1",
  status: "PASS",
  wasm_path: wasmPath,
  samples: payload.points.length,
  entry_max_abs_error: entryError,
  exit_max_abs_error: exitError,
  centre_error: centreError,
  coordinate_tolerance: profile.coordinate_tolerance,
  centre_tolerance: profile.centre_tolerance,
  wasm_receipt: payload.report.receipt,
  native_receipt: nativeReceipt,
  receipt_identical_to_native: receiptIdenticalToNative,
  wgsl_grid_samples: schedule.points.length,
  wgsl_workgroup_size: wgslProfile.workgroup_size,
  f32_reference_max_abs_kappa: maxKappaF32Residual,
  f32_reference_max_abs_tau: maxTauF32Residual,
  f32_reference_max_abs_error: maxF32ReferenceResidual,
  wgsl_residual_threshold: wgslProfile.residual_threshold,
  actual_gpu_execution: "browser runtime; adapter-specific sidecar",
}, null, 2));
