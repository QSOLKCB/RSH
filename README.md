# RSH — Robitaille–Slade Helix

**Bounded Frenet–Serret geometry, deterministic evidence, and cross-runtime conformance.**

RSH constructs a three-dimensional path by prescribing curvature and torsion
inside explicit Robitaille bounds, integrating the Frenet–Serret frame, and
translating the exact discrete midpoint to the coordinate origin.

**Authors:** J. Robitaille (DeltaKingZero) and Trent Slade / QSOL-IMC  
**Release:** 2.2.0  
**Model contract:** 2.0.0  
**Implementations:** Python reference + native Rust core/CLI + Rust/WebAssembly browser bridge

## Browser laboratory

The project site now runs the verified Rust core directly in WebAssembly:

**https://qsolkcb.github.io/RSH/**

The browser laboratory can change the sample count, curvature fraction, torsion
floor, and torsion amplitude; run the contract; inspect the resulting evidence
report; and download JSON and CSV outputs. JavaScript does not reproduce the
geometry equations. It passes scalar inputs through a small raw WASM ABI, reads
the UTF-8 JSON result from linear memory, and handles only interface, projection,
animation, downloads, and offline caching.

The rotating canvas is a projection of verified samples. It is not additional
evidence and does not create a physical interpretation.

After the first successful load, a service worker caches the page and WASM
module for offline reuse.

## Implementation authority

The Python implementation remains the readable scientific oracle. It defines
the equations, validation rules, canonical report schema, golden coordinates,
and reference receipt.

The Rust implementation reproduces the same geometry and verification contract
as a native core and command-line runner. It is accepted through the checked-in
cross-runtime conformance record. Runtime receipt identity is reported
separately rather than assumed.

The WASM bridge calls `rsh-core`; it is not a third geometry implementation. Its
ABI accepts numeric configuration values and exposes one JSON result buffer:

```text
rsh_abi_version() -> u32
rsh_run(samples, s0, s1, kappa_fraction, tau_floor, tau_amplitude) -> i32
rsh_output_ptr() -> pointer
rsh_output_len() -> length
```

Return code `0` means all report contracts passed, `1` means a report was
produced with at least one failed contract, and `2` means the configuration or
run was rejected.

See [the complete Phase 3 specification](docs/PHASE3_WASM.md) for the ABI,
conformance profile, browser boundary, and acceptance criteria.

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
| Browser authority | report and samples supplied by `rsh-core` through WASM |
| WASM acceptance | actual compiled module executed against `wasm_v2_129.json` |

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

The 129-sample Rust conformance run reproduces the Python golden entry and exit
coordinates within the declared `1e-12` tolerance. The Rust receipt is displayed
alongside the Python reference receipt; any runtime-sensitive floating-point
hash difference remains visible.

## WebAssembly build and conformance

The deployed bridge uses only the standard Rust WASM target and existing
workspace dependencies. It does not require `wasm-bindgen`, `wasm-pack`, npm, a
bundler, CDN, or runtime server process.

```bash
rustup target add wasm32-unknown-unknown
cargo test --locked -p rsh-wasm
cargo build --locked --release --target wasm32-unknown-unknown -p rsh-wasm
mkdir -p web/pkg
cp target/wasm32-unknown-unknown/release/rsh_wasm.wasm web/pkg/
```

CI additionally uses the runner's built-in Node WebAssembly runtime—without npm
packages—to execute the actual compiled module against the sealed profile:

```bash
node scripts/test_wasm.mjs \
  target/wasm32-unknown-unknown/release/rsh_wasm.wasm \
  conformance/wasm_v2_129.json
```

The probe checks the ABI, midpoint, entry and exit residuals, report contracts,
sample count, finite output, and receipt encoding. Native-versus-WASM receipt
identity is reported separately rather than assumed.

GitHub Pages performs the build and executable conformance test itself before
deployment and refuses to publish when either fails.

## Exact bounded logical sampling

Large logical fields can be represented without allocating the full field:

```text
logical_index(i) = floor(i × logical_count / rendered_count)
```

The Python and Rust implementations use exact integer arithmetic for this
mapping. The future WGSL backend must reproduce the same selected indices.

## Repository map

```text
rsh_runner.py                 Direct Python source-checkout runner
src/rsh/                      Python geometry, verification, exports, and CLI
crates/rsh-core/              Native Rust geometry and evidence library
crates/rsh-cli/               Native `rsh-rust` command-line runner
crates/rsh-wasm/              Raw WebAssembly ABI over `rsh-core`
conformance/                  Python, Rust, and WASM acceptance profiles
scripts/test_wasm.mjs         Executes the compiled module against golden data
web/                          Interactive Pages laboratory and offline cache
tests/                        Python geometry, evidence, export, and CLI tests
docs/MODEL.md                 Equations and numerical construction
docs/PHASE3_WASM.md           WebAssembly architecture and acceptance contract
docs/PROVENANCE.md            Attribution and implementation boundary
docs/SCIENTIFIC_BOUNDARY.md   Claims the evidence does and does not support
docs/ROADMAP.md               Python → Rust → WASM → WGSL plan
```

## Scientific precision

The central sample reaches the origin because the integrated path is translated
there as an explicit coordinate convention. That check confirms implementation
correctness; it is not an empirical discovery.

Receipts prove identity of a canonical report under a declared runtime and
encoding contract. They do not, by themselves, prove a physical interpretation.
Cross-runtime conformance proves agreement within specified observables and
numerical tolerances; it does not claim every intermediate floating-point bit is
identical.

See [the scientific boundary](docs/SCIENTIFIC_BOUNDARY.md) for the full statement.

## Planned sequence

1. **Python reference** — complete.
2. **Rust core and CLI** — implemented in v2.1.0.
3. **WASM bridge and browser laboratory** — implemented in v2.2.0.
4. **WGSL compute and visual kernels** — next: GPU acceleration checked against shared vectors.
5. **Optional C++/CUDA adapter** — only where interoperability requires it.

Performance never promotes an implementation to scientific authority. Every
backend must reproduce the declared contracts and state its numerical boundary.

## Licence and citation

MPL-2.0. See `NOTICE.md` for attribution and `CITATION.cff` for citation metadata.
