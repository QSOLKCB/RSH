#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const profilePath = process.argv[2] ?? "conformance/frenet_shard_prefix_v1_4097.json";
const reportPath = process.argv[3] ?? "target/shard-prefix-report.json";
const bundlePath = process.argv[4] ?? "target/shard-prefix-bundle.json";
const csvPath = process.argv[5] ?? "target/shard-prefix-path.csv";

const [profile, report, bundle, csv] = await Promise.all([
  readFile(profilePath, "utf8").then(JSON.parse),
  readFile(reportPath, "utf8").then(JSON.parse),
  readFile(bundlePath, "utf8").then(JSON.parse),
  readFile(csvPath, "utf8"),
]);

const FNV_OFFSET = 0xcbf29ce484222325n;
const FNV_PRIME = 0x100000001b3n;

function fnvUpdate(state, bytes) {
  let next = state;
  for (const byte of bytes) {
    next ^= BigInt(byte);
    next = BigInt.asUintN(64, next * FNV_PRIME);
  }
  return next;
}

function usizeBytes(value) {
  assert.ok(Number.isSafeInteger(value) && value >= 0, "invalid usize value");
  const bytes = Buffer.alloc(8);
  bytes.writeBigUInt64LE(BigInt(value));
  return bytes;
}

function f64Bytes(value) {
  assert.ok(Number.isFinite(value), "fingerprint input must be finite");
  const bytes = Buffer.alloc(8);
  bytes.writeDoubleLE(value);
  return bytes;
}

function transformValues(transform) {
  return [
    ...transform.tangent,
    ...transform.normal,
    ...transform.binormal,
    ...transform.translation,
  ];
}

function shardFingerprint(shard) {
  let state = fnvUpdate(FNV_OFFSET, Buffer.from("RSH-FRENET-SHARD-WORK-V1\0"));
  for (const value of [
    shard.shard_index,
    shard.start_interval,
    shard.end_interval_exclusive,
    shard.local_prefixes.length,
  ]) {
    state = fnvUpdate(state, usizeBytes(value));
  }
  for (const transform of shard.local_prefixes) {
    for (const value of transformValues(transform)) {
      state = fnvUpdate(state, f64Bytes(value));
    }
  }
  for (const value of transformValues(shard.reduction)) {
    state = fnvUpdate(state, f64Bytes(value));
  }
  return state.toString(16).padStart(16, "0");
}

function manifestFingerprint(shards) {
  let state = fnvUpdate(FNV_OFFSET, Buffer.from("RSH-FRENET-SHARD-MANIFEST-V1\0"));
  state = fnvUpdate(state, usizeBytes(shards.length));
  for (const shard of shards) {
    state = fnvUpdate(state, usizeBytes(shard.shard_index));
    state = fnvUpdate(state, Buffer.from(shard.deterministic_fingerprint));
  }
  return state.toString(16).padStart(16, "0");
}

assert.equal(report.schema, "RSH-FRENET-SHARD-PREFIX-RECONSTRUCTION-V1");
assert.equal(report.shard_prefix_contract, profile.shard_prefix_contract);
assert.equal(report.source_parallel_contract, profile.source_parallel_contract);
assert.equal(report.interval_policy, profile.interval_policy);
assert.equal(report.local_prefix_policy, profile.local_prefix_policy);
assert.equal(report.shard_prefix_policy, profile.shard_prefix_policy);
assert.equal(report.assembly_policy, profile.assembly_policy);
assert.equal(report.fingerprint_policy, profile.fingerprint_policy);
assert.equal(bundle.schema, "RSH-FRENET-SHARD-BUNDLE-V1");
assert.equal(bundle.shard_prefix_contract, profile.shard_prefix_contract);
assert.deepEqual(bundle.configuration, profile.configuration);

