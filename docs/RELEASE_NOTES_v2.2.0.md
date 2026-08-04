# RSH v2.2.0 — Verified WebAssembly Browser Laboratory

RSH v2.2.0 completes the third implementation phase by exposing the native Rust
geometry core to the browser through a compact raw WebAssembly ABI.

## Highlights

- adds `crates/rsh-wasm`, compiled for `wasm32-unknown-unknown`;
- keeps all scientific calculations inside `rsh-core`;
- replaces the previous schematic-only page with an interactive verified runner;
- displays report status, sample count, centre error, curvature bound, torsion
  range, frame error, path length, and runtime receipt;
- exports the complete browser payload as JSON and verified sample traces as CSV;
- caches the application and WASM module for offline use after first load;
- requires no npm, Node.js, bundler, `wasm-bindgen`, CDN, or server process;
- builds and validates the WebAssembly binary in CI and during Pages deployment.

## Browser ABI

The browser passes numeric inputs directly to the module:

```text
rsh_abi_version() -> u32
rsh_run(samples, s0, s1, kappa_fraction, tau_floor, tau_amplitude) -> i32
rsh_output_ptr() -> pointer
rsh_output_len() -> length
```

The output buffer contains UTF-8 JSON supplied by the Rust core. JavaScript is
limited to interface control, canvas projection, animation, downloads, and
offline caching. There is no duplicate JavaScript geometry model.

## Scientific boundary

The rotating canvas is a visual projection of verified Rust/WASM samples. It is
not itself evidence and does not imply a physical interpretation.

The Python implementation remains the scientific oracle. Native Rust remains a
conforming implementation. WASM is an execution bridge over that same Rust core,
not a third independent mathematical implementation.

## Validation

The release pipeline checks:

- Python reference tests on Python 3.10, 3.12, and 3.14;
- Rust formatting and Clippy with warnings denied;
- native Rust unit and conformance tests;
- host-side tests of the raw WASM ABI and structured error output;
- a release build for `wasm32-unknown-unknown`;
- the WebAssembly magic header and non-empty binary;
- browser source, service-worker, module-path, and Pages artifact integrity;
- the existing provenance boundary gate.

## Next phase

RSH v2.3 will begin the WGSL/WebGPU conformance phase. The first GPU milestone is
shared-vector verification and exact logical sampling—not visual spectacle.
