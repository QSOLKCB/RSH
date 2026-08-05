# RSH upgrade roadmap

This roadmap turns the repository's current implementation notes into an ordered
research and engineering programme. It supplements the historical phase record
in [`docs/ROADMAP.md`](docs/ROADMAP.md).

RSH keeps three boundaries explicit throughout this programme:

1. the Python geometry implementation remains the readable scientific oracle;
2. later runtimes are accepted through declared contracts and conformance gates;
3. performance, complexity, hardware execution, or anthropomorphic language does
   not promote an implementation to scientific authority.

## Status key

| Status | Meaning |
|---|---|
| **Complete** | Implemented, documented, and exercised by the validation matrix. |
| **Active** | Current development track with an explicit contract and evidence plan. |
| **Queued** | Accepted direction, not yet under implementation. |
| **Exploratory** | Research question without a sealed implementation contract. |

## 1. Rust/WASM tissue conformance

**Status: Complete in v2.7.0**

- port the Python tissue simulation to the shared `rsh-tissue` Rust crate;
- expose the same implementation through a bounded raw WASM ABI;
- compare Python, native Rust, and compiled WASM observables under the sealed
  tissue tolerance;
- preserve runtime-scoped receipts and the no-qualia/no-authority boundary;
- publish the offline browser tissue laboratory and add it to the validation
  matrix.

Acceptance evidence is recorded by `conformance/tissue_v1_8x20.json` and
`scripts/test_tissue_wasm.mjs`.

## 2. Parallel Frenet acceleration research

**Status: Active — first implementation milestone in progress**

The current full-path WGSL kernel executes the entire recurrence on a real GPU,
but does so in one invocation because each state depends on its predecessor. The
next contract will replace that serial recurrence with an associative prefix
composition of local rigid transforms.

### Planned milestones

1. Define `RSH-FRENET-PARALLEL-V1` independently of the canonical geometry and
   existing projected sequential numerical contract.
2. Represent every interval as a local SE(3) transform containing:
   - the midpoint Rodrigues frame rotation;
   - the midpoint-tangent displacement;
   - the interval schedule metadata required for evidence.
3. Define a deterministic inclusive doubling scan whose composition order is
   stable across native Rust, WASM, and WGSL.
4. Add a native f64 reference and compiled WASM bridge.
5. Add a multi-pass WGSL implementation using parallel interval construction,
   ping-pong prefix passes, parallel path emission, and midpoint centering.
6. Compare every returned position, frame, curvature, and torsion component with
   the f64 parallel reference under separately published gates.
7. Add browser benchmarking with warm-up, repeated measurements, medians,
   adapter metadata, and readback-inclusive timing.
8. Permit an **observed speedup statement** only when the real adapter executes,
   conformance passes, the benchmark protocol is complete, and the sidecar
   records the exact device, browser, sample count, and timing method.
9. Define shard summaries for multi-device or distributed experiments. A shard
   may export a local transform reduction, but no distributed result is accepted
   until ordered merge and full-path readback reproduce the same contract.

### Non-goals for the first milestone

- no universal GPU speedup claim;
- no replacement of the canonical geometry receipt;
- no silent reuse of the sequential per-step Gram–Schmidt policy, because that
  nonlinear projection is not associative;
- no claim that browser WebGPU exposes multiple physical GPUs;
- no distributed networking layer before deterministic shard composition is
  demonstrated locally.

## 3. NPU hardware support

**Status: Queued**

- add vendor-neutral host abstractions before device-specific drivers;
- implement INT8, BF16, and FP16 schedule or path kernels;
- require actual device execution, synchronization, and readback;
- preserve CPU/WASM fallback and precision-specific residual gates;
- record device, driver, compiler, precision, quantization parameters, grid, and
  residual metadata;
- validate on real NPU hardware before changing the profile-only status.

The existing `conformance/npu_tier2_v1.json` remains a requirements profile, not
a hardware-execution claim.

## 4. WebGPU full-path laboratory enhancements

**Status: Queued**

- live parameter tuning for sequential and parallel path contracts;
- step and interval inspection for position, tangent, normal, and binormal;
- frame-by-frame residual debugging;
- selectable overlays for f64 WASM, sequential f32 WGSL, and parallel f32 WGSL;
- exportable snapshots and residual traces;
- richer 3D navigation without turning the display into evidence.

