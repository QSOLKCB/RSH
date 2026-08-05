# RSH implementation roadmap

RSH advances by preserving explicit contracts across progressively faster or
more compositional implementations. The Python reference defines behaviour;
later runtimes must match declared inputs, outputs, bounds, and evidence schemas
within documented numerical tolerances.

## Phase 1 — Python reference

Status: **complete**

- standard-library Frenet–Serret integrator;
- validated curvature and torsion schedules;
- exact discrete midpoint coordinate normalisation;
- canonical JSON payload and domain-separated SHA-256 receipt;
- CSV, JSON, and SVG evidence exports;
- independent concurrent replay parity;
- unit, CLI, export, and invalid-input tests;
- golden coordinates and receipt for cross-runtime conformance.

## Phase 2 — Rust core and CLI

Status: **implemented in v2.1.0**

- `rsh-core` reproduces the geometry and verification contract natively;
- `rsh-cli` provides `info`, `verify`, `trace`, `conformance`, and `sample`;
- Rust output is checked against the 129-sample Python golden coordinates;
- dependencies are locked through `Cargo.lock`;
- formatting, Clippy, tests, and native evidence commands run in CI;
- receipt identity is reported separately from coordinate conformance.

## Phase 3 — WASM bridge

Status: **implemented in v2.2.0**

- `rsh-wasm` compiles the verified Rust core to `wasm32-unknown-unknown`;
- the raw ABI supplies verified geometry reports and sample coordinates;
- the actual compiled module is executed against a sealed 129-point profile;
- the browser contains no second geometry integrator;
- Pages builds, validates, and deploys the WASM artifact;
- the laboratory remains available offline after its first successful load.

## Phase 4 — WGSL compute and residual conformance

Status: **implemented in v2.3.0**

- `rsh_schedule` supplies even-sized f64 κ/τ grids from `rsh-core` through WASM;
- `kappa_tau_field.wgsl` evaluates the same controls on a 4096-point f32 grid;
- every GPU point is read back and compared with the CPU/WASM oracle;
- adapter, device, precision, workgroup, grid, and residual metadata are reported;
- a `1e-4` maximum residual gate controls sidecar acceptance;
- the GPU visual remains explicitly display-only;
- WebGPU absence, compilation failure, or device loss activates CPU/WASM fallback;
- shader, GPU module, and WASM runtime remain static Pages assets with offline caching.

The GPU remains an accelerated field evaluator, not a scientific oracle. No GPU
result replaces the geometry report or its domain-separated receipt.

## Phase 5 — native C ABI, C++17 consumer, and optional CUDA schedule adapter

Status: **implemented in v2.4.0; validation hardened in v2.4.1**

- `rsh-ffi` exports a versioned C ABI over `rsh-core`;
- fixed-layout configuration, summary, byte-buffer, and schedule structures are
  published in `include/rsh_ffi.h`;
- runtime size probes and C++ `static_assert`s guard ABI layout drift;
- Rust panics are contained and converted into an explicit status code;
- thread-local UTF-8 errors describe rejected calls;
- Rust-owned JSON and schedule buffers cross the boundary only through opaque
  handles with matching release functions;
- a dependency-free C++17 CLI consumes the ABI without reproducing geometry;
- CMake builds the Rust library before linking the native adapter;
- a 4096-point CPU f32 arithmetic reference validates the optional CUDA formula
  against the f64 Rust FFI schedule in ordinary CI;
- `rsh-cuda` may be built on CUDA-capable systems and records actual adapter,
  compute capability, kernel block size, and readback residuals;
- actual CUDA execution is never inferred from the portable arithmetic reference.

### v2.4.1 hardware-validation hardening

- CUDA architecture selection is configurable and recorded;
- the CUDA executable accepts explicit grid, block, threshold, device, and repeat
  controls while retaining the sealed defaults;
- sidecars include device UUID, CUDA API/compile versions, grid blocks, compiled
  architectures, and host pointer width;
- a `1e-6` diagnostic band supplements but does not replace the `1e-4` hard gate;
- a non-mutating preflight script reports host readiness;
- a Python harness validates strict JSON, repeated device execution, CPU-reference
  comparison, and optional Compute Sanitizer memcheck/racecheck;
- deterministic evidence packaging avoids recursive manifest hashes;
- a dispatch-only workflow targets trusted labelled self-hosted GPU runners;
- an independent RTX 5060 Ti / sm_120 result is preserved as a noncanonical
  hardware observation tied to its exact commit and toolchain.

The C++ and CUDA layers are adapters. Geometry, frame integration, centre
normalisation, reports, and receipts remain authoritative in `rsh-core`.

## Phase 6 — constitutional geometric tissue

Status: **Python reference implemented in v2.5.0**

- a machine-checkable constitution seals geometry invariants, oracle authority,
  objective ordering, human-ack requirements, and refusal rules;
- deterministic geometric cells are seeded from a verified 129-sample Python
  geometry report rather than a second path model;
