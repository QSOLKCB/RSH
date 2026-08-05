# RSH testing guide

Run commands from the repository root. This file is the canonical executable test
map for humans and AI agents.

## Environment

```bash
python3 --version
python3 -m pip --version
rustc --version
cargo --version
rustup --version
node --version
cmake --version
```

Optional GPU, CUDA, WebGPU, or NPU tools must be reported separately. Never infer
hardware execution from a source check, a successful build, or a CPU reference.

## Python reference

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --disable-pip-version-check -e .

python -m compileall -q src tests scripts rsh_runner.py
python -m unittest discover -s tests -v
```

Canonical smoke suite:

```bash
mkdir -p audit-output

python rsh_runner.py verify \
  -n 129 \
  -o audit-output/python-verify.csv \
  --json audit-output/python-verify.json

python rsh_runner.py receipt -n 129
python rsh_runner.py parity -n 129 --workers 3
python rsh_runner.py trace -n 129 -o audit-output/python-trace.csv
python rsh_runner.py visual -n 129 -o audit-output/python-visual.svg

rsh constitution --json audit-output/python-constitution.json
rsh tissue \
  --json audit-output/python-tissue.json \
  --trace audit-output/python-tissue.csv
```

The project uses `unittest` as its canonical Python runner. A pytest-only result
is useful additional evidence, but it is not the declared CI contract.

## Native Rust

```bash
rustup toolchain install stable --profile minimal --component rustfmt,clippy
rustup default stable

cargo fmt --all -- --check
cargo clippy --locked --workspace --all-targets -- -D warnings
cargo test --locked --workspace
```

Native smoke commands:

```bash
cargo run --locked -p rsh-cli -- verify -n 129 \
  --json audit-output/rust-verify.json
cargo run --locked -p rsh-cli -- conformance \
  --json audit-output/rust-conformance.json

cargo run --locked -p rsh-numerics-cli -- \
  run -n 1025 \
  --json audit-output/frenet-path.json \
  --csv audit-output/frenet-path.csv

cargo run --locked -p rsh-parallel-cli -- \
  run --samples 1025 \
  --json audit-output/parallel-path.json \
  --csv audit-output/parallel-path.csv
cargo run --locked -p rsh-parallel-cli -- \
  shards --samples 4097 --interval-width 256 \
  --json audit-output/parallel-shards.json

cargo run --locked -p rsh-tissue-cli -- \
  run \
  --json audit-output/rust-tissue.json \
  --csv audit-output/rust-tissue.csv
cargo run --locked -p rsh-tissue-cli -- \
  conformance \
  --json audit-output/rust-tissue-conformance.json
```

CPU benchmark commands are observational and must keep `speedup_claim: false`:

```bash
cargo run --release --locked -p rsh-numerics-cli -- \
  benchmark -n 16385 --loops 20

cargo run --release --locked -p rsh-parallel-cli -- \
  benchmark --samples 16385 --loops 10 \
  --json audit-output/parallel-cpu-benchmark.json
```

## Compiled WebAssembly

```bash
rustup target add wasm32-unknown-unknown

cargo test --locked \
  -p rsh-wasm \
  -p rsh-numerics-wasm \
  -p rsh-parallel-wasm \
  -p rsh-tissue-wasm

cargo build --locked --release --target wasm32-unknown-unknown \
  -p rsh-wasm \
  -p rsh-numerics-wasm \
  -p rsh-parallel-wasm \
  -p rsh-tissue-wasm
```

Verify the four-byte WebAssembly magic value:

```bash
for wasm in \
  target/wasm32-unknown-unknown/release/rsh_wasm.wasm \
  target/wasm32-unknown-unknown/release/rsh_numerics_wasm.wasm \
  target/wasm32-unknown-unknown/release/rsh_parallel_wasm.wasm \
  target/wasm32-unknown-unknown/release/rsh_tissue_wasm.wasm
do
  test -s "$wasm"
  test "$(od -An -t x1 -N4 "$wasm" | tr -d ' \n')" = "0061736d"
done
```

Geometry conformance:

```bash
cargo run --locked -p rsh-cli -- verify -n 129 \
  --json audit-output/rust-native-129.json

node scripts/test_wasm.mjs \
  target/wasm32-unknown-unknown/release/rsh_wasm.wasm \
  conformance/wasm_v2_129.json \
  audit-output/rust-native-129.json \
  conformance/wgsl_v1_4096.json
```

Full-path numerical conformance:

```bash
node scripts/test_frenet_path.mjs \
  target/wasm32-unknown-unknown/release/rsh_numerics_wasm.wasm \
  conformance/frenet_path_v1_1025.json
