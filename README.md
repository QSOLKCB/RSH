# RSH — Robitaille–Slade Helix

**Bounded Frenet–Serret geometry, deterministic evidence, and cross-runtime conformance.**

RSH constructs a three-dimensional path by prescribing curvature and torsion
inside explicit Robitaille bounds, integrating the Frenet–Serret frame, and
translating the exact discrete midpoint to the coordinate origin.

**Authors:** J. Robitaille (DeltaKingZero) and Trent Slade / QSOL-IMC  
**Release:** 2.1.0  
**Model contract:** 2.0.0  
**Implementations:** Python reference + native Rust core/CLI

## Project site

The static project site is deployed from `web/` through GitHub Actions:

**https://qsolkcb.github.io/RSH/**

The animated page graphic is explicitly schematic. It is not part of the
verification evidence and does not replace the numerical implementations.

## Implementation authority

The Python implementation remains the readable scientific oracle. It defines
the equations, validation rules, canonical report schema, golden coordinates,
and reference receipt.

The Rust implementation reproduces the same geometry and verification contract
as a native core and command-line runner. It is accepted through the checked-in
cross-runtime conformance record. Runtime receipt identity is reported
separately rather than assumed.

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

The 129-sample Rust conformance run currently reproduces the Python golden entry
and exit coordinates with maximum absolute errors below `5e-16`, comfortably
inside the declared `1e-12` tolerance.

The Rust receipt is intentionally displayed alongside the Python reference
receipt. Their difference is not hidden: the coordinate path conforms, while
transcendental floating-point details produce a distinct canonical report hash.

## Exact bounded logical sampling

Large logical fields can be represented without allocating the full field:

```text
logical_index(i) = floor(i × logical_count / rendered_count)
```

Both implementations use exact integer arithmetic for this mapping.

## Repository map

```text
rsh_runner.py                 Direct Python source-checkout runner
src/rsh/                      Python geometry, verification, exports, and CLI
crates/rsh-core/              Native Rust geometry and evidence library
crates/rsh-cli/               Native `rsh-rust` command-line runner
conformance/                  Cross-runtime golden records
web/                          Static GitHub Pages project site
tests/                        Python geometry, evidence, export, and CLI tests
docs/MODEL.md                 Equations and numerical construction
docs/PROVENANCE.md            Attribution and implementation boundary
docs/SCIENTIFIC_BOUNDARY.md   Claims the evidence does and does not support
docs/ROADMAP.md               Python → Rust → WASM/WGSL plan
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
3. **WASM bridge** — next: expose the Rust core to the offline browser site.
4. **WGSL compute and visual kernels** — GPU acceleration checked against shared vectors.
5. **Optional C++/CUDA adapter** — only where interoperability requires it.

Performance never promotes an implementation to scientific authority. Every
backend must reproduce the declared contracts and state its numerical boundary.

## Licence and citation

MPL-2.0. See `NOTICE.md` for attribution and `CITATION.cff` for citation metadata.
