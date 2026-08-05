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

**Status: Complete — single-device hardware validated**

`RSH-FRENET-PARALLEL-V1` now provides:

- midpoint Rodrigues SE(3) interval transforms;
- a deterministic inclusive doubling scan;
- native Rust and compiled WASM f64 references;
- a multi-pass normalized-quaternion WGSL implementation;
- full path readback and residual comparison;
- rejection sidecars that preserve failed hardware evidence;
- real RTX 5060 Ti WebGPU execution at 4,097 samples;
- real `sm_120` CUDA schedule execution, repeatability, and sanitizer evidence;
- a device/browser-scoped observed speedup statement with no universal claim.

The accepted single-device work does not replace the canonical geometry receipt.
Raw hardware evidence containing stable device identifiers remains outside the
public repository; only redacted observations belong in project documentation.

## 3. Deterministic shard-prefix path reconstruction

**Status: Complete — local deterministic reconstruction**

`RSH-FRENET-SHARD-PREFIX-V1` proves the composition boundary required before any
multi-device or distributed experiment:

1. partition the complete interval range into contiguous shard work units;
2. compute every shard's local inclusive prefixes and local reduction;
3. compute exclusive shard bases with an immutable-source Hillis–Steele scan;
4. apply each shard base to every local prefix;
5. assemble the complete ordered path and centre the discrete midpoint;
6. compare every reconstructed point and frame component with
   `RSH-FRENET-PARALLEL-V1`;
7. reject missing, reordered, overlapping, malformed, tampered, non-finite, or
   authority-promoting shard evidence.

The sealed 4,097-point profile uses 257-interval shards, including an irregular
final shard. Evidence is defined by:

```text
conformance/frenet_shard_prefix_v1_4097.json
docs/PHASE12_SHARD_PREFIX_RECONSTRUCTION.md
scripts/test_shard_prefix_reconstruction.mjs
```

This milestone proves local composition correctness only:

```text
actual_multi_device_execution: false
distributed_execution: false
speedup_claim: false
geometry_receipt_authority: false
```

## 4. NPU hardware support

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

## 5. WebGPU full-path laboratory enhancements

**Status: Queued**

- live parameter tuning for sequential and parallel path contracts;
- step and interval inspection for position, tangent, normal, and binormal;
- frame-by-frame residual debugging;
- selectable overlays for f64 WASM, sequential f32 WGSL, and parallel f32 WGSL;
- exportable snapshots and residual traces;
- richer 3D navigation without turning the display into evidence.

## 6. C++ and CUDA expansion

**Status: Queued**

- unified-memory experiments for large evidence grids;
- explicit multi-device partitioning using the accepted shard-prefix contract;
- a separately versioned CUDA full-path or tissue adapter;
- richer C++17 report, trace, and benchmark commands;
- continued sanitizer, ownership, ABI-layout, and authority-boundary testing.

No CUDA adapter becomes geometry authority, and CUDA schedule validation remains
separate from full-path or tissue execution.

## 7. Fuzzing expansion

**Status: Queued**

- shard bundle range, order, fingerprint, and local-prefix mutation fuzzing;
- tissue configuration and audit-chain fuzz targets;
- C ABI ownership, length, layout, and malformed-input fuzzing;
- WASM pointer/length and structured-error boundary fuzzing;
- differential Python/Rust tissue fuzzing over bounded configurations;
- reduction of every discovered failure into a deterministic regression case;
- scheduled or continuous fuzzing that never executes untrusted public-PR code
  on privileged hardware.

## 8. Documentation and examples

**Status: Queued**

- guided examples for Python geometry, Rust geometry, tissue, numerical paths,
  WASM laboratories, C++ FFI, CUDA evidence, and shard reconstruction;
- crate-level API documentation and examples that compile in CI;
- tutorials explaining receipts, runtime identity, residual sidecars, shard
  fingerprints, and the difference between a correctness surface and an oracle;
- research notebooks or static derivations that do not become runtime
  dependencies.

## 9. Dependency and toolchain maintenance

**Status: Continuous**

- evaluate new Rust editions before migration and record the minimum supported
  compiler;
- keep Python coverage current without weakening the reference-runtime policy;
- test supported CUDA toolkits and GPU architectures through explicit profiles;
- track WebGPU and core WASM changes through browser-source validation;
- update dependencies only with locked builds and full conformance replay.

## 10. Additional geometry and tissue models

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

## 11. Performance optimization

**Status: Queued, with measurements required**

- profile `rsh-core`, `rsh-numerics`, `rsh-parallel`, and `rsh-tissue` before
  optimization;
- evaluate portable SIMD for schedule, frame, shard-prefix, and metric
  calculations;
- reduce WASM size and parse/allocation overhead;
- add benchmark baselines and regression thresholds only after stable runner
  methodology is established;
- distinguish kernel time, transfer time, serialization time, and end-to-end
  latency.

Optimization must preserve contract output within its declared tolerance.

## 12. CI/CD and hardware automation

**Status: Queued**

- maintain trusted self-hosted GPU runners for manual or protected-branch CUDA
  and WebGPU validation;
- add automated browser execution through a controlled hardware environment;
- upload conformance and performance sidecars as immutable workflow artifacts;
- detect performance regressions only on pinned hardware and toolchains;
- never expose privileged hardware runners to arbitrary public pull-request code.

## 13. Cross-language contract testing

**Status: Continuous expansion**

- add more sealed configurations rather than relying on one golden case;
- add property-based invariants for bounds, centering, frame orthonormality,
  deterministic replay, shard coverage, and audit-chain completeness;
- compare Python, native Rust, WASM, C++/FFI, WGSL, CUDA, and future NPU outputs
  only where they implement the same named contract;
- record receipt identity separately from numerical observable conformance;
- strengthen profiles with negative cases and malformed-evidence rejection.

## Recommended order

The current priority sequence is:

1. fuzz and harden the accepted shard-prefix evidence boundary;
2. build a trusted self-hosted RTX workflow for protected hardware validation;
3. implement a separately versioned multi-device CUDA path experiment using the
   accepted local shard contract;
4. expand full-path browser inspection and residual-debugging tools;
5. proceed to hardware-backed NPU work;
6. continue documentation, toolchain maintenance, performance profiling, and
   cross-language matrix expansion throughout.
