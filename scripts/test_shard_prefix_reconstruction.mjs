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
const CSV_COLUMNS = [
  "index", "p", "s", "x", "y", "z", "kappa", "tau",
  "tx", "ty", "tz", "nx", "ny", "nz", "bx", "by", "bz",
];
const CSV_HEADER = CSV_COLUMNS.join(",");
const CSV_COMPONENT_FIELDS = CSV_COLUMNS.slice(1);

function finiteNumber(value, label) {
  assert.equal(typeof value, "number", `${label} must be a number`);
  assert.ok(Number.isFinite(value), `${label} must be finite`);
  return value;
}

function finiteTriplet(value, label) {
  assert.ok(Array.isArray(value), `${label} must be an array`);
  assert.equal(value.length, 3, `${label} must contain three components`);
  return value.map((component, index) => finiteNumber(component, `${label}[${index}]`));
}

function finiteTolerance(value, label) {
  const numeric = finiteNumber(value, label);
  assert.ok(numeric >= 0, `${label} must be non-negative`);
  return numeric;
}

function assertClose(actual, expected, tolerance, label) {
  finiteNumber(actual, `${label} actual`);
  finiteNumber(expected, `${label} expected`);
  finiteTolerance(tolerance, `${label} tolerance`);
  const scale = Math.max(1, Math.abs(actual), Math.abs(expected));
  const difference = Math.abs(actual - expected);
  assert.ok(
    difference <= tolerance * scale,
    `${label} differs by ${difference}, exceeding ${tolerance * scale}`,
  );
}

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
  finiteNumber(value, "fingerprint input");
  const bytes = Buffer.alloc(8);
  bytes.writeDoubleLE(value);
  return bytes;
}

