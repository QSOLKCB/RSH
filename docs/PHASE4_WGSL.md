# Phase 4 — WGSL compute and residual conformance

## Goal

Evaluate the RSH curvature and torsion schedules across a large one-dimensional
grid with WebGPU while preserving the CPU/WASM contract as the authority.
Phase 4 accelerates batch field evaluation and display. It does not move the
geometry receipt, centre normalisation, Frenet–Serret integration, or scientific
oracle onto the GPU.

## Architecture

```text
Python oracle ───────► conformance/python_v2_129.json
      │
      ▼
rsh-core f64 ────────► native Rust / verified geometry report
      │
      ├──────────────► rsh-wasm rsh_run()      geometry + receipt
      │
      └──────────────► rsh-wasm rsh_schedule() f64 κ/τ grid
                                             │
                                             ▼
                                 WGSL f32 schedule kernel
                                             │
                                             ▼
                              full-grid residual comparison
                                 PASS ───────► sidecar
                                 FAIL ───────► display only
```

JavaScript does not contain a second curvature or torsion model. The additive
`rsh_schedule` ABI calls the public schedule functions in `rsh-core` and returns
an f64 grid for residual comparison. The browser passes the same parameters and
constants to WGSL, reads the f32 storage buffer back, and compares every sample.

## Kernel

`web/wgsl/kappa_tau_field.wgsl` evaluates one point per invocation:

```text
workgroup size = 64
output[index]  = vec2<f32>(kappa(s), tau(s))
grid size      = 4096
```

The parameter buffer carries the sample count, interval, schedule controls,
`psi`, and the curvature bound. Constants that belong to the model are supplied
by the WASM oracle instead of being maintained as unrelated JavaScript values.

## Residual gate

The published browser gate is:

```text
max(max |kappa_gpu - kappa_wasm|,
    max |tau_gpu   - tau_wasm|) <= 1e-4
```

A passing run may export `RSH-WEBGPU-RESIDUAL-SIDECAR-V1`. The sidecar records:

- adapter and logical-device description;
- WGSL entry point and workgroup size;
- f32 precision and 4096-sample grid;
- maximum curvature, torsion, and combined residuals;
- the published threshold and gate result;
- `visual_verified: false`;
- an explicit statement that the sidecar does not replace the CPU/WASM receipt.

A failing residual disables any accepted-backend wording and marks the field as
`DISPLAY ONLY`. The visual chart is always display-only, even when the residual
gate passes.

## Fallback

When `navigator.gpu` is absent, an adapter is denied, shader compilation fails,
or the device is lost, the browser reports `CPU/WASM FALLBACK`. Geometry,
verification, receipts, JSON reports, and CSV traces continue to work through
the verified Rust/WASM path.

WebGPU failure is therefore an acceleration failure, not an evidence failure.

## CI boundary

GitHub-hosted CI cannot represent every browser adapter and driver. CI therefore:

1. builds and executes the real `rsh_wasm.wasm` module;
2. requires the additive `rsh_schedule` export;
3. evaluates the 4096-point f64 schedule oracle;
4. checks the WGSL source contract and workgroup declaration;
5. runs an explicitly labelled f32 arithmetic reference against the f64 grid;
6. fails when that reference exceeds `conformance/wgsl_v1_4096.json`.

The actual WGSL kernel runs in the user's browser on the selected adapter. Its
observed adapter-specific residual is displayed and exportable. CI never labels
the arithmetic reference as an actual GPU execution.

## Acceptance

- [x] 4096-point κ/τ field kernel with workgroup size 64.
- [x] f64 schedule oracle supplied by `rsh-core` through WASM.
- [x] full-grid f32 residual calculation in the browser.
- [x] adapter, device, precision, grid, workgroup, and residual metadata.
- [x] downloadable residual sidecar that cannot replace the geometry receipt.
- [x] mandatory CPU/WASM fallback when WebGPU is unavailable or rejected.
- [x] visual field explicitly tagged `data-verified="false"`.
- [x] static Pages deployment with shader and GPU module cached for offline use.

## Deferred work

A full Frenet–Serret path integrator in WGSL remains intentionally deferred. It
would require a separately declared numerical scheme, re-orthonormalisation
policy, path-level golden vectors, and substantially stronger adapter-specific
conformance evidence. Phase 4 does not quietly smuggle that complexity into a
pretty tube renderer.
