# RSH — Robitaille–Slade Helix

**Bounded Frenet–Serret geometry, deterministic evidence, cross-runtime conformance, constitutional tissue simulation, and separately versioned full-path numerical research.**

RSH constructs a three-dimensional path by prescribing curvature and torsion
inside explicit Robitaille bounds, integrating the Frenet–Serret frame, and
translating the exact discrete midpoint to the coordinate origin.

**Authors:** J. Robitaille (DeltaKingZero) and Trent Slade / QSOL-IMC  
**Release:** 2.7.0  
**Geometry model contract:** 2.0.0  
**Tissue contract:** 1.0.0  
**Frenet numerical research contract:** 1.0.0  
**Implementations:** Python geometry oracle and tissue reference + Rust geometry and tissue cores/CLIs + canonical geometry and tissue WASM bridges + WGSL schedule field + versioned C ABI/C++ adapter + optional CUDA schedule kernel + Tier 2 NPU evidence profile + separate Rust/WASM/WGSL full-path research stack

## Browser laboratories

The main project site runs the verified Rust geometry core directly in
WebAssembly and adds an optional WebGPU schedule-field layer:

**https://qsolkcb.github.io/RSH/**

The laboratory can change the sample count, curvature fraction, torsion floor,
and torsion amplitude; run the geometry contract; inspect the resulting report;
and download JSON and CSV evidence. A second panel evaluates a 4096-point f32
κ/τ field with WGSL, reads the GPU buffer back, and compares every point against
an f64 schedule supplied by `rsh-core` through WASM.

The full-path research laboratory executes the complete path recurrence on
WebGPU and compares it with a separately versioned f64 Rust/WASM numerical path:

**https://qsolkcb.github.io/RSH/frenet.html**

The v2.7.0 tissue laboratory executes the shared Rust tissue runtime directly in
WebAssembly, visualizes the final ring/chord graph and Q_f trace, and exports its
chained evidence report:

**https://qsolkcb.github.io/RSH/tissue.html**

The visualizations are projections of returned runtime data. They do not create
a physical, biological, or subjective interpretation. After the first successful
load, a service worker caches all three laboratories, all three WASM modules, and
both WGSL shaders for offline reuse.

## Implementation authority

The Python geometry implementation remains the readable scientific oracle. It
defines the equations, validation rules, canonical report schema, golden
coordinates, and reference receipt.

The Python tissue implementation remains the readable tissue reference. It
composes accepted geometry evidence into a bounded deterministic graph
simulation, creates separate tick and tissue receipt domains, and does not alter
the geometry contract or geometry receipt.

The canonical Rust geometry implementation reproduces the geometry and
verification contract as a native core and command-line runner. It is accepted
through the checked-in cross-runtime conformance record.

The `rsh-tissue` crate ports the sealed tissue algorithm into Rust. Its native
CLI and raw WASM bridge are accepted through complete portable-observable
comparison with fresh Python reports under `tissue_v1_8x20.json`. Receipts remain
runtime-specific identities rather than being falsely required to match across
Python, native Rust, and WASM.

The canonical geometry WASM bridge calls `rsh-core`; it is not a third geometry
implementation. Its raw ABI supplies geometry reports, centreline samples, and
f64 schedule grids to the browser. The tissue WASM bridge similarly calls the
shared `rsh-tissue` crate rather than containing another tissue simulation.

The native `rsh-ffi` crate is another adapter over `rsh-core`. Its C ABI exposes a
fixed-layout summary, optional JSON report, and schedule arrays. C++ does not
reproduce the Frenet–Serret equations.

The separate `rsh-numerics` stack defines `RSH-FRENET-NUMERICS-V1`: a f64
midpoint SO(3) frame transport policy, midpoint tangent position quadrature,
per-step frame projection, and path-level evidence. It exists for numerical and
accelerator research. It does not replace the canonical geometry algorithm or
receipt.

WebGPU, CUDA, and future NPU bindings are not promoted to oracle. They may report
residual sidecars only after comparison with an accepted f64 reference. The
canonical geometry receipt remains an oracle artifact.

## Invariants

