#!/usr/bin/env node

import assert from "node:assert/strict";
import {
  PARALLEL_GATES,
  ParallelResidualGateError,
  assertResidualGates,
  createRejectedParallelSidecar,
  failedResidualGates,
  gatePassed,
} from "../web/parallel-evidence.js";

const passing = {
  maxPosition: 1e-6,
  maxFrame: 2e-6,
  maxSchedule: 3e-7,
  maxFrameNorm: 4e-7,
  maxFrameOrthogonality: 5e-7,
};
assert.equal(gatePassed(passing), true);
assert.deepEqual(failedResidualGates(passing), []);
assert.doesNotThrow(() => assertResidualGates(passing, "warm-up", 1));

const rejected = {
  ...passing,
  maxFrameNorm: PARALLEL_GATES.frameNorm * 2,
  elapsedMilliseconds: 12.5,
  metadata: {
    adapter: "nvidia · blackwell",
    browser: "test browser",
    scan_passes: 13,
    timing_scope: "buffer-allocation-command-encoding-submit-readback",
    actual_gpu_execution: true,
    geometry_receipt_authority: false,
  },
};

let gateError;
try {
  assertResidualGates(rejected, "warm-up", 2);
} catch (error) {
  gateError = error;
}
assert.ok(gateError instanceof ParallelResidualGateError);
assert.equal(gateError.stage, "warm-up");
assert.equal(gateError.runIndex, 2);
assert.deepEqual(gateError.failures.map((failure) => failure.name), ["frame_norm"]);

const oracle = {
  parallel_contract: "RSH-FRENET-PARALLEL-V1",
  interval_policy: "midpoint-rodrigues-se3-v1",
  scan_policy: "hillis-steele-inclusive-se3-v1",
  model: "Robitaille-Slade Helix",
  model_version: "2.0.0",
};
const configuration = {
  samples: 4097,
  s0: 0,
  s1: 4,
  kappaFraction: 0.85,
  tauFloor: 0.22,
  tauAmplitude: 0.13,
};
const sidecar = createRejectedParallelSidecar({
  oracle,
  config: configuration,
  error: gateError,
  warmupRuns: 2,
  measuredRuns: 7,
  wasmTimings: [4, 3.8, 3.9],
  gpuTimings: [],
  wasmMedian: 3.9,
  minimumSpeedupSamples: 4097,
});

assert.equal(sidecar.status, "REJECTED");
assert.equal(sidecar.failure.stage, "warm-up");
assert.equal(sidecar.failure.run_index, 2);
assert.equal(sidecar.failure.failed_gates[0].name, "frame_norm");
assert.equal(sidecar.residuals.max_frame_norm_error, rejected.maxFrameNorm);
assert.equal(sidecar.actual_gpu_execution, true);
assert.equal(sidecar.complete_path_readback, true);
assert.equal(sidecar.conformance_passed, false);
assert.equal(sidecar.speedup_claim, false);
assert.equal(sidecar.universal_speedup_claim, false);
assert.equal(sidecar.geometry_receipt_authority, false);
assert.equal(sidecar.benchmark.benchmark_completed, false);

console.log(JSON.stringify({
  schema: "RSH-WEBGPU-PARALLEL-REJECTION-REGRESSION-V1",
  status: "PASS",
  failed_gate: sidecar.failure.failed_gates[0],
  rejection_evidence_retained: true,
  speedup_claim: false,
  universal_speedup_claim: false,
  geometry_receipt_authority: false,
}, null, 2));