- ring and chord edges define a bounded tissue graph;
- each tick performs bound projection, phase coupling, binding diffusion,
  neighbour prediction, shared-centroid normalization, and functional metric
  calculation;
- every tick extends a domain-separated receipt chain beginning with the seed
  geometry receipt;
- Q_f combines phase coherence, binding cohesion, prediction, edge continuity,
  role coverage, and dissociation pressure;
- Q_f is explicitly functional and does not claim consciousness, life, sentience,
  subjective awareness, or qualia;
- WebGPU, CUDA, and NPU values may be recorded only as residual sidecars, with
  f64 fallback on gate failure;
- a dry-run refinement evaluator creates intent tokens, validates bounds, detects
  contract escalation, requires explicit human acknowledgement, compares ordered
  objectives, and seals `KEEP_CANDIDATE` or `REVERT` recommendations;
- the evaluator does not edit source or commit configuration autonomously;
- `conformance/tissue_v1_8x20.json` fixes the default 8-cell, 20-tick receipt and
  functional metrics;
- `conformance/npu_tier2_v1.json` defines initial INT8/BF16/FP16 NPU evidence
  gates without claiming a vendor driver implementation.

The tissue layer composes accepted geometry evidence. Its shared-centroid law and
receipt domains are separate from the geometry midpoint law and geometry receipt.

## Phase 7 — Rust/WASM tissue conformance

Status: **implemented in v2.7.0**

- `rsh-tissue` ports the sealed Python tissue algorithm into a shared Rust crate;
- the port reproduces cell seeding, edge ordering, bound projection, phase
  coupling, binding diffusion, neighbour prediction, centroid normalization,
  Q_f metrics, sidecar fallback, and the complete audit chain;
- `rsh-tissue-cli` emits native reports, CSV traces, and a Python-observable
  conformance result;
- `rsh-tissue-wasm` exposes a raw browser ABI over the shared Rust crate rather
  than implementing another simulation;
- the Rust implementation reconstructs and verifies the canonical constitution
  hash;
- `scripts/test_tissue_wasm.mjs` executes fresh Python, native Rust, and compiled
  WASM reports and compares all portable tick and final-cell observables;
- the sealed cross-runtime tolerance is `1e-12`;
- receipts remain runtime-specific identities and are not required to match
  across Python, native Rust, and WASM;
- same-runtime deterministic replay and audit-chain integrity remain mandatory;
- the offline browser laboratory executes the Rust tissue runtime directly in
  WASM and exports its bounded evidence report.

See [Phase 9 tissue conformance](PHASE9_TISSUE_CONFORMANCE.md).

## Phase 8 — separately versioned full-path Frenet numerical research

Status: **research implementation in v2.6.0**

- `RSH-FRENET-NUMERICS-V1` names a new numerical contract without modifying the
  canonical geometry contract;
- `rsh-numerics` implements f64 midpoint SO(3) frame transport, midpoint tangent
  position quadrature, per-step modified Gram–Schmidt projection, and exact-grid
  midpoint centering;
- `rsh-numerics-cli` supplies JSON/CSV output and observational benchmarking with
  no timing acceptance gate;
- `rsh-numerics-wasm` exposes a separate browser ABI over the numerical path;
- `frenet_path_v1_1025.json` seals path, centre-frame, and accelerator vectors;
- a deterministic bounded configuration corpus runs in ordinary workspace tests;
- a scheduled/manual `cargo-fuzz` target mutates valid path configurations;
- `frenet_path.wgsl` evaluates κ, τ, position, T, N, B, frame projection, and
  midpoint centering on the adapter;
- every f32 path component is read back and compared with the f64 Rust/WASM path;
- position, frame, schedule, norm, and orthogonality gates control sidecar export;
- WebGPU failure preserves the f64 research path, and neither research backend
  replaces the canonical `rsh-core` report or receipt.

The first WGSL path kernel uses a single invocation because the state recurrence
is sequential. It establishes actual full-path adapter execution and conformance,
not a parallel speedup. Future segmented scans or interval-transfer composition
must be introduced under another explicit numerical policy and evidence profile.

See [Phase 8 numerical research](PHASE8_FRENET_NUMERICS.md).

## GitHub Pages

The `web/` source is assembled by `.github/workflows/pages.yml`. The workflow
builds the canonical geometry, numerical path, and tissue WASM modules; executes
all three conformance harnesses; places the modules under `web/pkg/`; validates
the shaders and browser assets; and only then uploads the artifact for deployment.

Native C++, FFI, and CUDA are intentionally not executed by Pages. Native
adapters are built through CI, CUDA hardware validation uses the manual
trusted-runner workflow, and the tissue page executes only the bounded shared
Rust/WASM runtime.

## Governance rule

Performance, compositional complexity, or anthropomorphic terminology does not
promote an implementation to scientific authority. A later backend is accepted
only after it reproduces the applicable reference contracts, passes the
cross-runtime suite, and states every known source of numerical divergence.