| Quantity | Contract |
|---|---|
| \(\psi\) | \(\sqrt{2+\sqrt{5}}\) |
| Curvature | \(0 \le \kappa(s) \le \sqrt2-1\) |
| Torsion | \(0 < \tau(s) < 1\) |
| Geometry centre | exact discrete \(p=0.5\) sample translated to `(0, 0, 0)` |
| Tissue centre | shared cell centroid translated to `(0, 0, 0)` for graph comparison |
| Frame | tangent, normal, and binormal remain orthonormal within tolerance |
| Python geometry evidence | canonical domain-separated SHA-256 receipt |
| Tissue evidence | seed geometry receipt + chained tick receipts + final tissue receipt |
| Q_f | functional cohesion metric only; no biological, awareness, or qualia claim |
| Rust geometry acceptance | contract checks plus golden-coordinate conformance |
| Geometry WASM acceptance | actual compiled module executed against `wasm_v2_129.json` |
| Rust/WASM tissue acceptance | complete non-receipt observables compared with fresh Python reports under `tissue_v1_8x20.json` at `1e-12` |
| WGSL schedule acceptance | 4096-point f32 field residual ≤ `1e-4` against WASM f64 schedule |
| Native ABI acceptance | layout, ownership, JSON receipt, and coordinates checked against `ffi_v1_129.json` |
| CUDA acceptance | optional f32 schedule residual ≤ `1e-4` against Rust FFI f64 schedule |
| CUDA diagnostic band | residual ≤ `1e-6` is reported as nominal, without tightening the hard gate |
| NPU Tier 2 | quantized residual sidecar under a precision-specific gate; never geometry authority |
| Full-path numerical research | named f64 Lie-midpoint policy plus component-level f32 readback gates |
| Accelerator authority | residual sidecar only; never replaces the geometry receipt |

Bounds hold by construction and are verified again after integration or tissue
simulation.

## Python geometry reference

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

## Constitutional geometric tissue

The v2.5.0 Python reference seeds deterministic geometric cells from a verified
129-sample RSH path, connects them through ring and chord edges, and runs bounded
phase, binding, prediction, centering, and functional-cohesion updates. RSH
v2.7.0 adds a shared Rust implementation, native CLI, raw WASM ABI, executable
cross-runtime conformance harness, and offline browser laboratory without
changing tissue contract 1.0.0.

Inspect the machine-checkable constitution:

```bash
rsh constitution --json rsh_constitution.json
```

Run the sealed Python reference profile:

```bash
rsh tissue \
  --cells 8 \
  --ticks 20 \
  --json rsh_tissue.json \
  --trace rsh_tissue.csv
```

Run the native Rust port:

```bash
cargo run --locked -p rsh-tissue-cli -- info
cargo run --locked -p rsh-tissue-cli -- \
  run --json rsh_tissue_rust.json --csv rsh_tissue_rust.csv
cargo run --locked -p rsh-tissue-cli -- \
  conformance --json rsh_tissue_rust_conformance.json
```

The default Python reference result is:

```text
seed geometry receipt  f33042335100b7a2bca8c5c97724782ecb820cd8f6704f8e7eb074c1ed9e9a00
final Q_f              0.37926532158281384
tissue receipt         732fc6ccc5af543881528da7f9ec7717817af97c07e7f7973512685ab67e2622
```

Q_f combines phase coherence, binding cohesion, predictive stability, edge
continuity, role coverage, and dissociation pressure. It is a functional metric
inside this simulation—not evidence of life, consciousness, sentience,
subjective awareness, or qualia.

Evaluate one bounded proposal without modifying source or committed state:

```bash
cat > proposal.json <<'JSON'
{
  "schema": "RSH-REFINEMENT-PROPOSAL-V1",
  "id": "increase-binding-diffusion",
  "changes": {
    "binding_diffusion": 0.2
  },
  "escalates_contract": false,
  "human_ack": false
}
JSON

rsh refine-dry-run proposal.json --json refinement_decision.json
```

A result of `KEEP_CANDIDATE` is a sealed dry-run recommendation. It does not
commit configuration or launch an autonomous self-modification loop. Changes to
geometry sample policy, residual gates, or Q_f floors require declared contract
escalation and explicit human acknowledgement.