```

Parallel Frenet conformance:

```bash
cargo run --locked -p rsh-parallel-cli -- \
  run --samples 1025 --json audit-output/parallel-native.json

node scripts/test_parallel_frenet.mjs \
  target/wasm32-unknown-unknown/release/rsh_parallel_wasm.wasm \
  conformance/frenet_parallel_v1_1025.json \
  audit-output/parallel-native.json
```

Tissue conformance across Python, native Rust, and compiled WASM:

```bash
python rsh_runner.py tissue --json audit-output/tissue-python.json
cargo run --locked -p rsh-tissue-cli -- \
  run --json audit-output/tissue-rust.json

node scripts/test_tissue_wasm.mjs \
  target/wasm32-unknown-unknown/release/rsh_tissue_wasm.wasm \
  conformance/tissue_v1_8x20.json \
  audit-output/tissue-python.json \
  audit-output/tissue-rust.json
```

Runtime receipts may differ. Cross-runtime acceptance uses the declared portable
observable tolerance; same-runtime deterministic replay remains mandatory.

## C++17 and Rust FFI

```bash
cmake -S native/cpp -B build/native -DCMAKE_BUILD_TYPE=Release
cmake --build build/native --parallel 2
ctest --test-dir build/native --output-on-failure

python3 scripts/test_cpp_ffi.py \
  build/native/rsh-cpp \
  conformance/ffi_v1_129.json \
  conformance/cuda_schedule_v1_4096.json
```

The CPU f32 CUDA reference is not actual CUDA execution.

## CUDA hardware validation

First run the non-mutating preflight:

```bash
sh scripts/cuda_preflight.sh
```

Build only on a CUDA-capable host with the toolkit installed:

```bash
cmake -S native/cpp -B build/cuda \
  -DCMAKE_BUILD_TYPE=Release \
  -DRSH_ENABLE_CUDA=ON \
  -DRSH_CUDA_ARCHITECTURES=native
cmake --build build/cuda --parallel 2
```

Run the repository harness against the actual CUDA executable:

```bash
python3 scripts/test_cuda.py \
  --executable build/cuda/rsh-cuda \
  --profile conformance/cuda_schedule_v1_4096.json \
  --runs 3 \
  --sanitizers auto \
  --output audit-output/cuda
```

A valid hardware claim requires real kernel launch, synchronization, readback,
and `actual_cuda_execution: true`. CUDA schedule evidence remains
`geometry_receipt_authority: false`.

## Browser and WebGPU source validation

Routine CI validates source and fallback boundaries without claiming a GPU run:

```bash
node --check web/app.js
node --check web/gpu.js
node --check web/frenet.js
node --check web/path-gpu.js
node --check web/parallel.js
node --check web/parallel-gpu.js
node --check web/tissue.js
node --check web/sw.js

node --check scripts/test_wasm.mjs
node --check scripts/test_frenet_path.mjs
node --check scripts/test_parallel_frenet.mjs
node --check scripts/test_tissue_wasm.mjs
```

Actual WebGPU evidence requires a browser adapter, full buffer readback, and a
passing sidecar. A compiled WGSL module alone is not hardware execution.

## Conformance and documentation syntax

```bash
for profile in conformance/*.json conformance/observed/*.json; do
  test -f "$profile" || continue
  python3 -m json.tool "$profile" >/dev/null
done

python3 -m py_compile \
  scripts/test_cpp_ffi.py \
  scripts/test_cuda.py \
  scripts/package_evidence.py

sh -n scripts/cuda_preflight.sh
```

## Change-to-test matrix

| Changed area | Minimum validation |
|---|---|
| `src/rsh/**`, `tests/**` | Python compile, `unittest`, relevant CLI smoke command |
| Rust crates | fmt, Clippy, workspace tests, relevant native CLI |
| WASM ABI | host ABI tests, release WASM build, Node harness |
| `web/**`, WGSL | Node syntax checks, fallback review, Pages validation |
| C++/FFI | CMake build, CTest, FFI harness |
| CUDA | portable checks; actual claims require a hardware run |
| conformance JSON | JSON parse plus every profile consumer |
| receipt/canonical JSON | deterministic replay and receipt regression tests |
| parallel shards | prefix, overlap, order, missing-tail, coverage, final reduction |
| docs only | links, commands, filenames, and CI presence checks |

## Evidence manifest

```bash
find audit-output -maxdepth 1 -type f ! -name SHA256SUMS.txt -print0 \
  | sort -z \
  | xargs -0 sha256sum \
  > audit-output/SHA256SUMS.txt
```

Do not make a checksum manifest recursively hash itself.