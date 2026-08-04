# RSH v2.3.0 — Residual-Gated WebGPU Schedule Field

RSH v2.3.0 completes the required Phase 4 milestone: a WGSL/WebGPU schedule
kernel checked point-by-point against an f64 oracle supplied by the existing
Rust core through WebAssembly.

## Highlights

- adds `web/wgsl/kappa_tau_field.wgsl`, a 64-thread compute kernel for κ/τ fields;
- adds the `rsh_schedule` raw ABI export without breaking the Phase 3 ABI;
- evaluates a 4096-point f64 schedule inside `rsh-core` for GPU comparison;
- runs the WGSL field on the browser's selected WebGPU adapter;
- reads the f32 buffer back and calculates full-grid curvature and torsion residuals;
- publishes a `1e-4` residual gate and refuses accepted-backend wording above it;
- records adapter, logical device, precision, workgroup, grid, and residual metadata;
- exports a residual sidecar that is explicitly separate from the geometry receipt;
- keeps the verified CPU/WASM path active when WebGPU is missing, rejected, or lost;
- adds a display-only κ/τ field chart clearly separated from the verified path visual;
- caches the shader and WebGPU modules for offline reuse after the first load.

## Authority boundary

Python remains the readable scientific oracle. Native Rust and WASM remain the
verified geometry implementations. WebGPU is an accelerated f32 schedule field
with residual evidence only.

A passing GPU sidecar does not create a new geometry receipt. A failing sidecar
does not invalidate the CPU/WASM report; it restricts the GPU result to display
only. The chart carries `data-verified="false"` regardless of the gate result.

## Additive WASM ABI

```text
rsh_schedule(samples, s0, s1, kappa_fraction, tau_floor, tau_amplitude) -> i32
```

The function accepts even grid sizes, validates the schedule controls through
`rsh-core`, and writes `RSH-SCHEDULE-RUN-V1` JSON into the existing output buffer.
This avoids a duplicate JavaScript equation set.

## Conformance

`conformance/wgsl_v1_4096.json` seals:

- 4096 samples over `s = [0, 4]`;
- workgroup size 64;
- f32 field precision;
- maximum residual threshold `1e-4`;
- required CPU/WASM fallback;
- no GPU receipt authority;
- display-only visual status.

CI executes the compiled WASM module, checks the schedule export, validates the
shader source contract, and runs an explicitly labelled f32 arithmetic reference
against the f64 oracle. Actual adapter-specific WGSL execution occurs in the
browser and produces the downloadable sidecar.

## Next phase

C++/CUDA remains optional and interoperability-driven. A GPU Frenet–Serret path
integrator is not implied by this release and would require its own numerical
contract and conformance package.