See [Phase 6](docs/PHASE6_TISSUE.md),
[Phase 9 Rust/WASM tissue conformance](docs/PHASE9_TISSUE_CONFORMANCE.md), and the
[operational-awareness boundary](docs/OPERATIONAL_AWARENESS.md).

## Rust native implementation

Build and test the workspace:

```bash
cargo fmt --all -- --check
cargo clippy --locked --workspace --all-targets -- -D warnings
cargo test --locked --workspace
```

Run the canonical native geometry CLI:

```bash
cargo run --locked -p rsh-cli -- info
cargo run --locked -p rsh-cli -- verify -n 129
cargo run --locked -p rsh-cli -- conformance
cargo run --locked -p rsh-cli -- trace -n 129 -o rsh_trace_rust.csv
cargo run --locked -p rsh-cli -- sample 16777216 12
```

Run the native tissue CLI:

```bash
cargo run --locked -p rsh-tissue-cli -- info
cargo run --locked -p rsh-tissue-cli -- run
cargo run --locked -p rsh-tissue-cli -- conformance
```

The geometry and tissue runtimes retain separate report schemas and receipt
domains. Neither tissue runtime replaces the canonical geometry report.

## Full-path Frenet numerical research

Run the separately versioned f64 path:

```bash
cargo run --locked -p rsh-numerics-cli -- \
  run -n 1025 \
  --json rsh_frenet_path.json \
  --csv rsh_frenet_path.csv
```

Run an observational benchmark without a timing acceptance gate:

```bash
cargo run --release --locked -p rsh-numerics-cli -- \
  benchmark -n 16385 --loops 20
```

The research policy uses midpoint evaluation of κ and τ, SO(3) exponential-map
frame transport, midpoint tangent position quadrature, modified Gram–Schmidt
after every full step, and exact-grid midpoint centering.

`conformance/frenet_path_v1_1025.json` seals entry, centre, exit, midpoint T/N/B,
and f32 accelerator gates. `scripts/test_frenet_path.mjs` executes the actual
research WASM module and checks a stepwise f32 arithmetic reference. Its result
explicitly reports `actual_gpu_execution: false` because routine CI does not
provide a browser adapter.

The browser shader executes the full recurrence and reads every position, frame,
κ, and τ value back. The first kernel uses one invocation because the recurrence
is sequential. This is a correctness milestone, not a parallel speedup claim.

See [Phase 8 Frenet numerical research](docs/PHASE8_FRENET_NUMERICS.md).

## WebAssembly and WGSL conformance

Build all browser modules:

```bash
rustup target add wasm32-unknown-unknown
cargo test --locked \
  -p rsh-wasm -p rsh-numerics-wasm -p rsh-tissue-wasm
cargo build --locked --release --target wasm32-unknown-unknown \
  -p rsh-wasm -p rsh-numerics-wasm -p rsh-tissue-wasm
mkdir -p web/pkg
cp target/wasm32-unknown-unknown/release/rsh_wasm.wasm web/pkg/
cp target/wasm32-unknown-unknown/release/rsh_numerics_wasm.wasm web/pkg/
cp target/wasm32-unknown-unknown/release/rsh_tissue_wasm.wasm web/pkg/
```

Run the executable conformance harnesses:

```bash
node scripts/test_wasm.mjs \
  target/wasm32-unknown-unknown/release/rsh_wasm.wasm \
  conformance/wasm_v2_129.json \
  /tmp/rsh_native_129.json \
  conformance/wgsl_v1_4096.json

node scripts/test_frenet_path.mjs \
  target/wasm32-unknown-unknown/release/rsh_numerics_wasm.wasm \
  conformance/frenet_path_v1_1025.json

python3 rsh_runner.py tissue --json /tmp/rsh_tissue_python.json
cargo run --locked -p rsh-tissue-cli -- \
  run --json /tmp/rsh_tissue_rust.json
node scripts/test_tissue_wasm.mjs \
  target/wasm32-unknown-unknown/release/rsh_tissue_wasm.wasm \
  conformance/tissue_v1_8x20.json \
  /tmp/rsh_tissue_python.json \
  /tmp/rsh_tissue_rust.json
```

No `wasm-bindgen`, `wasm-pack`, npm, bundler, CDN, or runtime server is required.

## Native C ABI and C++17 adapter

