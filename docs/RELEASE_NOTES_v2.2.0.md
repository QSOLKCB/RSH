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
- requires no npm, bundler, `wasm-bindgen`, `wasm-pack`, CDN, or server process;
- adds a sealed `conformance/wasm_v2_129.json` acceptance profile;
- executes the actual compiled WebAssembly module against Python golden
  coordinates in CI and before Pages deployment;
- enforces exact receipt identity between the sealed WebAssembly module and the
  native Rust report for the same canonical configuration;
- documents the complete Phase 3 architecture and scientific boundary in
  `docs/PHASE3_WASM.md`.

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

The supplied Phase 3 pack proposed generated `wasm-bindgen` bindings. Upstream
RSH uses a raw ABI instead, avoiding generated glue and build-time package
machinery while retaining the same core model and acceptance contract.

## Scientific boundary

The rotating canvas is a visual projection of verified Rust/WASM samples. It is
not itself evidence and does not imply a physical interpretation.

The Python implementation remains the scientific oracle. Native Rust remains a
conforming implementation. WASM is an execution bridge over that same Rust core,
not a third independent mathematical implementation.

Receipt encoding and domain separation remain supplied by `rsh-core`. The
sealed 129-sample WebAssembly profile must reproduce the native Rust receipt
exactly. Python receipt identity remains reported separately because Python and
Rust follow different runtime paths.

## Validation

The release pipeline checks:

- Python reference tests on Python 3.10, 3.12, and 3.14;
- Rust formatting and Clippy with warnings denied;
- native Rust unit and conformance tests;
- host-side tests of the raw WASM ABI and structured error output;
- a release build for `wasm32-unknown-unknown`;
- execution of the actual `.wasm` file under Node's built-in WebAssembly runtime;
- ABI version, sample count, midpoint tolerance, entry and exit residuals,
  finite output, report status, sealed receipt, and native receipt identity;
- browser source, service-worker, module-path, and Pages artifact integrity;
- the existing provenance boundary gate.

The sealed run produced:

```text
entry max abs error = 1.1102230246251565e-16
exit max abs error  = 8.881784197001252e-16
centre error        = 0
WASM/native receipt = 9cccdea9db0e0cb4c30accab275a672efb9c69fed022f5087f273a87aa28f253
```

Node is used only as a zero-package CI execution harness. It is not required by
the deployed laboratory or its users.

## Next phase

RSH v2.3 will begin the WGSL/WebGPU conformance phase. The first GPU milestone is
shared-vector verification and exact logical sampling—not visual spectacle.
