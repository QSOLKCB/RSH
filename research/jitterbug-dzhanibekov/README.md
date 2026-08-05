# Jitterbug / Dzhanibekov exploratory attitude study

This directory documents the input boundary for RSH’s exploratory attitude
laboratory. The executable model lives in `web/attitude-model.js` so the same
deterministic implementation is exercised by Node CI and the offline browser
surface.

## What is implemented

1. A torque-free rigid-body reference with fixed principal moments
   `I1 < I2 < I3` and an initial spin dominated by the intermediate axis.
2. A reduced variable-inertia analogue with a prescribed bounded shape
   coordinate `lambda(t)` and a smoothly rotating positive-definite inertia
   tensor.
3. Unit-quaternion kinematics with normalization after every fixed RK4 step.
4. Geodesic quaternion comparison after a global orientation alignment, time
   translation, and one scalar time-rescaling factor.
5. Explicit claim boundaries and a deterministic exploratory regression profile.

The second model is **not a validated Fuller Jitterbug mechanism**. It does not
contain articulated members, hinges, constraint forces, internal generalized
momentum, collisions, or experimental calibration.

## Future mechanism input boundary

A physically meaningful Jitterbug experiment should provide a data set matching
`vertex-schema.example.json` or a later versioned successor. At minimum it needs:

- member and vertex identifiers;
- vertex coordinates as a function of a shape coordinate;
- fixed-length and articulated constraints;
- member masses or mass density;
- allowed shape-coordinate range and lock limits;
- shape velocity or generalized momentum;
- initial attitude and total angular momentum;
- provenance and units.

A future multibody solver must receive a separate contract name. It must not
silently replace the reduced analogue or the RSH geometry oracle.

## Run

```bash
node scripts/test_attitude_exploratory.mjs \
  conformance/attitude_exploratory_v1.json
```

The browser laboratory is `web/attitude.html` and is deployed to:

```text
https://qsolkcb.github.io/RSH/attitude.html
```

## Non-claims

```text
jitterbug_is_dzhanibekov: false
proves_quantized_spacetime: false
visual_similarity_establishes_identical_dynamics: false
rsh_contains_validated_jitterbug_dynamics: false
geometry_receipt_authority: false
universal_scale_invariance_claim: false
physical_equivalence_claim: false
```
