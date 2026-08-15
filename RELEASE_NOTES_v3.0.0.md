# RSH v3.0.0 — Machine-Checked Geometry

RSH v3.0.0 adds the project's first Lean 4 formal theorem surface while preserving the authority and version boundaries of the existing geometry, tissue, numerical, accelerator, and evidence contracts.

## Authors

- Dr. J. Robitaille
- Trent Slade

## Contributor

- ChatGPT 5.6 Sol Thinking — formalization implementation and proof-engineering assistance

## Highlights

- Adds `RSH-FORMAL-V1` under `formal/lean/`.
- Pins Lean 4.32.1 and Mathlib v4.32.1 at commit `520045ab14e26149ee970e2e617ca04b09bde5d6`.
- Machine-checks the three fibre-selected exact median reflections used by the Sierpiński inversive-witness contract.
- Proves exact reflection involution and squared-norm preservation.
- Proves the exact inversive radius invariant `r² × r'² = 1/9` over rational arithmetic.
- Proves exact double application of the same fibre transformation recovers the source point.
- Proves `2^32 < 3^21` and an injective unsigned-32 embedding into the 21-trit numeric address capacity.
- Proves the six algebraic Frenet–Serret compatibility identities for an orthonormal frame.
- Proves the exact coordinate-normalization identity underlying discrete midpoint centring.
- Proves monotone endpoint admission, start-above-bound refusal, and uniqueness of a strict-antitone curvature crossing.
- Proves positivity of the analytic torsion derivative-sign polynomial for positive `a` and nonnegative `t`.
- Adds a CI audit that rejects `sorry`, `admit`, and project-defined axioms/constants and publishes Lean axiom reports for release theorems.
- Adds Zenodo-ready `.zenodo.json` metadata separating human creators from the AI contributor role.

## Scientific boundary

The formalization certifies the propositions stated in `RSH-FORMAL-V1`. It does not certify binary64 rounding behavior, receipt serialization, accelerator execution, experimental physics, biological interpretation, consciousness, sentience, or qualia.

The Python geometry oracle remains the readable canonical implementation of the prescribed-schedule geometry contract. Rust/WASM/FFI/accelerator implementations remain conformance surfaces. Formal proofs do not silently change those authority boundaries.

## Reproduce

```bash
cd formal/lean
lake update
lake exe cache get
bash audit.sh
```

## Zenodo suggestion

**Title:** RSH v3.0.0: Machine-Checked Robitaille–Slade Helix Geometry and Deterministic Evidence

**Resource type:** Software

**Creators:** Dr. J. Robitaille; Trent Slade

**Contributor:** ChatGPT 5.6 Sol Thinking (Other / formalization and proof-engineering assistance)
