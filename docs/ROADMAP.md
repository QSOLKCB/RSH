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

The native implementation currently agrees with the Python golden entry and
exit coordinates to below `5e-16`, against a declared `1e-12` tolerance. Its
runtime receipt differs because the full report includes transcendental values
whose final floating-point details are runtime-sensitive. That distinction is
recorded rather than concealed.

## Phase 3 — WASM bridge

Status: **next**

- compile `rsh-core` to WebAssembly;
- provide an offline browser interface without a required server;
- keep scientific calculations in the verified Rust core;
- treat JavaScript as interface, animation, and file-export glue;
- compare WASM output against the same Python conformance record;
- publish the browser laboratory through the existing Pages workflow.

## Phase 4 — WGSL compute and visual kernels

- batch path evaluation and large logical-field sampling on WebGPU;
- validate selected GPU results against Python, native Rust, and WASM vectors;
- separate visual interpolation from verified model samples;
- report adapter, device, precision, and workgroup parameters in evidence;
- retain a CPU/WASM fallback where WebGPU is unavailable.

## Phase 5 — optional C++/CUDA adapter

C++ is not a second canonical implementation. Add it only when required for an
existing native integration, CUDA-specific benchmark, or stable C ABI consumer.
Any such adapter must consume the same conformance vectors and publish its own
runtime and compiler provenance.

## GitHub Pages

The `web/` directory is deployed by `.github/workflows/pages.yml`. The current
site is a project and implementation-status surface. Its animated projection is
labelled schematic and is not evidence. Phase 3 will replace the status-only
interaction with calculations supplied by the verified WASM core.

## Governance rule

Performance does not promote an implementation to scientific authority. A later
backend is accepted only after it reproduces the reference contracts, passes the
cross-runtime suite, and states every known source of numerical divergence.
