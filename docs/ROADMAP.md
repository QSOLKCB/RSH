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

## Phase 5 — optional C++/CUDA adapter

Status: **optional on demand**

C++ is not a second canonical implementation. Add it only when required for an
existing native integration, CUDA-specific benchmark, or stable C ABI consumer.
Any such adapter must consume the same conformance vectors and publish its own
runtime and compiler provenance.

A full WGSL or CUDA Frenet–Serret integrator would require a separately versioned
numerical contract, path-level golden vectors, frame-error limits, and explicit
adapter/compiler residual evidence. It is not assumed by the schedule-field work.

## GitHub Pages

The `web/` source is assembled by `.github/workflows/pages.yml`. The workflow
builds `rsh_wasm.wasm`, executes the WASM/WGSL source conformance harness, places
the module under `web/pkg/`, validates the shader and browser assets, and only
then uploads the artifact for deployment.

## Governance rule

Performance does not promote an implementation to scientific authority. A later
backend is accepted only after it reproduces the reference contracts, passes the
cross-runtime suite, and states every known source of numerical divergence.
