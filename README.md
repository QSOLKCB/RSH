# RSH — Robitaille–Slade Helix

**Bounded Frenet–Serret geometry, deterministic evidence, and cross-runtime conformance.**

RSH constructs a three-dimensional path by prescribing curvature and torsion
inside explicit Robitaille bounds, integrating the Frenet–Serret frame, and
translating the exact discrete midpoint to the coordinate origin.

**Authors:** J. Robitaille (DeltaKingZero) and Trent Slade / QSOL-IMC  
**Release:** 2.3.0  
**Model contract:** 2.0.0  
**Implementations:** Python reference + native Rust core/CLI + Rust/WebAssembly bridge + residual-gated WGSL/WebGPU field

## Browser laboratory

The project site runs the verified Rust core directly in WebAssembly and adds an
optional WebGPU acceleration layer:

**https://qsolkcb.github.io/RSH/**

The laboratory can change the sample count, curvature fraction, torsion floor,
and torsion amplitude; run the geometry contract; inspect the resulting report;
and download JSON and CSV evidence. A second panel evaluates a 4096-point f32
κ/τ field with WGSL, reads the GPU buffer back, and compares every point against
an f64 schedule supplied by `rsh-core` through WASM.

The rotating path is a projection of verified WASM samples. The WebGPU field
chart is display-only. Neither visual creates a physical interpretation.

After the first successful load, a service worker caches the page, WASM module,
WGSL shader, and browser modules for offline reuse.

## Implementation authority

The Python implementation remains the readable scientific oracle. It defines
the equations, validation rules, canonical report schema, golden coordinates,
and reference receipt.

The Rust implementation reproduces the same geometry and verification contract
as a native core and command-line runner. It is accepted through the checked-in
cross-runtime conformance record.

The WASM bridge calls `rsh-core`; it is not a third geometry implementation. Its
raw ABI is additive:

```text
rsh_abi_version() -> u32
rsh_run(samples, s0, s1, kappa_fraction, tau_floor, tau_amplitude) -> i32
rsh_schedule(samples, s0, s1, kappa_fraction, tau_floor, tau_amplitude) -> i32
rsh_output_ptr() -> pointer
rsh_output_len() -> length
```

`rsh_run` produces the verified geometry report and centreline samples.
`rsh_schedule` produces an f64 κ/τ grid for WebGPU residual comparison and
accepts even grid sizes such as 4096. JavaScript does not reproduce the model
equations.

WebGPU is not promoted to oracle. It may export a residual sidecar only after its
f32 field has been compared point-by-point with the WASM f64 grid. The geometry
receipt remains a CPU/WASM artifact.

## Invariants

| Quantity | Contract |
|---|---|
| \(\psi\) | \(\sqrt{2+\sqrt{5}}\) |
| Curvature | \(0 \le \kappa(s) \le \sqrt{2}-1\) |
| Torsion | \(0 < \tau(s) < 1\) |
| Centre | exact discrete \(p=0.5\) sample translated to `(0, 0, 0)` |
| Frame | tangent, normal, and binormal remain orthonormal within tolerance |
| Python evidence | canonical domain-separated SHA-256 receipt |
| Rust acceptance | contract checks plus golden-coordinate conformance |
| WASM acceptance | actual compiled module executed against `wasm_v2_129.json` |
| WGSL acceptance | 4096-point f32 field residual ≤ `1e-4` against WASM f64 schedule |
| GPU authority | residual sidecar only; never replaces the geometry receipt |
| Fallback | CPU/WASM remains fully functional without WebGPU |

Bounds hold by construction and are verified again after integration.

## Python reference

Run directly from a checkout with no third-party runtime dependencies:

```bash
python3 rsh_runner.py info
python3 rsh_runner.py verify
python3 rsh_runner.py receipt
python3 rsh_runner.py parity --workers 4
python3 rsh_runner.py trace -o rsh_trace.csv
python3 rsh_runner.py visual -o rsh_visual.svg
```

The package can also be installed locally:

```bash
python3 -m pip install -e .
rsh verify
```

## Rust native implementation

Build and test the workspace:

```bash
cargo fmt --all -- --check
cargo clippy --locked --workspace --all-targets -- -D warnings
cargo test --locked --workspace
```

Run the native CLI:

