# Phase 11 — Exploratory Jitterbug / Dzhanibekov attitude dynamics

## Status

**Exploratory research surface.** This phase does not alter the canonical RSH
geometry contract, the tissue contract, or the accepted Frenet numerical and
parallel contracts.

## Research question

A visual comparison suggested that the Fuller Jitterbug transformation and the
Dzhanibekov intermediate-axis effect can display a similar flip-like movement.
Phase 11 asks a narrower, testable question:

> Can a reduced variable-inertia attitude model produce a unit-quaternion path
> with a meaningful geometric resemblance to a torque-free intermediate-axis
> rigid-body trajectory after orientation and time alignment?

The question is about trajectories. It is not a claim that the mechanisms are
physically identical.

## Model A — torque-free rigid body

The rigid reference uses principal moments

```text
I1 < I2 < I3
```

and integrates Euler’s torque-free equations:

```text
d/dt(I omega) + omega × (I omega) = 0
q_dot = 1/2 q ⊗ (omega_x, omega_y, omega_z, 0)
```

The default initial condition is dominated by the intermediate principal axis
with small perturbations. The fixed-step RK4 result is checked for angular
momentum, rotational-energy, and quaternion-norm drift.

## Model B — variable-inertia analogue

The reduced analogue prescribes

```text
lambda(t) = 1/2 (1 - cos(2 pi t / T))
```

and interpolates positive principal moments while rotating their principal-axis
frame smoothly. The equation is expanded as

```text
I omega_dot + I_dot omega + omega × (I omega) = 0
```

and solved for `omega_dot` at each derivative evaluation.

This model allows energy variation because prescribed shape motion can perform
work. It is not a multibody Fuller Jitterbug. A full mechanism needs vertex
geometry, member masses, hinge constraints, shape velocities, lock limits, and
configuration-dependent momentum coupling.

## Quaternion comparison

The attitude distance is

```text
d(q1, q2) = 2 acos(|dot(q1, q2)|)
```

so `q` and `-q` remain equivalent. Comparison permits:

1. one fixed global initial-orientation alignment;
2. time translation;
3. one scalar time-rescaling factor.

The exploratory verdict vocabulary is:

- `STRONG TRAJECTORY RESEMBLANCE`;
- `PARTIAL TRAJECTORY RESEMBLANCE`;
- `NO MATERIAL RESEMBLANCE`;
- `INSUFFICIENT MODEL`.

The default profile is expected to return `PARTIAL TRAJECTORY RESEMBLANCE`: both
models contain large attitude reversals, but complete quaternion paths retain a
large geodesic mismatch.

## Determinism and tests

`web/attitude-model.js` is dependency-free and shared by the browser laboratory
and `scripts/test_attitude_exploratory.mjs`. CI checks:

- deterministic fixed-step output;
- unit-quaternion normalization;
- rigid angular-momentum and energy conservation;
- variable-inertia angular-momentum conservation and nontrivial energy change;
- positive finite inertia tensors;
- quaternion sign invariance;
- malformed-input rejection;
- all claim boundaries remain false.

## Browser surface

```text
https://qsolkcb.github.io/RSH/attitude.html
```

The lab displays two projected inertia wireframes, body axes, attitude-excursion
traces, controls for the analogue shape clock and tilt, and an exportable compact
comparison sidecar. The display is not evidence beyond the calculated report.

## Claim boundaries

Every report states:

```text
jitterbug_is_dzhanibekov: false
proves_quantized_spacetime: false
visual_similarity_establishes_identical_dynamics: false
rsh_contains_validated_jitterbug_dynamics: false
geometry_receipt_authority: false
universal_scale_invariance_claim: false
physical_equivalence_claim: false
```

GPU acceleration is not required for this phase. A future GPU ensemble adapter
could emit residual sidecars against an accepted CPU/WASM model, but would not
become geometry authority.
