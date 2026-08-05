# RSH command reference

Run commands from the repository root. Install the Python package first:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

## Python CLI

The installed entry point is `rsh`.

```bash
rsh -h
rsh info
```

### Canonical geometry

```bash
rsh verify -n 129 \
  -o rsh_verify.csv \
  --json rsh_verify.json

rsh trace -n 129 -o rsh_trace.csv
rsh visual -n 129 -o rsh_visual.svg
rsh receipt -n 129
rsh parity -n 129 --workers 3
rsh benchmark -n 4097
rsh sample 16777216 12
```

The repository runner exposes the same Python surface without relying on the
installed console script:

```bash
python rsh_runner.py -h
python rsh_runner.py verify -n 129
```

A no-install diagnostic is available through:

```bash
PYTHONPATH=src python -m rsh -h
```

Do not treat `python -m src.rsh` as the canonical invocation.

### Constitution and tissue

```bash
rsh constitution --json rsh_constitution.json

rsh tissue \
  --cells 8 \
  --ticks 20 \
  --json rsh_tissue.json \
  --trace rsh_tissue.csv
```

Bounded refinement is a dry-run recommendation, not autonomous source editing:

```bash
cat > refinement.json <<'JSON'
{
  "schema": "RSH-REFINEMENT-PROPOSAL-V1",
  "id": "example-binding-diffusion",
  "changes": {
    "binding_diffusion": 0.2
  }
}
JSON

rsh refine-dry-run refinement.json \
  --json refinement_decision.json
```

## Native Rust geometry CLI

```bash
cargo run --locked -p rsh-cli -- info
cargo run --locked -p rsh-cli -- verify --help
cargo run --locked -p rsh-cli -- trace --help
cargo run --locked -p rsh-cli -- conformance --help

cargo run --locked -p rsh-cli -- \
  verify -n 129 --json rsh_rust_verify.json

cargo run --locked -p rsh-cli -- \
  conformance --json rsh_rust_conformance.json

cargo run --locked -p rsh-cli -- \
  trace -n 65 -o rsh_rust_trace.csv
```

## Full-path Frenet numerical research

This is the separately versioned `RSH-FRENET-NUMERICS-V1` surface. It does not
replace the canonical geometry contract or receipt.

```bash
cargo run --locked -p rsh-numerics-cli -- info

cargo run --locked -p rsh-numerics-cli -- \
  run -n 1025 \
  --json rsh_frenet_path.json \
  --csv rsh_frenet_path.csv

cargo run --release --locked -p rsh-numerics-cli -- \
  benchmark -n 16385 --loops 20
```

The native benchmark is an observation only and makes no GPU speedup claim.

## Parallel Frenet research

This is the separately versioned `RSH-FRENET-PARALLEL-V1` surface.

```bash
cargo run --locked -p rsh-parallel-cli -- info

cargo run --locked -p rsh-parallel-cli -- \
  run --samples 1025 \
  --json rsh_parallel_report.json \
  --csv rsh_parallel_path.csv

cargo run --locked -p rsh-parallel-cli -- \
  shards --samples 4097 --interval-width 256 \
  --json rsh_parallel_shards.json

cargo run --release --locked -p rsh-parallel-cli -- \
  benchmark --samples 16385 --loops 10 \
  --json rsh_parallel_cpu_benchmark.json
```

Shard summaries are ordered local reductions and distributed-computation
groundwork. They are not evidence that multiple devices or machines executed.

## Native Rust tissue CLI

```bash
cargo run --locked -p rsh-tissue-cli -- info

cargo run --locked -p rsh-tissue-cli -- \
  run \
  --json rsh_tissue_rust.json \
  --csv rsh_tissue_rust.csv

cargo run --locked -p rsh-tissue-cli -- \
  conformance \
  --json rsh_tissue_rust_conformance.json
```

## Compiled WASM conformance

Build all browser modules:

```bash
rustup target add wasm32-unknown-unknown

cargo build --locked --release --target wasm32-unknown-unknown \
  -p rsh-wasm \
  -p rsh-numerics-wasm \
  -p rsh-parallel-wasm \
  -p rsh-tissue-wasm
```

Run the Node harnesses:

```bash
node scripts/test_wasm.mjs \
  target/wasm32-unknown-unknown/release/rsh_wasm.wasm \
  conformance/wasm_v2_129.json

node scripts/test_frenet_path.mjs \
  target/wasm32-unknown-unknown/release/rsh_numerics_wasm.wasm \
  conformance/frenet_path_v1_1025.json

cargo run --locked -p rsh-parallel-cli -- \
  run --samples 1025 --json /tmp/rsh_parallel_native.json
node scripts/test_parallel_frenet.mjs \
  target/wasm32-unknown-unknown/release/rsh_parallel_wasm.wasm \
  conformance/frenet_parallel_v1_1025.json \
  /tmp/rsh_parallel_native.json

python rsh_runner.py tissue --json /tmp/rsh_tissue_python.json
cargo run --locked -p rsh-tissue-cli -- \
  run --json /tmp/rsh_tissue_rust.json
node scripts/test_tissue_wasm.mjs \
  target/wasm32-unknown-unknown/release/rsh_tissue_wasm.wasm \
  conformance/tissue_v1_8x20.json \
  /tmp/rsh_tissue_python.json \
  /tmp/rsh_tissue_rust.json
```

## C++17 and FFI

```bash
cmake -S native/cpp -B build/native -DCMAKE_BUILD_TYPE=Release
cmake --build build/native --parallel 2
ctest --test-dir build/native --output-on-failure

build/native/rsh-cpp --help

python3 scripts/test_cpp_ffi.py \
  build/native/rsh-cpp \
  conformance/ffi_v1_129.json \
  conformance/cuda_schedule_v1_4096.json
```

## CUDA

Preflight without changing the host:

```bash
sh scripts/cuda_preflight.sh
```

Configure an actual CUDA build:

```bash
cmake -S native/cpp -B build/cuda \
  -DCMAKE_BUILD_TYPE=Release \
  -DRSH_ENABLE_CUDA=ON \
  -DRSH_CUDA_ARCHITECTURES=native
cmake --build build/cuda --parallel 2
```

Hardware validation:

```bash
python3 scripts/test_cuda.py \
  --executable build/cuda/rsh-cuda \
  --profile conformance/cuda_schedule_v1_4096.json \
  --runs 3 \
  --sanitizers auto \
  --output artifacts/cuda-audit
```

A CPU f32 `cuda-reference` result is not actual CUDA. A hardware statement
requires kernel launch, synchronization, readback, and
`actual_cuda_execution: true`.

## Browser laboratories

After GitHub Pages deployment:

```text
https://qsolkcb.github.io/RSH/
https://qsolkcb.github.io/RSH/frenet.html
https://qsolkcb.github.io/RSH/parallel.html
https://qsolkcb.github.io/RSH/tissue.html
```

The laboratories are static and offline-capable after a successful first load.
WebGPU absence must preserve the Rust/WASM fallback and must not generate a GPU
claim.

## Fuzzing

Deterministic stress cases run in ordinary Rust tests. The heavier fuzz workflow
is manual/scheduled:

```bash
cargo install cargo-fuzz
cargo fuzz run frenet_path
```

Only run fuzz targets defined under `fuzz/fuzz_targets/`. Keep bounded input
projection and do not convert random bytes directly into unbounded allocations.

## Full test guide

See [`TESTING.md`](TESTING.md) for the validation matrix, evidence rules, and
change-to-test mapping.