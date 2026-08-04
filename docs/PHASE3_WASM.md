# Phase 3 — verified WebAssembly bridge

## Goal

Run the existing `rsh-core` geometry and verification contract inside a browser.
Python remains the readable scientific oracle. Native Rust and WebAssembly are
accepted through the same declared observables, bounds, and conformance vectors.
JavaScript is limited to interface state, file export, canvas projection, and
offline caching.

## Scientific boundary

- WebAssembly must reproduce the checked-in Python golden coordinates within the
  declared tolerance.
- Curvature, torsion, centre normalisation, frame verification, and receipts are
  produced by `rsh-core`, not by JavaScript.
- For the sealed 129-sample Phase 3 profile, the WebAssembly receipt must equal
  the native Rust receipt for the same canonical report.
- Python receipt identity remains reported separately because Python and Rust
  follow distinct runtime paths.
- Canvas projection is interface output. It is not an additional verified sample
  set and does not establish a physical interpretation.
- The project makes computational and implementation claims only.

## Architecture

```text
Python oracle ───────► conformance/python_v2_129.json
      │
      ▼
rsh-core ────────────► native Rust CLI
      │
      └──────────────► rsh-wasm raw ABI
                            │
                            ▼
                    browser laboratory
                    JS interface + Canvas
```

The uploaded implementation pack proposed `wasm-bindgen`. Upstream RSH uses a
smaller raw WebAssembly ABI instead. This removes generated JavaScript glue,
`wasm-pack`, npm, and bundling from the deployed laboratory while preserving the
same scientific contract. It is an implementation substitution, not a model
change.

## Raw ABI

```text
rsh_abi_version() -> u32
rsh_run(samples, s0, s1, kappa_fraction, tau_floor, tau_amplitude) -> i32
rsh_output_ptr() -> pointer
rsh_output_len() -> length
```

`rsh_run` writes a UTF-8 JSON payload into WebAssembly linear memory.

Return codes:

- `0`: a report was produced and every verification contract passed;
- `1`: a report was produced with at least one failed contract;
- `2`: configuration, integration, or serialization failed.

The JSON payload includes:

- model and ABI versions;
- the complete `rsh-core` verification report;
- verified centreline samples containing `p`, `x`, `y`, `z`, `kappa`, and `tau`;
- an explicit evidence-boundary note.

## Browser laboratory

The static Pages laboratory provides:

- odd sample-count selection;
- curvature-fraction and torsion-schedule controls;
- live verification metrics and pass/fail state;
- full runtime receipt display;
- JSON report export;
- CSV trace export;
- rotation and projection of the exact samples returned by WebAssembly;
- service-worker caching after the first successful load.

No server process is required. The Pages workflow builds the `.wasm` file,
assembles the static artifact, executes the conformance probe, validates the
binary header and required assets, and only then permits deployment.

## Conformance

`conformance/wasm_v2_129.json` defines the Phase 3 acceptance profile. CI runs
the compiled WebAssembly module under Node's built-in WebAssembly runtime with
no npm packages. The probe verifies:

- ABI version `1`;
- 129 returned samples;
- `pass_all = true`;
- exact discrete midpoint placement within `1e-15`;
- entry and exit coordinates within the Python `1e-12` tolerance;
- finite bounded schedule and report values;
- the sealed WebAssembly receipt;
- exact receipt identity with the native Rust report generated in the same job.

The current sealed result is:

```text
entry max abs error = 1.1102230246251565e-16
exit max abs error  = 8.881784197001252e-16
centre error        = 0
WASM/native receipt = 9cccdea9db0e0cb4c30accab275a672efb9c69fed022f5087f273a87aa28f253
```

## Acceptance

- [x] The browser executes `rsh-core` through WebAssembly.
- [x] The midpoint sample is at the coordinate origin within tolerance.
- [x] The actual `.wasm` binary is executed in CI against the Python golden data.
- [x] The sealed WebAssembly receipt equals the native Rust receipt.
- [x] JavaScript contains no second curvature, torsion, or integration model.
- [x] The laboratory works as static GitHub Pages content and caches for offline
      reuse after first load.
- [x] Visual projection is clearly separated from evidence claims.