```bash
cargo run --locked -p rsh-cli -- info
cargo run --locked -p rsh-cli -- verify -n 129
cargo run --locked -p rsh-cli -- conformance
cargo run --locked -p rsh-cli -- trace -n 129 -o rsh_trace_rust.csv
cargo run --locked -p rsh-cli -- sample 16777216 12
```

## WebAssembly and WGSL conformance

Build the browser module:

```bash
rustup target add wasm32-unknown-unknown
cargo test --locked -p rsh-wasm
cargo build --locked --release --target wasm32-unknown-unknown -p rsh-wasm
mkdir -p web/pkg
cp target/wasm32-unknown-unknown/release/rsh_wasm.wasm web/pkg/
```

Run the executable WASM and WGSL-source conformance harness:

```bash
node scripts/test_wasm.mjs \
  target/wasm32-unknown-unknown/release/rsh_wasm.wasm \
  conformance/wasm_v2_129.json \
  /tmp/rsh_native_129.json \
  conformance/wgsl_v1_4096.json
```

The harness executes the actual `.wasm` file, checks the sealed geometry profile,
requires the additive schedule export, validates the WGSL source contract, and
runs an explicitly labelled f32 arithmetic reference against the f64 schedule.
Actual adapter-specific WGSL execution occurs in the browser and produces a
residual sidecar.

No `wasm-bindgen`, `wasm-pack`, npm, bundler, CDN, or runtime server is required.

## WebGPU residual policy

The browser publishes:

```text
max(max |kappa_gpu - kappa_wasm|,
    max |tau_gpu   - tau_wasm|) <= 1e-4
```

A passing field may export `RSH-WEBGPU-RESIDUAL-SIDECAR-V1` with adapter, device,
precision, workgroup, grid, and residual metadata. The chart remains tagged
`data-verified="false"`. A failing or unavailable GPU switches to CPU/WASM
fallback without affecting the geometry report.

See [the complete Phase 4 specification](docs/PHASE4_WGSL.md).

## Exact bounded logical sampling

Large logical fields can be represented without allocating the full field:

```text
logical_index(i) = floor(i × logical_count / rendered_count)
```

The Python and Rust implementations use exact integer arithmetic for this
mapping. Any future GPU logical-index kernel must reproduce the same indices.

## Repository map

```text
rsh_runner.py                    Direct Python source-checkout runner
src/rsh/                         Python geometry, verification, exports, and CLI
crates/rsh-core/                 Native Rust geometry and evidence library
crates/rsh-cli/                  Native `rsh-rust` command-line runner
crates/rsh-wasm/                 Raw WASM ABI over `rsh-core`
conformance/wasm_v2_129.json     Sealed geometry/WASM profile
conformance/wgsl_v1_4096.json    Phase 4 schedule-field profile
scripts/test_wasm.mjs            Executable WASM and f32 reference harness
web/app.js                       Verified browser geometry controller
web/gpu.js                       WebGPU execution and residual readback
web/wgsl/                        WGSL compute kernels
web/                             Static Pages laboratory and offline cache
tests/                           Python geometry, evidence, export, and CLI tests
docs/PHASE3_WASM.md              WebAssembly architecture and acceptance contract
docs/PHASE4_WGSL.md              WebGPU architecture and residual boundary
docs/SCIENTIFIC_BOUNDARY.md      Claims the evidence does and does not support
docs/ROADMAP.md                  Python → Rust → WASM → WGSL plan
```

## Scientific precision

The central sample reaches the origin because the integrated path is translated
there as an explicit coordinate convention. That check confirms implementation
correctness; it is not an empirical discovery.

Receipts prove identity of a canonical report under a declared runtime and
encoding contract. GPU residuals prove numerical agreement of a sampled f32
field within a published threshold. Neither establishes a physical theory.

## Planned sequence

1. **Python reference** — complete.
2. **Rust core and CLI** — implemented in v2.1.0.
3. **WASM bridge and browser laboratory** — implemented in v2.2.0.
4. **WGSL schedule field and residual conformance** — implemented in v2.3.0.
5. **Optional C++/CUDA adapter** — only where interoperability requires it.

A full GPU Frenet–Serret integrator is not silently implied by Phase 4. It would
require its own numerical contract, path-level vectors, and adapter-specific
frame and coordinate residual evidence.

## Licence and citation

MPL-2.0. See `NOTICE.md` for attribution and `CITATION.cff` for citation metadata.