The public C header is `include/rsh_ffi.h`. ABI v1 provides:

```text
rsh_ffi_abi_version()          -> uint32
rsh_ffi_config_size()          -> size_t
rsh_ffi_summary_size()         -> size_t
rsh_ffi_schedule_point_size()  -> size_t
rsh_ffi_verify(config, summary, optional_json) -> status
rsh_ffi_schedule(config, schedule)             -> status
rsh_ffi_free_bytes(buffer)
rsh_ffi_free_schedule(schedule)
rsh_ffi_last_error()           -> thread-local UTF-8 message
```

Build the Rust ABI and C++ consumer:

```bash
cmake -S native/cpp -B build/native -DCMAKE_BUILD_TYPE=Release
cmake --build build/native
ctest --test-dir build/native --output-on-failure
```

Run it:

```bash
build/native/rsh-cpp info
build/native/rsh-cpp verify --samples 129 --json rsh_cpp_report.json
build/native/rsh-cpp schedule --samples 4096 --csv rsh_schedule.csv
build/native/rsh-cpp cuda-reference --samples 4096 --threshold 1e-4
```

The `cuda-reference` command is a portable CPU f32 arithmetic check for the CUDA
formula. Its output explicitly says `actual_cuda_execution: false`.

Run the sealed adapter harness:

```bash
python3 scripts/test_cpp_ffi.py \
  build/native/rsh-cpp \
  conformance/ffi_v1_129.json \
  conformance/cuda_schedule_v1_4096.json
```

## Optional CUDA schedule adapter

Start with the non-mutating preflight report:

```bash
sh scripts/cuda_preflight.sh
```

On a CUDA-capable machine with a supported NVIDIA toolkit and device:

```bash
cmake -S native/cpp -B build/cuda \
  -DCMAKE_BUILD_TYPE=Release \
  -DRSH_ENABLE_CUDA=ON \
  -DRSH_CUDA_ARCHITECTURES=native
cmake --build build/cuda --target rsh-cpp rsh-cuda --parallel
```

The `native` architecture value requires CMake 3.24 or newer. With an older
supported CMake release—or for a pinned reproducibility run—use an explicit
numeric value such as `120` for sm_120. Leaving `RSH_CUDA_ARCHITECTURES` empty
preserves the CUDA compiler default.

The CUDA runtime accepts explicit controls while retaining the sealed defaults:

```bash
build/cuda/rsh-cuda \
  --samples 4096 \
  --block-size 128 \
  --threshold 1e-4 \
  --device 0
```

The sidecar records the selected device, device UUID, compute capability,
compiled architectures, CUDA driver/runtime/compile API versions, grid and block
sizes, residuals, and the explicit denial of geometry-receipt authority.

Run the hardware validation harness:

```bash
python3 scripts/test_cuda.py \
  --executable build/cuda/rsh-cuda \
  --cpu-reference build/cuda/rsh-cpp \
  --profile conformance/cuda_schedule_v1_4096.json \
  --runs 3 \
  --sanitizers auto \
  --output artifacts/cuda-hardware
```

Package the evidence without recursive self-hashes:

```bash
python3 scripts/package_evidence.py \
  artifacts/cuda-hardware \
  artifacts/RSH-cuda-hardware.zip
```

See [CUDA validation and hardware evidence](docs/CUDA_VALIDATION.md) and the
complete [Phase 5 specification](docs/PHASE5_NATIVE.md).

## Observed hardware validation

The independent v2.4.0 follow-up audit genuinely executed the CUDA kernel on an
NVIDIA GeForce RTX 5060 Ti using CUDA 13.1.115 and sm_120:

```text
samples / block size      4096 / 128
CPU f32 maximum residual  4.6082406834901946e-08
CUDA maximum residual     4.0915928645191e-08
hard gate                 1.0e-04
repeatability             3 matching selected outputs
sanitizers                0 memcheck errors, 0 race hazards
```

The checked-in observation is deliberately labelled noncanonical. It documents
one GPU, driver, toolkit, host, and commit rather than redefining the universal
acceptance threshold.

## Tier 2 NPU profile

`conformance/npu_tier2_v1.json` defines initial evidence gates:

