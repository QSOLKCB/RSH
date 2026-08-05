#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const wasmPath = process.argv[2]
  ?? "target/wasm32-unknown-unknown/release/rsh_parallel_wasm.wasm";
const profilePath = process.argv[3] ?? "conformance/frenet_parallel_v1_1025.json";
const nativeReportPath = process.argv[4] ?? join(tmpdir(), "rsh_parallel_native.json");

const [wasmBytes, profile, nativeReport] = await Promise.all([
  readFile(wasmPath),
  readFile(profilePath, "utf8").then(JSON.parse),
  readFile(nativeReportPath, "utf8").then(JSON.parse),
]);
assert.equal(
  Buffer.from(wasmBytes.subarray(0, 4)).toString("hex"),
  "0061736d",
  "invalid parallel WebAssembly magic header",
);

const { instance } = await WebAssembly.instantiate(wasmBytes, {});
const api = instance.exports;
for (const name of [
  "memory",
  "rsh_parallel_abi_version",
  "rsh_parallel_run",
  "rsh_parallel_output_ptr",
  "rsh_parallel_output_len",
]) {
  assert.ok(name in api, `missing parallel WASM export: ${name}`);
}
assert.equal(Number(api.rsh_parallel_abi_version()), 1);

const c = profile.configuration;
const status = Number(api.rsh_parallel_run(
  c.samples,
  c.s0,
  c.s1,
  c.kappa_fraction,
  c.tau_floor,
  c.tau_amplitude,
));
const pointer = Number(api.rsh_parallel_output_ptr());
const length = Number(api.rsh_parallel_output_len());
assert.ok(Number.isSafeInteger(pointer) && pointer >= 0, "invalid parallel output pointer");
assert.ok(Number.isSafeInteger(length) && length > 0, "invalid parallel output length");
assert.ok(
  pointer <= api.memory.buffer.byteLength
    && length <= api.memory.buffer.byteLength - pointer,
  "parallel output span exceeds WASM memory",
);
const payload = JSON.parse(
  new TextDecoder().decode(new Uint8Array(api.memory.buffer, pointer, length)),
);
assert.equal(status, 0, payload.message ?? "parallel WASM failed");
assert.equal(payload.schema, "RSH-FRENET-PARALLEL-RUN-V1");
assert.equal(payload.parallel_contract, profile.parallel_contract);
assert.equal(payload.interval_policy, profile.interval_policy);
assert.equal(payload.scan_policy, profile.scan_policy);
assert.equal(payload.actual_parallel_hardware_execution, false);
assert.equal(payload.distributed_execution, false);
assert.equal(payload.speedup_claim, false);
assert.equal(payload.geometry_receipt_authority, false);

const report = payload.report;
assert.equal(report.schema, "RSH-FRENET-PARALLEL-RUN-V1");
assert.equal(report.pass_all, true);
assert.equal(report.scan_passes, profile.expected.scan_passes);
assert.equal(report.intervals, profile.expected.intervals);
assert.equal(report.samples, c.samples);
assert.equal(payload.points.length, c.samples);
assert.equal(payload.points[profile.expected.centre_index].p, profile.expected.centre_p);
for (const key of [
  "pass_finite",
  "pass_centre",
  "pass_frame",
  "pass_schedule_bounds",
  "pass_scan_equivalence",
  "pass_shard_merge",
]) {
  assert.equal(report[key], profile.requirements[key], `${key} mismatch`);
}
assert.ok(
  Math.hypot(...report.centre) <= profile.expected.maximum_centre_error,
  "parallel centre residual exceeds profile",
);
assert.ok(
  report.max_frame_norm_error <= profile.expected.maximum_frame_error_f64,
  "parallel frame norm residual exceeds profile",
);
assert.ok(
  report.max_frame_orthogonality_error <= profile.expected.maximum_frame_error_f64,
  "parallel frame orthogonality residual exceeds profile",
);
assert.ok(
  report.max_scan_vs_sequential_component_error
    <= profile.expected.maximum_scan_vs_sequential_component_error,
  "parallel scan residual exceeds profile",
);
assert.ok(
  report.max_shard_merge_component_error
    <= profile.expected.maximum_shard_merge_component_error,
  "parallel shard merge residual exceeds profile",
);

const tolerance = profile.expected.native_wasm_observable_tolerance;
let comparedNumbers = 0;
let maximumResidual = 0;
function comparePortable(actual, expected, path = "report") {
  if (typeof expected === "number") {
    assert.equal(typeof actual, "number", `${path} must be numeric`);
    assert.ok(Number.isFinite(actual) && Number.isFinite(expected), `${path} must be finite`);
    const residual = Math.abs(actual - expected);
    comparedNumbers += 1;
    maximumResidual = Math.max(maximumResidual, residual);
    assert.ok(residual <= tolerance, `${path} residual ${residual} exceeds ${tolerance}`);
    return;
  }
  if (Array.isArray(expected)) {
    assert.ok(Array.isArray(actual), `${path} must be an array`);
    assert.equal(actual.length, expected.length, `${path} length mismatch`);
    expected.forEach((value, index) => comparePortable(actual[index], value, `${path}[${index}]`));
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
comparePortable(report, nativeReport);

for (const point of payload.points) {
  const numbers = [
    point.p, point.s, point.x, point.y, point.z, point.kappa, point.tau,
    point.tx, point.ty, point.tz, point.nx, point.ny, point.nz,
    point.bx, point.by, point.bz,
  ];
  assert.ok(numbers.every(Number.isFinite), `non-finite point ${point.index}`);
}

console.log(JSON.stringify({
  schema: "RSH-FRENET-PARALLEL-WASM-CONFORMANCE-RESULT-V1",
  status: "PASS",
  samples: c.samples,
  scan_passes: report.scan_passes,
  compared_report_numbers: comparedNumbers,
  maximum_native_wasm_residual: maximumResidual,
  tolerance,
  actual_parallel_hardware_execution: false,
  actual_multi_device_execution: false,
  speedup_claim: false,
  geometry_receipt_authority: false,
}, null, 2));
