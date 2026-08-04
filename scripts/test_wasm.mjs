#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const wasmPath = process.argv[2] ?? "target/wasm32-unknown-unknown/release/rsh_wasm.wasm";
const profilePath = process.argv[3] ?? "conformance/wasm_v2_129.json";
const nativeReportPath = process.argv[4] ?? null;

const [wasmBytes, profileText] = await Promise.all([
  readFile(wasmPath),
  readFile(profilePath, "utf8"),
]);
const profile = JSON.parse(profileText);

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
  "rsh_output_ptr",
  "rsh_output_len",
]) {
  assert.ok(name in exports, `missing WebAssembly export: ${name}`);
}

assert.equal(Number(exports.rsh_abi_version()), profile.abi_version);

const config = profile.configuration;
const status = Number(exports.rsh_run(
  config.samples,
  config.s0,
  config.s1,
  config.kappa_fraction,
  config.tau_floor,
  config.tau_amplitude,
));

const pointer = Number(exports.rsh_output_ptr());
const length = Number(exports.rsh_output_len());
assert.ok(Number.isInteger(pointer) && pointer >= 0, "invalid output pointer");
assert.ok(Number.isInteger(length) && length > 0, "invalid output length");

const bytes = new Uint8Array(exports.memory.buffer, pointer, length);
const payload = JSON.parse(new TextDecoder("utf-8").decode(bytes));

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

console.log(JSON.stringify({
  schema: "RSH-WASM-CONFORMANCE-RESULT-V1",
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
}, null, 2));