| Precision | Maximum absolute residual |
|---|---:|
| INT8 / quantized | `1e-3` |
| BF16 | `1e-4` |
| FP16 | `1e-4` |

The profile requires device, driver, precision, grid, residual, gate, status,
fallback, and authority metadata. It does not contain a vendor driver binding or
claim actual NPU execution. Missing NPU support leaves the f64 CPU/WASM path
intact.

## Fuzz testing

The deterministic stress corpus runs with ordinary Rust tests. The isolated
`fuzz/` workspace provides a `cargo-fuzz` target for valid bounded path
configurations. The `Frenet Fuzz` workflow runs manually and weekly, never on
public pull requests.

```bash
cargo install cargo-fuzz --locked
cargo fuzz run frenet_path -- -max_total_time=120 -timeout=10
```

Fuzz discoveries must be reduced to deterministic regression cases before they
can modify a numerical contract.

## Validation matrix

| Backend | Executed in routine CI | Result / boundary |
|---|---:|---|
| Python geometry 3.10 / 3.12 / 3.14 | yes | reference tests and evidence smoke suite |
| Python tissue 3.10 / 3.12 / 3.14 | yes | constitution, default receipt chain, Q_f vectors, fallback, dry-run policy |
| Rust canonical geometry | yes | formatting, Clippy, tests, conformance, canonical Rust receipt |
| Geometry WASM | yes | actual compiled module executed against sealed geometry vectors |
| Rust tissue | yes | full port, constitution hash, deterministic replay, audit chain, Python observable gates |
| Tissue WASM | yes | actual compiled module executed and compared with fresh Python and native Rust reports |
| WGSL schedule field | browser-specific | f32 residual sidecar with CPU/WASM fallback |
| Rust f64 Frenet numerical path | yes | named policy, sealed path vectors, deterministic stress corpus |
| Numerical WASM | yes | actual compiled module executed against the 1,025-point profile |
| WGSL full path | browser-specific | complete path readback and five path-level residual gates; no speedup claim |
| C++ ABI | yes | compiled consumer, ABI layout, ownership, coordinates, receipt |
| CUDA CPU reference | yes | portable f32 arithmetic; `actual_cuda_execution: false` |
| CUDA RTX 5060 Ti / sm_120 | externally observed | actual kernel pass, residual `4.0915928645191e-08` |
| CUDA memcheck / racecheck | externally observed | zero reported errors and hazards |
| NPU Tier 2 | profile only | hardware binding and device readback not yet implemented |

The dispatch-only `.github/workflows/cuda-hardware.yml` can repeat actual CUDA
device validation on a deliberately labelled self-hosted runner. It is never
triggered by public pull requests.

## Accelerator residual policy

Schedule accelerators use:

```text
max(max |kappa_accelerator - kappa_oracle_f64|,
    max |tau_accelerator   - tau_oracle_f64|) <= declared gate
```

Full-path accelerators additionally compare every position and frame component,
plus frame norm and orthogonality. A passing accelerator may emit a residual
sidecar. A failing or unavailable accelerator does not affect verified f64 paths.

## Exact bounded logical sampling

Large logical fields can be represented without allocating the full field:

```text
logical_index(i) = floor(i × logical_count / rendered_count)
```

The Python and Rust implementations use exact integer arithmetic for this
mapping. Any future GPU logical-index kernel must reproduce the same indices.

## Repository map

