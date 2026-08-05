#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  CLAIM_BOUNDARIES,
  compareAttitudeTrajectories,
  integrateDzhanibekov,
  integrateJitterbugAnalogue,
  jitterbugInertiaState,
  quaternionDistance,
} from "../web/attitude-model.js";

const profilePath = process.argv[2] ?? "conformance/attitude_exploratory_v1.json";
const profile = JSON.parse(await readFile(profilePath, "utf8"));

const dz = integrateDzhanibekov(profile.dzhanibekov);
const jb = integrateJitterbugAnalogue(profile.jitterbug);
const comparison = compareAttitudeTrajectories(dz, jb, profile.comparison);

assert.equal(dz.schema, "RSH-EXPLORATORY-DZHANIBEKOV-RIGID-V1");
assert.equal(jb.schema, "RSH-EXPLORATORY-JITTERBUG-VARIABLE-INERTIA-V1");
assert.equal(comparison.schema, "RSH-ATTITUDE-COMPARISON-EXPLORATORY-V1");
assert.equal(comparison.verdict, profile.expected.verdict);
assert.ok(
  dz.invariants.angular_momentum.relative_drift
    <= profile.expected.dzhanibekov_max_angular_momentum_relative_drift,
);
assert.ok(
  dz.invariants.energy.relative_drift
    <= profile.expected.dzhanibekov_max_energy_relative_drift,
);
assert.ok(
  jb.invariants.angular_momentum.relative_drift
    <= profile.expected.jitterbug_max_angular_momentum_relative_drift,
);
assert.ok(
  jb.invariants.energy.relative_drift
    >= profile.expected.jitterbug_min_energy_relative_drift,
);
assert.ok(
  dz.invariants.quaternion_normalization_error_max
    <= profile.expected.maximum_quaternion_normalization_error,
);
assert.ok(
  jb.invariants.quaternion_normalization_error_max
    <= profile.expected.maximum_quaternion_normalization_error,
);
assert.ok(dz.attitude_reversals_approx_180deg.length >= profile.expected.minimum_dzhanibekov_reversals);
assert.ok(jb.attitude_reversals_approx_180deg.length >= profile.expected.minimum_jitterbug_reversals);
assert.ok(
  comparison.best_alignment.quaternion_distance.rms_deg
    >= profile.expected.minimum_best_alignment_rms_degrees,
);
assert.ok(
  comparison.best_excursion_alignment.attitude_excursion_correlation
    >= profile.expected.minimum_excursion_correlation,
);
assert.ok(
  comparison.best_excursion_alignment.attitude_excursion_correlation
    <= profile.expected.maximum_excursion_correlation,
);

const signInvariant = quaternionDistance([0, 0, 0, 1], [0, 0, 0, -1]);
assert.ok(signInvariant <= Number.EPSILON);

for (const time of [0, 1, 2, 4, 8, 17.5]) {
  const state = jitterbugInertiaState(time, profile.jitterbug);
  assert.ok(state.lambda >= 0 && state.lambda <= 1);
  assert.ok(state.principal_moments.every((value) => Number.isFinite(value) && value > 0));
  assert.ok(state.inertia.flat().every(Number.isFinite));
  assert.ok(state.inertia_rate.flat().every(Number.isFinite));
}

for (const [name, value] of Object.entries(CLAIM_BOUNDARIES)) {
  assert.equal(value, false, `${name} must remain false`);
  assert.equal(comparison.claims[name], false, `${name} must remain false in report`);
}

assert.throws(
  () => integrateDzhanibekov({ inertia: [1, 1, 3], duration: 1, dt: 0.01 }),
  /I1 < I2 < I3/,
);
assert.throws(
  () => integrateJitterbugAnalogue({ inertiaClosed: [1, 0, 2], duration: 1, dt: 0.01 }),
  /positive/,
);
assert.throws(
  () => integrateJitterbugAnalogue({ shapePeriod: 0, duration: 1, dt: 0.01 }),
  /positive/,
);

console.log(JSON.stringify({
  schema: "RSH-ATTITUDE-EXPLORATORY-REGRESSION-V1",
  status: "PASS",
  verdict: comparison.verdict,
  dzhanibekov: {
    samples: dz.samples.length,
    reversals: dz.attitude_reversals_approx_180deg.length,
    angular_momentum_relative_drift: dz.invariants.angular_momentum.relative_drift,
    energy_relative_drift: dz.invariants.energy.relative_drift,
    maximum_quaternion_normalization_error: dz.invariants.quaternion_normalization_error_max,
  },
  jitterbug_analogue: {
    samples: jb.samples.length,
    reversals: jb.attitude_reversals_approx_180deg.length,
    angular_momentum_relative_drift: jb.invariants.angular_momentum.relative_drift,
    generalized_energy_relative_drift: jb.invariants.energy.relative_drift,
    maximum_quaternion_normalization_error: jb.invariants.quaternion_normalization_error_max,
  },
  comparison: comparison.best_alignment,
  geometry_receipt_authority: false,
  physical_equivalence_claim: false,
  universal_scale_invariance_claim: false,
}, null, 2));
