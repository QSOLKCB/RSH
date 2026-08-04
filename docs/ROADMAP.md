# RSH implementation roadmap

RSH advances by preserving one scientific contract across progressively faster
implementations. The Python reference defines behaviour; later runtimes must
match its declared inputs, outputs, bounds, and receipt schema within documented
numerical tolerances.

## Phase 1 — Python reference

Status: **current**

- standard-library Frenet–Serret integrator;
- validated curvature and torsion schedules;
- exact discrete midpoint coordinate normalisation;
- canonical JSON payload and domain-separated SHA-256 receipt;
- CSV, JSON, and SVG evidence exports;
- independent concurrent replay parity;
- unit, CLI, export, and invalid-input tests;
- golden vectors and receipts for cross-language conformance.

Phase 1 is complete when CI passes on every declared Python runtime and a stable
golden-vector bundle is committed.

## Phase 2 — Rust core and CLI

- implement the same model and report schema in a small `rsh-core` crate;
- expose a native `rsh-cli` binary;
- compare Rust output with Python golden vectors;
- document floating-point tolerances explicitly;
- keep receipt compatibility only where byte-identical canonical values are
  genuinely guaranteed; otherwise use a versioned cross-runtime conformance
  record rather than pretending distinct floating-point paths are identical.

## Phase 3 — WASM bridge

- compile the Rust core to WebAssembly;
- provide an offline browser interface without a required server;
- keep all scientific calculations in the verified core;
- treat JavaScript as interface and file-export glue, not a second model.

## Phase 4 — WGSL compute and visual kernels

- batch path evaluation and large logical-field sampling on WebGPU;
- validate selected GPU results against Python and Rust vectors;
- separate visual interpolation from verified model samples;
- report adapter, device, precision, and workgroup parameters in evidence.

## Phase 5 — optional C++/CUDA adapter

C++ is not a second canonical implementation. Add it only when required for an
existing native integration, CUDA-specific benchmark, or stable C ABI consumer.
Any such adapter must consume the same conformance vectors and publish its own
runtime and compiler provenance.

## Governance rule

Performance does not promote an implementation to scientific authority. A later
backend is accepted only after it reproduces the reference contracts, passes the
cross-runtime suite, and states every known source of numerical divergence.