## 5. C++ and CUDA expansion

**Status: Queued**

- unified-memory experiments for large evidence grids;
- explicit multi-device partitioning and ordered reduction;
- a separately versioned CUDA full-path or tissue adapter;
- richer C++17 report, trace, and benchmark commands;
- continued sanitizer, ownership, ABI-layout, and authority-boundary testing.

No CUDA adapter becomes geometry authority, and CUDA schedule validation remains
separate from full-path or tissue execution.

## 6. Fuzzing expansion

**Status: Queued**

- tissue configuration and audit-chain fuzz targets;
- C ABI ownership, length, layout, and malformed-input fuzzing;
- WASM pointer/length and structured-error boundary fuzzing;
- differential Python/Rust tissue fuzzing over bounded configurations;
- reduction of every discovered failure into a deterministic regression case;
- scheduled or continuous fuzzing that never executes untrusted public-PR code
  on privileged hardware.

## 7. Documentation and examples

**Status: Queued**

- guided examples for Python geometry, Rust geometry, tissue, numerical paths,
  WASM laboratories, C++ FFI, and CUDA evidence;
- crate-level API documentation and examples that compile in CI;
- tutorials explaining receipts, runtime identity, residual sidecars, and the
  difference between a correctness surface and an oracle;
- research notebooks or static derivations that do not become runtime
  dependencies.

## 8. Dependency and toolchain maintenance

**Status: Continuous**

- evaluate new Rust editions before migration and record the minimum supported
  compiler;
- keep Python coverage current without weakening the reference-runtime policy;
- test supported CUDA toolkits and GPU architectures through explicit profiles;
- track WebGPU and core WASM changes through browser-source validation;
- update dependencies only with locked builds and full conformance replay.

## 9. Additional geometry and tissue models

**Status: Exploratory**

Any alternative curvature/torsion bounds, path generators, tissue update laws,
or Q_f factors require new names and contracts. They must not silently modify the
Robitaille–Slade model, tissue contract 1.0.0, or existing receipts.

Candidate work:

- alternative bounded schedule families;
- Bishop/parallel-transport handling for zero-curvature intervals;
- additional graph topologies and update policies;
- explicitly versioned Q_f factor extensions;
- model-comparison reports that keep each contract's evidence separate.

## 10. Performance optimization

**Status: Queued, with measurements required**

- profile `rsh-core`, `rsh-numerics`, and `rsh-tissue` before optimization;
- evaluate portable SIMD for schedule, frame, and metric calculations;
- reduce WASM size and parse/allocation overhead;
- add benchmark baselines and regression thresholds only after stable runner
  methodology is established;
- distinguish kernel time, transfer time, serialization time, and end-to-end
  latency.

Optimization must preserve contract output within its declared tolerance.

## 11. CI/CD and hardware automation

**Status: Queued**

- maintain trusted self-hosted GPU runners for manual or protected-branch CUDA
  and WebGPU validation;
- add automated browser execution through a controlled hardware environment;
- upload conformance and performance sidecars as immutable workflow artifacts;
- detect performance regressions only on pinned hardware and toolchains;
- never expose privileged hardware runners to arbitrary public pull-request code.

## 12. Cross-language contract testing

**Status: Continuous expansion**

- add more sealed configurations rather than relying on one golden case;
- add property-based invariants for bounds, centering, frame orthonormality,
  deterministic replay, and audit-chain completeness;
- compare Python, native Rust, WASM, C++/FFI, WGSL, CUDA, and future NPU outputs
  only where they implement the same named contract;
- record receipt identity separately from numerical observable conformance;
- strengthen profiles with negative cases and malformed-evidence rejection.

## Recommended order

The current priority sequence is:

1. complete the parallel Frenet contract and single-device WGSL scan;
2. collect real browser GPU measurements and publish noncanonical observations;
3. prove deterministic shard composition before multi-device experiments;
4. expand fuzzing around the new parallel and tissue boundaries;
5. proceed to hardware-backed NPU work;
6. continue documentation, toolchain maintenance, performance profiling, and
   cross-language matrix expansion throughout.
