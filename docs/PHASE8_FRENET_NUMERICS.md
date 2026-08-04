# Phase 8 — separately versioned Frenet numerical research

## Status

Implemented as a **research surface in v2.6.0**.

This phase deliberately does not alter the canonical geometry contract in
`rsh-core`. The existing midpoint integrator, geometry report, golden vectors,
and receipt domain remain unchanged. New numerical and accelerator work lives in
separate crates, schemas, WASM exports, shader assets, and evidence sidecars.

## Mathematical form

For the orthonormal frame

```text
Q(s) = [T(s) | N(s) | B(s)] ∈ SO(3)
```

the Frenet–Serret system is represented as

```text
Q'(s) = Q(s) A(s)

A(s) = [ 0      -κ(s)    0    ]
       [ κ(s)    0      -τ(s) ]
       [ 0        τ(s)   0    ]
```

`A(s)` is skew-symmetric. Phase 8 evaluates it at each interval midpoint and
advances the frame through the SO(3) exponential map. Position is advanced with
the corresponding midpoint tangent. Modified Gram–Schmidt is applied after each
full frame step, and the exact discrete midpoint is translated to the origin.

This policy is named and frozen as:

```text
RSH-FRENET-NUMERICS-V1
lie-midpoint-so3-projected-v1
```

## Rust surfaces

- `rsh-numerics` implements the f64 research path and path-level report;
- `rsh-numerics-cli` supplies `info`, `run`, and non-gating `benchmark` commands;
- `rsh-numerics-wasm` exposes the same research path through a separate raw ABI;
- `conformance/frenet_path_v1_1025.json` seals the 1,025-point vectors and gates.

Run the f64 path:

```bash
cargo run --locked -p rsh-numerics-cli -- \
  run -n 1025 \
  --json /tmp/rsh_frenet_path.json \
  --csv /tmp/rsh_frenet_path.csv
```

Run a measurement without creating a performance acceptance gate:

```bash
cargo run --release --locked -p rsh-numerics-cli -- \
  benchmark -n 16385 --loops 20
```

The benchmark reports elapsed time only. It does not claim a speedup and does
not alter numerical acceptance.

## Full-path WGSL execution

`web/wgsl/frenet_path.wgsl` performs all of the following on the adapter:

1. bounded κ and τ evaluation;
2. SO(3) midpoint frame advancement;
3. midpoint position integration;
4. tangent, normal, and binormal storage;
5. per-step frame projection;
6. exact-grid midpoint centering;
7. complete storage-buffer readback.

The first implementation uses one invocation and one workgroup because every
path state depends on its predecessor. This establishes full-path execution and
component-level conformance; it does **not** claim parallel acceleration.
Parallel prefix composition, segmented scans, or interval-transfer operators may
be studied later under another explicitly versioned policy.

The browser research surface is:

```text
https://qsolkcb.github.io/RSH/frenet.html
```

It overlays the f64 Rust/WASM path and the f32 GPU readback, displays the midpoint
T/N/B frame, and permits export only after all published gates pass.

## Path-level gates

The profile compares every sample and records:

- maximum position-component residual;
- maximum tangent/normal/binormal component residual;
- maximum κ/τ residual;
- maximum frame norm error;
- maximum pairwise frame orthogonality error.

The initial f32 research gates are intentionally conservative:

| Quantity | Gate |
|---|---:|
| Position component vs f64 | `2e-4` |
| Frame component vs f64 | `2e-4` |
| κ/τ component vs f64 | `1e-4` |
| Frame norm error | `2e-6` |
| Frame orthogonality error | `2e-6` |

A passing WebGPU result may emit
`RSH-WEBGPU-FRENET-PATH-SIDECAR-V1`. The sidecar records actual adapter execution
but has no canonical geometry-receipt authority.

## Fuzz and stress testing

Routine workspace tests execute a deterministic bounded configuration corpus.
A separate `cargo-fuzz` target mutates sample counts, arc-length intervals,
curvature fractions, torsion floors, and torsion amplitudes while constructing
only valid bounded configurations.

The scheduled `Frenet Fuzz` workflow is manual and weekly. Fuzz findings must be
reduced into deterministic regression cases before they can affect a contract.
The workflow is not a substitute for path-level conformance vectors.

## Degeneracy boundary

The current Robitaille-defined schedules keep curvature positive, so the Frenet
normal remains defined inside this package. General curve imports may contain
zero-curvature intervals, non-regular points, derivative noise, or lower-
dimensional degeneracy. Such inputs require a separately specified frame policy,
such as a Bishop or parallel-transport fallback, before they can enter this
contract.

Coordinate-axis singularities from alternative local-coordinate formulations are
not hidden by this implementation. The SO(3) formulation avoids selecting a
privileged global axis, while finite-value, frame, and schedule checks remain
mandatory.

## Source basis

The implementation was informed by:

- the matrix and moving-frame Frenet–Serret formulation;
- the interpretation of the frame ODE on `SO(3)` / `SO(d)`;
- midpoint exponential-map approximations for frame transport;
- higher-dimensional independence and degeneracy conditions;
- the distinction between curvature/torsion data and rigid Euclidean placement.

Useful public references include:

- https://mathworld.wolfram.com/FrenetFormulas.html
- https://web.mit.edu/hyperbook/Patrikalakis-Maekawa-Cho/node25.html
- https://dmnsgn.github.io/frenet-serret-frames/

The papers supplied with the implementation review are listed in the PR evidence
notes. They are research references, not bundled runtime dependencies.

## Authority boundary

This phase proves neither a physical interpretation nor a universal fastest
integrator. It establishes a named numerical policy, executable f64 vectors, a
full-path f32 adapter experiment, deterministic stress coverage, and explicit
fallback.

The accepted `rsh-core` geometry path and receipt remain authoritative for the
geometry contract. Phase 8 results are numerical research evidence only.
