# RSH v2.6.0 — Full-Path Frenet Numerical Research

RSH v2.6.0 opens the previously deferred full-path accelerator programme without
changing the accepted geometry model or canonical receipt path.

## New numerical contract

A separate `RSH-FRENET-NUMERICS-V1` contract defines a f64
`lie-midpoint-so3-projected-v1` integrator:

- κ and τ are evaluated at interval midpoints;
- the frame advances through the SO(3) exponential map;
- position advances with midpoint tangent quadrature;
- modified Gram–Schmidt restores the frame after every full step;
- the exact discrete midpoint is translated to the origin;
- path reports explicitly deny canonical geometry-receipt authority.

The canonical Python and `rsh-core` geometry contract remains version 2.0.0 and
retains its existing algorithm, vectors, and receipt domain.

## Rust and WASM research surfaces

New workspace crates:

- `rsh-numerics` — f64 path implementation and path-level report;
- `rsh-numerics-cli` — run, CSV/JSON export, and non-gating benchmark commands;
- `rsh-numerics-wasm` — separate raw WASM ABI for browser and test conformance.

The sealed 1,025-sample profile records entry, centre, exit, and midpoint T/N/B
vectors together with explicit f64 and f32 tolerances.

## Full-path WebGPU laboratory

The new `frenet.html` research page executes the complete recurrence in WGSL:

- curvature and torsion schedules;
- position integration;
- tangent, normal, and binormal updates;
- per-step projection;
- midpoint centering;
- complete storage-buffer readback.

The current shader deliberately uses a single invocation because the path is a
sequential recurrence. It is a full-path correctness milestone, not a parallel
speedup claim.

Passing adapters may export `RSH-WEBGPU-FRENET-PATH-SIDECAR-V1` only after
position, frame, schedule, norm, and orthogonality residuals satisfy the checked-
in gates. Adapter failure or gate failure leaves the f64 Rust/WASM research path
active, while canonical geometry remains in `rsh-core`.

## Fuzz and deterministic stress testing

- a deterministic bounded 96-case corpus runs with ordinary Rust tests;
- a `cargo-fuzz` target mutates valid Frenet path configurations;
- a weekly/manual workflow runs the fuzz target under nightly Rust;
- fuzz results must become deterministic regression vectors before changing a
  contract.

## Performance work

The release adds an explicit native benchmark command for the new numerical
path. Benchmark output is observational and has no pass/fail timing threshold.
The canonical core is not silently rewritten for SIMD, and no speedup is claimed
without controlled measurements.

Future performance work may investigate portable SIMD for independent schedule
batches and parallel interval-composition methods for frame transport. Those
would require their own conformance evidence before promotion.

## Scientific boundary

The new path contract and GPU sidecars are numerical implementation evidence.
They do not validate a physical theory, infer consciousness, or replace the
canonical geometry receipt.
