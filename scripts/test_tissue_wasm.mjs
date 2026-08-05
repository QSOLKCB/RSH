#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const wasmPath = process.argv[2]
  ?? "target/wasm32-unknown-unknown/release/rsh_tissue_wasm.wasm";
const profilePath = process.argv[3] ?? "conformance/tissue_v1_8x20.json";
const pythonPath = process.argv[4] ?? join(tmpdir(), "rsh_tissue_python.json");
const rustPath = process.argv[5] ?? join(tmpdir(), "rsh_tissue_rust.json");

const [wasmBytes, profile, pythonReport, rustReport] = await Promise.all([
  readFile(wasmPath),
  readFile(profilePath, "utf8").then(JSON.parse),
  readFile(pythonPath, "utf8").then(JSON.parse),
  readFile(rustPath, "utf8").then(JSON.parse),
]);
assert.equal(
  Buffer.from(wasmBytes.subarray(0, 4)).toString("hex"),
  "0061736d",
  "invalid tissue WebAssembly magic header",
);

const { instance } = await WebAssembly.instantiate(wasmBytes, {});
const api = instance.exports;
for (const name of [
  "memory",
  "rsh_tissue_abi_version",
  "rsh_tissue_run",
  "rsh_tissue_output_ptr",
  "rsh_tissue_output_len",
]) {
  assert.ok(name in api, `missing tissue WASM export: ${name}`);
}
assert.equal(Number(api.rsh_tissue_abi_version()), profile.rust_wasm.abi_version);

const backendCode = {
  none: 0,
  webgpu: 1,
  cuda: 2,
  npu: 3,
}[profile.configuration.sidecar_backend];
assert.ok(Number.isInteger(backendCode), "unknown tissue sidecar backend");
const c = profile.configuration;
const status = Number(api.rsh_tissue_run(
  c.cells,
  c.ticks,
  c.geometry_samples,
  c.ds,
  c.phase_coupling,
  c.binding_diffusion,
  backendCode,
  c.sidecar_residual,
  c.residual_gate,
  c.qf_floor,
));

const pointer = Number(api.rsh_tissue_output_ptr());
const length = Number(api.rsh_tissue_output_len());
assert.ok(Number.isSafeInteger(pointer) && pointer >= 0, "invalid tissue output pointer");
assert.ok(Number.isSafeInteger(length) && length > 0, "invalid tissue output length");
assert.ok(
  pointer <= api.memory.buffer.byteLength
    && length <= api.memory.buffer.byteLength - pointer,
  "tissue output span exceeds WASM memory",
);
const payload = JSON.parse(
  new TextDecoder().decode(new Uint8Array(api.memory.buffer, pointer, length)),
);
assert.equal(status, 0, payload.message ?? "tissue WASM failed");
assert.equal(payload.schema, profile.rust_wasm.payload_schema);
assert.equal(payload.abi_version, profile.rust_wasm.abi_version);
assert.equal(payload.implementation, profile.rust_wasm.wasm_implementation);
assert.equal(payload.geometry_receipt_authority, false);
assert.equal(payload.subjective_awareness_claim, false);
assert.equal(payload.autonomous_source_modification, false);

const wasmReport = payload.report;
assert.equal(wasmReport.schema, profile.rust_wasm.report_schema);
for (const key of [
  "pass_all",
  "pass_constitution",
  "pass_bounds",
  "pass_centre",
  "pass_qf_floor",
  "audit_chain_valid",
]) {
  assert.equal(wasmReport[key], true, `${key} must pass`);
}
assert.equal(wasmReport.sidecar_accepted, false);
assert.equal(wasmReport.fallback_used, false);
assert.equal(wasmReport.ticks.length, c.ticks);
assert.equal(wasmReport.final_cells.length, c.cells);

const tolerance = profile.expected.observable_absolute_tolerance;
let maxResidual = 0;
let numberCount = 0;
function comparePortable(actual, expected, path = "report") {
  if (path.toLowerCase().includes("receipt")) return;
  if (typeof expected === "number") {
    assert.equal(typeof actual, "number", `${path} must be numeric`);
    assert.ok(Number.isFinite(actual) && Number.isFinite(expected), `${path} must be finite`);
    const residual = Math.abs(actual - expected);
    maxResidual = Math.max(maxResidual, residual);
    numberCount += 1;
    assert.ok(residual <= tolerance, `${path} residual ${residual} exceeds ${tolerance}`);
    return;
  }
  if (Array.isArray(expected)) {
    assert.ok(Array.isArray(actual), `${path} must be an array`);
    assert.equal(actual.length, expected.length, `${path} length mismatch`);
    expected.forEach((value, index) => {
      comparePortable(actual[index], value, `${path}[${index}]`);
    });
    return;
  }
  if (expected && typeof expected === "object") {
    assert.ok(actual && typeof actual === "object", `${path} must be an object`);
    for (const [key, value] of Object.entries(expected)) {
      comparePortable(actual[key], value, `${path}.${key}`);
    }
    return;
  }
  assert.equal(actual, expected, `${path} mismatch`);
}

comparePortable(wasmReport, rustReport, "wasm_vs_native");
comparePortable(rustReport, pythonReport, "native_vs_python");
comparePortable(wasmReport, pythonReport, "wasm_vs_python");

assert.equal(pythonReport.receipt, profile.expected.reference_report_receipt);
assert.equal(
  pythonReport.seed_geometry_receipt,
  profile.expected.seed_geometry_receipt,
);
assert.equal(
  pythonReport.ticks[0].receipt,
  profile.expected.reference_first_tick_receipt,
);
assert.equal(
  pythonReport.ticks.at(-1).receipt,
  profile.expected.reference_last_tick_receipt,
);
for (const [actual, expected] of [
  [pythonReport.ticks[0].metrics.q_f, profile.expected.first_q_f],
  [pythonReport.final_q_f, profile.expected.final_q_f],
  [pythonReport.min_q_f, profile.expected.minimum_q_f],
  [pythonReport.max_q_f, profile.expected.maximum_q_f],
  [pythonReport.ticks.at(-1).metrics.dissociation, profile.expected.final_dissociation],
]) {
  assert.ok(Math.abs(actual - expected) <= tolerance);
}

console.log(JSON.stringify({
  schema: "RSH-TISSUE-RUST-WASM-CONFORMANCE-RESULT-V1",
  status: "PASS",
  samples: { cells: c.cells, ticks: c.ticks },
  compared_numeric_observables: numberCount,
  maximum_cross_runtime_residual: maxResidual,
  tolerance,
  python_receipt: pythonReport.receipt,
  rust_native_receipt: rustReport.receipt,
  rust_wasm_receipt: wasmReport.receipt,
  native_wasm_receipt_identity_required: false,
  native_wasm_receipt_identical: rustReport.receipt === wasmReport.receipt,
  python_receipt_identity_required: false,
  geometry_receipt_authority: false,
  subjective_awareness_claim: false,
}, null, 2));