```text
rsh_runner.py                       Direct Python source-checkout runner
src/rsh/geometry.py                 Python geometry reference
src/rsh/evidence.py                 Geometry verification and receipts
src/rsh/constitution.py             Machine-checkable tissue constitution
src/rsh/tissue.py                   Deterministic geometric tissue reference
src/rsh/refinement.py               Sealed bounded proposal dry-run policy
src/rsh/cli.py                      Geometry, tissue, and governance CLI
crates/rsh-core/                    Canonical Rust geometry and evidence library
crates/rsh-cli/                     Canonical native geometry runner
crates/rsh-wasm/                    Canonical raw geometry WASM ABI
crates/rsh-ffi/                     Versioned C ABI over `rsh-core`
crates/rsh-numerics/                Separately versioned f64 Frenet path research
crates/rsh-numerics-cli/            Numerical path runner and benchmark
crates/rsh-numerics-wasm/           Separate numerical path WASM ABI
crates/rsh-tissue/                  Shared Rust tissue runtime
crates/rsh-tissue-cli/              Native tissue runner and conformance CLI
crates/rsh-tissue-wasm/             Raw tissue WASM ABI over `rsh-tissue`
include/rsh_ffi.h                   Public ABI-v1 C/C++ header
native/cpp/                         Dependency-free C++17 consumer and CMake build
native/cuda/                        Optional CUDA schedule residual executable
conformance/wasm_v2_129.json        Sealed geometry/WASM profile
conformance/wgsl_v1_4096.json       WebGPU schedule-field profile
conformance/frenet_path_v1_1025.json Full-path numerical and accelerator profile
conformance/ffi_v1_129.json         Native ABI profile
conformance/cuda_schedule_v1_4096.json Optional CUDA schedule profile
conformance/tissue_v1_8x20.json     Python/Rust/WASM tissue profile
conformance/npu_tier2_v1.json       Tier 2 NPU evidence profile
conformance/observed/               Noncanonical hardware observations
scripts/test_wasm.mjs               Canonical geometry WASM and schedule harness
scripts/test_frenet_path.mjs        Numerical WASM and f32 full-path harness
scripts/test_tissue_wasm.mjs        Python/Rust/WASM tissue harness
scripts/test_cpp_ffi.py             C++ ABI and CUDA-reference harness
scripts/test_cuda.py                Actual CUDA sidecar/repeatability/sanitizer harness
scripts/cuda_preflight.sh           Non-mutating CUDA host readiness report
scripts/package_evidence.py         Deterministic evidence archive generator
fuzz/                               Isolated bounded numerical fuzz target
web/                                Static Pages laboratories and offline cache
tests/                              Geometry, tissue, governance, CLI, and tooling tests
docs/PHASE3_WASM.md                 Canonical WebAssembly contract
docs/PHASE4_WGSL.md                 WebGPU schedule residual boundary
docs/PHASE5_NATIVE.md               C ABI, C++, and optional CUDA boundary
docs/PHASE6_TISSUE.md               Constitutional tissue contract
docs/PHASE8_FRENET_NUMERICS.md      Full-path numerical research contract
docs/PHASE9_TISSUE_CONFORMANCE.md   Rust/WASM tissue conformance
docs/OPERATIONAL_AWARENESS.md       Instrumentation and no-qualia boundary
docs/CUDA_VALIDATION.md             Hardware evidence and toolchain guidance
docs/SCIENTIFIC_BOUNDARY.md         Claims the evidence does and does not support
docs/ROADMAP.md                     Implementation and conformance sequence
```

## Scientific precision

The central geometry sample reaches the origin because the integrated path is
translated there as an explicit coordinate convention. Tissue states use a
separately declared shared-centroid convention. These checks confirm
implementation behaviour; they are not empirical discoveries.

Receipts prove identity of reports under declared runtime and encoding contracts.
Cross-runtime tissue acceptance is based on explicit portable observables and
tolerances, not automatic receipt equality. Accelerator residuals prove numerical
agreement within published gates. Q_f compares functional factors inside one
simulation. None of these establishes a physical theory, biological organism,
consciousness, or subjective experience.

## Planned sequence

1. **Python geometry reference** — complete.
2. **Rust core and CLI** — implemented in v2.1.0.
3. **WASM bridge and browser laboratory** — implemented in v2.2.0.
4. **WGSL schedule field and residual conformance** — implemented in v2.3.0.
5. **Native C ABI, C++17 consumer, and optional CUDA schedule adapter** — implemented in v2.4.0 and hardware-validation hardened in v2.4.1.
6. **Constitutional geometric tissue Python reference** — implemented in v2.5.0.
7. **Rust/WASM tissue conformance** — implemented in v2.7.0 from the sealed Python vectors.
8. **Full-path Frenet numerical research** — implemented in v2.6.0 as a separate f64/WASM/WGSL correctness surface; parallel acceleration remains future research.

Performance, compositional complexity, or anthropomorphic language never promotes
an adapter or simulation to scientific authority.

## Licence and citation

MPL-2.0. See `NOTICE.md` for attribution and `CITATION.cff` for citation metadata.
