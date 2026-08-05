# RSH architecture and authority map

RSH is a multi-runtime geometry and tissue research repository. Its architecture
separates readable reference behaviour, native implementations, accelerator
research, browser laboratories, hardware adapters, and evidence records.

## Core rule

A later implementation becomes acceptable by reproducing a declared contract
within its published gates. It does not become the scientific oracle merely
because it is faster, lower-level, parallel, or executed on specialized hardware.

```text
canonical reference
      ↓ declared contract
native implementation
      ↓ cross-runtime conformance
WASM / FFI / accelerator adapter
      ↓ actual execution + readback + residual gates
observed evidence sidecar
```

Receipts prove deterministic evidence identity for a particular runtime and
serialization path. They do not prove that a physical interpretation is true.

## Runtime layers

### Python reference — `src/rsh/`

Responsibilities:

- readable canonical geometry behaviour;
- validation and bounded configuration;
- canonical JSON and domain-separated receipts;
- constitution and tissue reference;
- CLI exports and evidence generation.

Entry points:

```text
rsh
python rsh_runner.py
```

The package uses a `src/` layout and should normally be installed with
`python -m pip install -e .`.

### Rust geometry — `crates/rsh-core`, `crates/rsh-cli`

Responsibilities:

- native implementation of the geometry contract;
- deterministic report and coordinate conformance;
- reusable core for WASM and FFI adapters.

Receipt identity and coordinate conformance are reported separately.

### Geometry WASM — `crates/rsh-wasm`

Responsibilities:

- raw bounded ABI over the shared Rust core;
- compiled browser execution;
- no second JavaScript geometry integrator.

The browser must validate output pointer/length spans before reading linear
memory.

### Full-path numerical research — `crates/rsh-numerics*`

Contract:

```text
RSH-FRENET-NUMERICS-V1
lie-midpoint-so3-projected-v1
```

Responsibilities:

- f64 midpoint Lie-group frame transport;
- midpoint tangent position quadrature;
- modified Gram–Schmidt after each full step;
- path-level evidence for accelerator comparison.

This surface is deliberately separate from the canonical geometry contract.

### Parallel Frenet research — `crates/rsh-parallel*`

Contract:

```text
RSH-FRENET-PARALLEL-V1
midpoint-rodrigues-se3-v1
hillis-steele-inclusive-se3-v1
```

Responsibilities:

- local midpoint SE(3) interval transforms;
- deterministic inclusive prefix scan;
- sequential-fold equivalence checks;
- complete centred path generation;
- ordered segment summaries for later multi-device research;
- native, WASM, WGSL, and browser benchmark surfaces.

The v2.6 projected recurrence is not silently parallelized. Per-step
Gram–Schmidt is nonlinear and cannot be inserted into an associative scan without
creating a different numerical contract.

Segment-summary validation requires an expected full interval count. The complete
path builder also compares the merged reduction with the expected final
sequential transform. Local summaries alone do not prove distributed execution.

### Tissue — `src/rsh/tissue.py`, `crates/rsh-tissue*`

Contract:

```text
RSH-TISSUE-CONTRACT 1.0.0
```

Responsibilities:

- geometry-seeded deterministic cells;
- ring/chord graph construction;
- phase coupling and binding diffusion;
- neighbour prediction and shared-centroid normalization;
- bounded `Q_f` functional cohesion metrics;
- chained tick and report evidence;
- Python, native Rust, and compiled WASM conformance.

`Q_f` is functional. It is not a measure of consciousness, life, sentience,
qualia, or subjective awareness.

### C ABI and C++ — `crates/rsh-ffi`, `native/cpp`

Responsibilities:

- versioned fixed-layout C ABI over `rsh-core`;
- opaque Rust-owned buffers with matching release functions;
- panic containment and explicit status codes;
- dependency-light C++17 consumer;
- runtime layout probes and 64-bit layout assertions.

C++ is a consumer, not a separate geometry oracle.

### CUDA — `native/cuda`

Current responsibilities:

- optional schedule-field execution;
- real device metadata and residual readback when hardware executes;
- portable CPU f32 arithmetic reference in ordinary CI;
- evidence packaging and optional Compute Sanitizer checks.

The CPU reference is not actual CUDA. CUDA schedule execution is not full
Frenet path integration and cannot issue geometry receipts.

### WebGPU and browser — `web/`

Laboratories:

```text
index.html       canonical geometry and schedule residual lab
frenet.html      sequential full-path numerical research
parallel.html    multi-pass parallel prefix research and benchmark
 tissue.html     Rust/WASM tissue laboratory
```

WGSL backends must:

- use the declared parameter-buffer layout;
- execute on a real adapter before setting actual-execution fields;
- read back complete output buffers;
- compare every required observable with the Rust/WASM reference;
- preserve the CPU/WASM result when WebGPU is unavailable or fails;
- export sidecars only after all gates pass.

### NPU profile — `conformance/npu_tier2_v1.json`

The Tier 2 NPU profile currently defines evidence gates and fallback policy. It
is not a vendor driver binding and is not proof of NPU execution.

## Evidence hierarchy

| Evidence | What it proves | What it does not prove |
|---|---|---|
| Build success | Source compiled | Code executed correctly |
| Unit test pass | Tested local behaviour | Cross-runtime identity |
| Conformance pass | Declared observables meet gates | Scientific truth |
| Receipt match | Same-runtime evidence identity | Physical interpretation |
| Hardware sidecar | Recorded device executed and returned data | Universal behaviour |
| Benchmark sidecar | Observed timing under recorded scope | Universal speedup |

## Versioning boundaries

Keep these distinct:

- software release version;
- canonical geometry contract version;
- tissue contract version;
- WASM ABI version;
- FFI ABI version;
- numerical research contract;
- parallel research contract;
- sidecar schema version;
- conformance-profile schema version.

A software release may advance without changing a mathematical contract.
Conversely, a changed numerical policy requires a separately named contract even
when the public software version changes only once.

## Fallback policy

Fallback is part of the architecture, not an error to hide.

- WebGPU unavailable → keep the verified Rust/WASM result.
- CUDA unavailable → report hardware validation as blocked; keep portable tests.
- NPU unavailable → keep f64 CPU/WASM fallback.
- Sidecar exceeds a gate → reject the sidecar; do not discard the reference result.
- Optional tool missing → report `BLOCKED BY ENVIRONMENT`; do not manufacture a
  successful hardware claim.

## Security and bounds

All boundaries must validate before work begins:

- integer type and boolean rejection;
- minimum, maximum, odd/even, and total-work limits;
- allocation sizes and multiplication overflow;
- FFI struct version and layout;
- pointer and length spans;
- WASM linear-memory ranges;
- JSON schema and complete required fields;
- GPU dispatch and buffer dimensions;
- ordered shard ranges and complete expected coverage;
- deterministic audit-chain length and terminal identity.

## Where to start

- AI agents: [`AGENTS.md`](AGENTS.md)
- commands: [`COMMANDS.md`](COMMANDS.md)
- tests: [`TESTING.md`](TESTING.md)
- active programme: [`ROADMAP.md`](ROADMAP.md)
- historical phases: [`docs/ROADMAP.md`](docs/ROADMAP.md)
