# RSH implementation roadmap

RSH advances by preserving one scientific contract across progressively faster
implementations. The Python reference defines behaviour; later runtimes must
match its declared inputs, outputs, bounds, and evidence schema within documented
numerical tolerances.

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

Status: **implemented in v2.4.0**

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

The C++ and CUDA layers are adapters. Geometry, frame integration, centre
normalisation, reports, and receipts remain authoritative in `rsh-core`.

## Phase 6 — separately versioned GPU path integration research

Status: **not scheduled**

A full WGSL or CUDA Frenet–Serret integrator is not an automatic continuation of
the schedule kernels. Before implementation, it requires:

- a separately named and versioned numerical integration contract;
- an explicit midpoint/frame update and re-orthonormalisation policy;
- path-level golden vectors at multiple sample counts;
- coordinate, tangent, normal, binormal, centre, and frame-error thresholds;
- compiler flags, shader/compiler versions, adapter, driver, and precision
  provenance;
- clear separation between reproducible evidence and display interpolation;
- a fallback that never suppresses the accepted Rust/WASM path.

That work should begin with a conformance document and vectors, not a renderer.

## GitHub Pages

The `web/` source is assembled by `.github/workflows/pages.yml`. The workflow
builds `rsh_wasm.wasm`, executes the WASM/WGSL source conformance harness, places
the module under `web/pkg/`, validates the shader and browser assets, and only
then uploads the artifact for deployment.

Native C++, FFI, and CUDA artifacts are intentionally not shipped through Pages.
They are built and tested through the repository's native CI path.

## Governance rule

Performance does not promote an implementation to scientific authority. A later
backend is accepted only after it reproduces the reference contracts, passes the
cross-runtime suite, and states every known source of numerical divergence.
