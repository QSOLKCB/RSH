# CUDA validation and hardware evidence

RSH treats CUDA as an optional schedule accelerator. The Rust core remains the
source of the f64 κ/τ oracle, geometry report, and receipt. A CUDA result is
accepted only as an adapter-specific residual sidecar.

## Three different claims

These statements are deliberately separate:

1. **CUDA source exists** — the repository contains a kernel.
2. **CUDA compiled** — a compatible toolkit accepted the source for a declared
   architecture.
3. **CUDA executed** — a device was selected, memory was allocated, the kernel
   launched and synchronized, output was read back, and residual validation
   passed.

Only the third case may report `actual_cuda_execution: true`.

## Preflight

Run the non-mutating host check first:

```bash
sh scripts/cuda_preflight.sh
```

It reports the detected operating system, glibc, CMake, C++ and Rust toolchains,
`nvcc`, NVIDIA devices, compute capability, and Compute Sanitizer availability.
It does not install packages, modify drivers, or patch toolkit headers.

## Build

The CMake cache option is empty by default and therefore preserves the CUDA
compiler default. For an adapter-specific hardware run, select `native`
explicitly:

```bash
cmake -S native/cpp -B build/cuda \
  -DCMAKE_BUILD_TYPE=Release \
  -DRSH_ENABLE_CUDA=ON \
  -DRSH_CUDA_ARCHITECTURES=native
cmake --build build/cuda --target rsh-cuda --parallel
```

The `native` architecture value requires CMake 3.24 or newer. Older supported
CMake releases must use an explicit numeric architecture instead:

```bash
-DRSH_CUDA_ARCHITECTURES=120
```

An explicit value is also preferable for a pinned reproducibility run. The CMake
configure log prints the effective architecture and the CUDA sidecar records the
compiled architecture string.

## Runtime controls

The sealed defaults remain 4096 samples, 128 threads per block, device zero, and
a `1e-4` residual gate:

```bash
build/cuda/rsh-cuda \
  --samples 4096 \
  --block-size 128 \
  --threshold 1e-4 \
  --device 0
```

`--repeat-run` adds an audit run identifier without changing the numerical
calculation.

## Automated hardware test

```bash
python3 scripts/test_cuda.py \
  --executable build/cuda/rsh-cuda \
  --cpu-reference build/cuda/rsh-cpp \
  --profile conformance/cuda_schedule_v1_4096.json \
  --runs 3 \
  --sanitizers auto \
  --output artifacts/cuda-hardware
```

The harness:

- executes strict-JSON CUDA sidecars;
- checks device and toolchain provenance;
- validates every residual against the sealed profile;
- compares selected output fields across repeated runs;
- optionally executes Compute Sanitizer memcheck and racecheck;
- records a manifest without attempting a recursive self-hash.

Exit codes distinguish invalid input, unavailable CUDA, malformed output,
residual failure, repeatability failure, and sanitizer failure.

Package the resulting evidence deterministically:

```bash
python3 scripts/package_evidence.py \
  artifacts/cuda-hardware \
  artifacts/RSH-cuda-hardware.zip
```

The manifest excludes itself. The final ZIP receives a separate `.sha256`
receipt.

## Residual policy

The hard acceptance gate remains:

```text
maximum residual <= 1e-4
```

RSH also reports a diagnostic observation band of `1e-6`. A result above that
band but inside `1e-4` remains accepted while being labelled
`PASS_WITH_WARNING`. One hardware observation is not enough evidence to tighten
the universal gate.

## Observed RTX 5060 Ti result

The checked-in observation
`conformance/observed/cuda_sm120_rtx5060ti_cuda13_1.json` records an independent
execution of the Phase 5 adapter:

```text
GPU                       NVIDIA GeForce RTX 5060 Ti
Compute capability        12.0 / sm_120
CUDA toolkit              13.1.115
Samples / block size      4096 / 128
CPU f32 maximum residual  4.6082406834901946e-08
CUDA maximum residual     4.0915928645191e-08
Hard gate                 1.0e-04
Repeated runs             3, identical selected outputs
Memcheck                   0 errors
Racecheck                  0 hazards
```

This is an observed, noncanonical result tied to one commit, GPU, driver, toolkit,
and host environment. The stable device UUID is intentionally not copied into
the public repository.

## Known toolchain issue from the observation

The audit host used glibc 2.43 with a user-local CUDA 13.1 toolkit. Compilation
required a local compatibility adjustment to CUDA's `math_functions.h`
`rsqrt`/`rsqrtf` exception declarations. That adjustment was made inside the
temporary toolkit extraction, not in RSH source and not in the system driver.

RSH does not automate or recommend patching vendor headers. On a similar host:

1. prefer a CUDA toolkit officially supporting the distribution and glibc;
2. consult current NVIDIA release notes;
3. use a container or supported build image where practical;
4. record any local workaround as environment provenance.

## Manual GitHub hardware workflow

`.github/workflows/cuda-hardware.yml` is dispatch-only and targets a deliberately
labelled self-hosted runner. It is not triggered by pull requests. Public
repositories should never expose a self-hosted GPU runner to arbitrary PR code.

## Authority boundary

A passing CUDA sidecar confirms numerical agreement of the sampled f32 schedule
with the Rust FFI f64 oracle under the recorded adapter and toolchain. It does
not validate a physical theory, execute the Frenet–Serret integrator, or replace
the canonical geometry receipt.