const expected = profile.sharding;
assert.equal(report.samples, profile.configuration.samples);
assert.equal(report.intervals, expected.expected_intervals);
assert.equal(report.interval_width, expected.interval_width);
assert.equal(report.shard_count, expected.expected_shard_count);
assert.equal(report.shard_prefix_passes, expected.expected_shard_prefix_passes);
assert.equal(report.reconstructed_prefix_count, expected.expected_reconstructed_prefix_count);
assert.equal(bundle.expected_intervals, expected.expected_intervals);
assert.equal(bundle.interval_width, expected.interval_width);
assert.equal(bundle.shard_count, expected.expected_shard_count);
assert.equal(bundle.shards.length, expected.expected_shard_count);
assert.equal(
  bundle.shards.at(-1).interval_count,
  expected.expected_final_shard_interval_count,
);

let expectedStart = 0;
let totalLocalPrefixes = 0;
for (const [index, shard] of bundle.shards.entries()) {
  assert.equal(shard.schema, "RSH-FRENET-SHARD-WORK-V1");
  assert.equal(shard.shard_index, index);
  assert.equal(shard.start_interval, expectedStart);
  assert.equal(
    shard.end_interval_exclusive,
    shard.start_interval + shard.interval_count,
  );
  assert.equal(shard.local_prefixes.length, shard.interval_count);
  assert.equal(shard.geometry_receipt_authority, false);
  assert.equal(shard.fingerprint_policy, profile.fingerprint_policy);
  assert.match(shard.deterministic_fingerprint, /^[0-9a-f]{16}$/);
  assert.equal(shard.deterministic_fingerprint, shardFingerprint(shard));
  assert.deepEqual(shard.local_prefixes.at(-1), shard.reduction);
  expectedStart = shard.end_interval_exclusive;
  totalLocalPrefixes += shard.local_prefixes.length;
}
assert.equal(expectedStart, expected.expected_intervals);
assert.equal(totalLocalPrefixes, expected.expected_intervals);
assert.equal(bundle.manifest_fingerprint, manifestFingerprint(bundle.shards));
assert.equal(report.manifest_fingerprint, bundle.manifest_fingerprint);

for (const [key, value] of Object.entries(profile.requirements)) {
  assert.equal(report[key], value, `${key} mismatch`);
}
assert.ok(
  report.max_reconstruction_vs_parallel_component_error
    <= profile.tolerances.maximum_reconstruction_vs_parallel_component_error,
);
assert.ok(
  report.max_local_tail_vs_reduction_component_error
    <= profile.tolerances.maximum_local_tail_vs_reduction_component_error,
);
assert.ok(report.max_frame_norm_error <= profile.tolerances.maximum_frame_error);
assert.ok(report.max_frame_orthogonality_error <= profile.tolerances.maximum_frame_error);
assert.ok(Math.hypot(...report.centre) <= profile.tolerances.maximum_centre_error);

assert.equal(bundle.actual_multi_device_execution, false);
assert.equal(bundle.distributed_execution, false);
assert.equal(bundle.geometry_receipt_authority, false);

const lines = csv.trimEnd().split("\n");
assert.equal(lines[0], "index,p,s,x,y,z,kappa,tau,tx,ty,tz,nx,ny,nz,bx,by,bz");
assert.equal(lines.length, profile.configuration.samples + 1);
assert.equal(Number(lines[1].split(",")[0]), 0);
assert.equal(Number(lines.at(-1).split(",")[0]), profile.configuration.samples - 1);

console.log(JSON.stringify({
  schema: "RSH-FRENET-SHARD-PREFIX-CONFORMANCE-RESULT-V1",
  status: "PASS",
  samples: report.samples,
  intervals: report.intervals,
  shard_count: report.shard_count,
  shard_prefix_passes: report.shard_prefix_passes,
  maximum_reconstruction_residual: report.max_reconstruction_vs_parallel_component_error,
  maximum_local_tail_residual: report.max_local_tail_vs_reduction_component_error,
  manifest_fingerprint: report.manifest_fingerprint,
  actual_local_shard_execution: true,
  actual_multi_device_execution: false,
  distributed_execution: false,
  speedup_claim: false,
  geometry_receipt_authority: false,
}, null, 2));
