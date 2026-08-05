# RSH agent guide

This file is the canonical starting point for AI coding agents, review agents,
and automated audit environments working on this repository.

Read these files before changing code:

1. [`README.md`](README.md) — project purpose and public usage;
2. [`ROADMAP.md`](ROADMAP.md) — active and queued upgrade tracks;
3. [`ARCHITECTURE.md`](ARCHITECTURE.md) — runtime and authority boundaries;
4. [`TESTING.md`](TESTING.md) — exact validation commands;
5. [`COMMANDS.md`](COMMANDS.md) — executable CLI and laboratory commands;
6. the relevant phase document under [`docs/`](docs/).

## Non-negotiable project boundaries

RSH has multiple implementations, but they do not have equal authority.

- The readable Python geometry implementation is the canonical scientific oracle.
- Rust, WASM, WGSL, C++, CUDA, NPU, and parallel research layers are accepted
  only through their declared contracts and conformance gates.
- Receipts prove deterministic evidence identity for a declared runtime and
  serialization path. They do not prove physical truth.
- A CPU f32 reference is not actual CUDA execution.
- A compiled shader is not actual WebGPU execution.
- A hardware profile is not a hardware binding.
- Performance, parallelism, or hardware execution never promotes an adapter into
  geometry-receipt authority.
- `Q_f` is a functional cohesion metric. Do not describe it as consciousness,
  sentience, life, qualia, or subjective awareness.
- Do not claim autonomous self-modification. Refinement remains a bounded dry-run
  recommendation process requiring the declared human acknowledgement boundary.

Preserve explicit false fields such as:

```text
geometry_receipt_authority: false
subjective_awareness_claim: false
autonomous_source_modification: false
universal_speedup_claim: false
```

Do not remove or invert these boundaries to make a result look more impressive.

## Repository layout

```text
src/rsh/                    Python reference and installed `rsh` CLI
crates/rsh-core/            canonical Rust geometry implementation
crates/rsh-cli/             native Rust geometry CLI
crates/rsh-wasm/            raw geometry WASM ABI
crates/rsh-numerics*/       separately versioned full-path numerical research
crates/rsh-parallel*/       separately versioned parallel-prefix research
crates/rsh-tissue*/         Rust/native/WASM tissue contract implementation
crates/rsh-ffi/             Rust C ABI
native/cpp/                 C++17 consumer and CMake project
native/cuda/                optional CUDA adapters
web/                        offline browser laboratories and WGSL shaders
conformance/                sealed machine-readable profiles
scripts/                    cross-runtime and hardware validation harnesses
tests/                      Python unit and CLI tests
fuzz/                       cargo-fuzz targets
docs/                       phase contracts, evidence policy, and release notes
```

## Environment baseline

Required for the complete portable suite:

- Python 3.10 or newer;
- Rust stable with `rustfmt` and `clippy`;
- Node.js with WebAssembly support;
- CMake and a C++17 compiler for native adapter tests.

Optional:

- `wasm32-unknown-unknown` Rust target;
- WebGPU-capable browser and adapter;
- NVIDIA driver, CUDA toolkit, and Compute Sanitizer;
- trusted self-hosted hardware runners.

Never silently install or replace GPU drivers. Report unavailable optional
hardware as `BLOCKED BY ENVIRONMENT` rather than simulating a pass.

## First-time setup

From the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --disable-pip-version-check -e .

rustup toolchain install stable --profile minimal --component rustfmt,clippy
rustup default stable
rustup target add wasm32-unknown-unknown
```

The Python package uses a `src/` layout. The intended invocation is the installed
entry point:

```bash
rsh -h
```

For a no-install diagnostic only, use:

```bash
PYTHONPATH=src python -m rsh -h
```

Do not use `python -m src.rsh` as the canonical command.

## Fast validation

Run the smallest useful gate after a local edit:

```bash
python -m unittest discover -s tests -v
cargo fmt --all -- --check
cargo clippy --locked --workspace --all-targets -- -D warnings
cargo test --locked --workspace
```

For complete commands, including WASM, C++/FFI, CUDA, browser source checks, and
cross-runtime tissue/parallel conformance, follow [`TESTING.md`](TESTING.md).

## Change-to-test mapping

| Changed area | Minimum required checks |
|---|---|
| `src/rsh/**`, `tests/**` | Python compile, unit tests, relevant CLI evidence command |
| `crates/**` | `cargo fmt`, Clippy, workspace tests, relevant native CLI |
| `*-wasm`, WASM ABI | host ABI tests, release WASM build, Node conformance harness |
| `web/**`, WGSL | `node --check`, Pages source checks, browser fallback preserved |
| `native/cpp/**`, `rsh-ffi` | CMake build, CTest, `scripts/test_cpp_ffi.py` |
| `native/cuda/**` | portable source checks; real CUDA claims require actual hardware run |
| `conformance/**` | JSON validation plus every consumer of the changed profile |
| receipts/canonical JSON | deterministic replay and same-runtime receipt tests |
| parallel shard logic | ordering, overlap, missing-prefix, missing-tail, and final-reduction tests |
| docs/metadata only | syntax/link review plus any CI file-presence checks |

## Coding rules

- Keep implementations dependency-light and deterministic.
- Use bounded inputs before allocation, iteration, FFI access, or GPU dispatch.
- Reject booleans where an integer count is required.
- Validate pointer/length spans before reading WASM or FFI memory.
- Keep error payloads schema-complete, including serialization fallbacks.
- Preserve exact interval order for non-commutative SE(3) composition.
- Do not insert nonlinear per-step projection into an associative prefix scan
  without defining a new numerical contract.
- Do not tighten published residual gates from one hardware observation.
- Do not edit `Cargo.lock` by hand except to repair a proven corruption; normally
  regenerate it with Cargo and retain `--locked` in validation commands.
- Keep generated evidence outside source directories unless the profile explicitly
  calls for a checked-in noncanonical observation.

## Evidence and benchmark language

Use these distinctions precisely:

- **built** — compilation completed;
- **executed** — the implementation actually ran;
- **read back** — output returned from the adapter/device;
- **conformant** — declared residual and invariant gates passed;
- **observed speedup** — an actual device benchmark passed the published timing
  protocol for the recorded environment;
- **universal speedup** — not claimed by this repository.

A benchmark must record warm-up, measured runs, timing scope, median, sample count,
software versions, and device metadata before setting `speedup_claim: true`.

## Working with source ZIPs

A ZIP exported from GitHub normally lacks `.git` metadata. In that environment:

- hash the ZIP and important source/profile files;
- state that the exact commit cannot be proven from the extracted tree alone;
- do not invent a branch, tag, or commit identity;
- still run the full available conformance suite.

## Pull request expectations

Before declaring a PR ready:

1. address every actionable unresolved review thread;
2. add regression coverage for the reported failure mode;
3. run the relevant local/CI matrix;
4. reply with the fixing commit and exact behavioural change;
5. resolve only threads that are actually addressed;
6. state optional hardware coverage honestly;
7. keep release, contract, and evidence versions distinct.

When uncertain, prefer a narrower claim and stronger evidence.