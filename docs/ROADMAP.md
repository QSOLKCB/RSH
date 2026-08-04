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

The native implementation agrees with the Python golden entry and exit
coordinates inside the declared `1e-12` tolerance. Its runtime receipt may
differ because the full report includes transcendental values whose final
floating-point details are runtime-sensitive. That distinction is recorded
rather than concealed.

## Phase 3 — WASM bridge

Status: **implemented in v2.2.0**

- `rsh-wasm` compiles the verified Rust core to `wasm32-unknown-unknown`;
- a dependency-free raw ABI accepts numeric configuration inputs and exposes a
  UTF-8 JSON output buffer through WebAssembly linear memory;
- browser calculations remain inside `rsh-core`; JavaScript handles interface,
  projection, animation, downloads, and service-worker caching only;
- the Pages laboratory reports pass/fail, bounds, frame error, centre error,
  path length, and the runtime receipt;
- JSON reports and CSV traces can be downloaded directly from the browser;
- host ABI tests and a release-target WASM build run in CI;
- Pages builds the module itself and refuses deployment when source or binary
  validation fails;
- the site becomes available offline after its first successful load.

The bridge does not use `wasm-bindgen`, npm, Node.js, or a bundler. This keeps the
browser boundary small, auditable, and independent of a second package-runtime
stack.

## Phase 4 — WGSL compute and visual kernels

Status: **next**

- batch path evaluation and large logical-field sampling on WebGPU;
- validate selected GPU results against Python, native Rust, and WASM vectors;
- separate visual interpolation from verified model samples;
- report adapter, device, precision, and workgroup parameters in evidence;
- retain the CPU/WASM path where WebGPU is unavailable;
- never allow a GPU visual approximation to silently replace verified samples.

The first WGSL milestone should be a conformance harness, not a visual effect:
selected logical indices, curvature/torsion schedules, and projected positions
must be compared against checked-in vectors before the GPU path is treated as an
accepted backend.

## Phase 5 — optional C++/CUDA adapter

C++ is not a second canonical implementation. Add it only when required for an
existing native integration, CUDA-specific benchmark, or stable C ABI consumer.
Any such adapter must consume the same conformance vectors and publish its own
runtime and compiler provenance.

## GitHub Pages

The `web/` source is assembled by `.github/workflows/pages.yml`. The workflow
builds `rsh_wasm.wasm`, places it under `web/pkg/`, validates the complete
artifact, and only then uploads it for deployment.

The rotating display is a browser projection of samples returned by `rsh-core`.
It remains labelled as a visual projection and is not promoted to evidence.

## Governance rule

Performance does not promote an implementation to scientific authority. A later
backend is accepted only after it reproduces the reference contracts, passes the
cross-runtime suite, and states every known source of numerical divergence.