function transformValues(transform) {
  assert.ok(transform && typeof transform === "object", "transform must be an object");
  return [
    ...finiteTriplet(transform.tangent, "transform.tangent"),
    ...finiteTriplet(transform.normal, "transform.normal"),
    ...finiteTriplet(transform.binormal, "transform.binormal"),
    ...finiteTriplet(transform.translation, "transform.translation"),
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

function identityTransform() {
  return {
    tangent: [1, 0, 0],
    normal: [0, 1, 0],
    binormal: [0, 0, 1],
    translation: [0, 0, 0],
  };
}

function add(left, right) {
  return [left[0] + right[0], left[1] + right[1], left[2] + right[2]];
}

function rotate(transform, vector) {
  return add(
    add(
      transform.tangent.map((value) => value * vector[0]),
      transform.normal.map((value) => value * vector[1]),
    ),
    transform.binormal.map((value) => value * vector[2]),
  );
}

function compose(left, right) {
  return {
    tangent: rotate(left, right.tangent),
    normal: rotate(left, right.normal),
    binormal: rotate(left, right.binormal),
    translation: add(left.translation, rotate(left, right.translation)),
  };
}

function inclusiveDoublingScan(transforms) {
  let current = transforms.map((transform) => ({
    tangent: [...transform.tangent],
    normal: [...transform.normal],
    binormal: [...transform.binormal],
    translation: [...transform.translation],
  }));
  let offset = 1;
  while (offset < current.length) {
    const previous = current;
    current = previous.map((transform, index) => (
      index < offset ? transform : compose(previous[index - offset], transform)
    ));
    offset *= 2;
  }
  return current;
}

function reconstructExpectedRows(shardBundle) {
  const configuration = shardBundle.configuration;
  const samples = configuration.samples;
  assert.ok(Number.isSafeInteger(samples) && samples >= 3, "bundle sample count is invalid");
  const reductions = shardBundle.shards.map((shard) => shard.reduction);
  const inclusive = inclusiveDoublingScan(reductions);
  const bases = [identityTransform(), ...inclusive.slice(0, -1)];
  const prefixes = [identityTransform()];
  for (const [index, shard] of shardBundle.shards.entries()) {
    for (const localPrefix of shard.local_prefixes) {
      prefixes.push(compose(bases[index], localPrefix));
    }
  }
  assert.equal(prefixes.length, samples, "reconstructed CSV reference length mismatch");

  const midpoint = prefixes[Math.floor(samples / 2)].translation;
  const denominator = samples - 1;
  const ds = (configuration.s1 - configuration.s0) / denominator;
  const psi = Math.sqrt(2 + Math.sqrt(5));
  const kappaBound = Math.sqrt(2) - 1;

  return prefixes.map((transform, index) => {
    const p = index / denominator;
    const s = configuration.s0 + index * ds;
    const kappa = configuration.kappa_fraction
      * kappaBound
      * (0.92 + 0.08 * Math.cos(0.35 * s * psi));
    const tau = configuration.tau_floor
      + configuration.tau_amplitude * (1 + Math.sin(0.25 * s * psi));
    return {
      index,
      p,
      s,
      x: transform.translation[0] - midpoint[0],
      y: transform.translation[1] - midpoint[1],
      z: transform.translation[2] - midpoint[2],
      kappa,
      tau,
      tx: transform.tangent[0],
      ty: transform.tangent[1],
      tz: transform.tangent[2],
      nx: transform.normal[0],
      ny: transform.normal[1],
      nz: transform.normal[2],
      bx: transform.binormal[0],
      by: transform.binormal[1],
      bz: transform.binormal[2],
    };
  });
}

function parseCsv(text, expectedSamples) {
  const lines = text.trimEnd().split(/\r?\n/);
  assert.equal(lines[0], CSV_HEADER, "path CSV header mismatch");
  assert.equal(lines.length, expectedSamples + 1, "path CSV row count mismatch");
  return lines.slice(1).map((line, rowIndex) => {
    const columns = line.split(",");
    assert.equal(columns.length, CSV_COLUMNS.length, `CSV row ${rowIndex} column count mismatch`);
    assert.match(columns[0], /^(0|[1-9][0-9]*)$/, `CSV row ${rowIndex} index is not canonical`);
    const index = Number(columns[0]);
    assert.ok(Number.isSafeInteger(index), `CSV row ${rowIndex} index is not safe`);
    assert.equal(index, rowIndex, `CSV row ${rowIndex} index is out of order`);
    const row = { index };
    for (let columnIndex = 1; columnIndex < CSV_COLUMNS.length; columnIndex += 1) {
      const token = columns[columnIndex];
      assert.equal(token, token.trim(), `CSV row ${rowIndex} contains padded numeric data`);
      assert.notEqual(token, "", `CSV row ${rowIndex} contains an empty numeric field`);
      row[CSV_COLUMNS[columnIndex]] = finiteNumber(
        Number(token),
        `CSV row ${rowIndex} ${CSV_COLUMNS[columnIndex]}`,
      );
    }
    return row;
  });
}

function compareCsvRows(actualRows, expectedRows, tolerance) {
  assert.equal(actualRows.length, expectedRows.length, "CSV/reference row count mismatch");
  for (const [rowIndex, actual] of actualRows.entries()) {
    const expectedRow = expectedRows[rowIndex];
    assert.equal(actual.index, expectedRow.index, `CSV row ${rowIndex} index mismatch`);
    for (const field of CSV_COMPONENT_FIELDS) {
      assertClose(actual[field], expectedRow[field], tolerance, `CSV row ${rowIndex} ${field}`);
    }
  }
}

function pathLength(rows) {
  let total = 0;
  for (let index = 1; index < rows.length; index += 1) {
    const dx = rows[index].x - rows[index - 1].x;
    const dy = rows[index].y - rows[index - 1].y;
    const dz = rows[index].z - rows[index - 1].z;
    total += Math.hypot(dx, dy, dz);
  }
  return finiteNumber(total, "CSV path length");
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

const reconstructionTolerance = finiteTolerance(
  profile.tolerances.maximum_reconstruction_vs_parallel_component_error,
  "maximum reconstruction tolerance",
);
const localTailTolerance = finiteTolerance(
  profile.tolerances.maximum_local_tail_vs_reduction_component_error,
  "maximum local-tail tolerance",
);
const frameTolerance = finiteTolerance(
  profile.tolerances.maximum_frame_error,
  "maximum frame tolerance",
);
const centreTolerance = finiteTolerance(
  profile.tolerances.maximum_centre_error,
  "maximum centre tolerance",
);

const reconstructionResidual = finiteNumber(
  report.max_reconstruction_vs_parallel_component_error,
  "maximum reconstruction residual",
);
const localTailResidual = finiteNumber(
  report.max_local_tail_vs_reduction_component_error,
  "maximum local-tail residual",
);
const frameNormResidual = finiteNumber(report.max_frame_norm_error, "maximum frame norm error");
const frameOrthogonalityResidual = finiteNumber(
  report.max_frame_orthogonality_error,
  "maximum frame orthogonality error",
);
const centre = finiteTriplet(report.centre, "report.centre");
const entry = finiteTriplet(report.entry, "report.entry");
const exit = finiteTriplet(report.exit, "report.exit");
const reportedPathLength = finiteNumber(report.path_length, "report.path_length");

assert.ok(reconstructionResidual <= reconstructionTolerance);
assert.ok(localTailResidual <= localTailTolerance);
assert.ok(frameNormResidual <= frameTolerance);
assert.ok(frameOrthogonalityResidual <= frameTolerance);
assert.ok(Math.hypot(...centre) <= centreTolerance);

assert.equal(bundle.actual_multi_device_execution, false);
assert.equal(bundle.distributed_execution, false);
assert.equal(bundle.geometry_receipt_authority, false);

const csvRows = parseCsv(csv, profile.configuration.samples);
const expectedRows = reconstructExpectedRows(bundle);
const csvComponentTolerance = Math.min(1e-12, reconstructionTolerance);
compareCsvRows(csvRows, expectedRows, csvComponentTolerance);
for (const [component, value] of entry.entries()) {
  assertClose(csvRows[0][["x", "y", "z"][component]], value, csvComponentTolerance, `entry[${component}]`);
}
const midpointRow = csvRows[Math.floor(csvRows.length / 2)];
for (const [component, value] of centre.entries()) {
  assertClose(midpointRow[["x", "y", "z"][component]], value, csvComponentTolerance, `centre[${component}]`);
}
for (const [component, value] of exit.entries()) {
  assertClose(csvRows.at(-1)[["x", "y", "z"][component]], value, csvComponentTolerance, `exit[${component}]`);
}
assertClose(pathLength(csvRows), reportedPathLength, 1e-12, "reported path length");

// Guard the validator itself against the exact malformed-evidence classes that
// prompted the post-merge hardening review.
assert.throws(() => finiteNumber(null, "negative null residual"));
assert.throws(() => finiteNumber("0", "negative string residual"));
const corruptedRows = csvRows.map((row) => ({ ...row }));
corruptedRows[Math.floor(corruptedRows.length / 3)].x += 1;
assert.throws(() => compareCsvRows(corruptedRows, expectedRows, csvComponentTolerance));

console.log(JSON.stringify({
  schema: "RSH-FRENET-SHARD-PREFIX-CONFORMANCE-RESULT-V1",
  status: "PASS",
  samples: report.samples,
  intervals: report.intervals,
  shard_count: report.shard_count,
  shard_prefix_passes: report.shard_prefix_passes,
  maximum_reconstruction_residual: reconstructionResidual,
  maximum_local_tail_residual: localTailResidual,
  csv_rows_validated: csvRows.length,
  csv_component_tolerance: csvComponentTolerance,
  path_length: reportedPathLength,
  manifest_fingerprint: report.manifest_fingerprint,
  malformed_numeric_evidence_rejected: true,
  corrupted_csv_evidence_rejected: true,
  actual_local_shard_execution: true,
  actual_multi_device_execution: false,
  distributed_execution: false,
  speedup_claim: false,
  geometry_receipt_authority: false,
}, null, 2));
