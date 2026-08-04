# Phase 5 — Native C ABI, C++ consumer, and optional CUDA schedule adapter

## Goal

Expose the verified Rust implementation to native consumers without creating a
second geometry model. Phase 5 adds a versioned C ABI, a dependency-free C++17
command-line consumer, and an optional CUDA schedule residual executable.

The Rust core remains authoritative for geometry, frame integration, centre
normalisation, verification, JSON reports, and SHA-256 receipts.

## Architecture

```text
Python oracle
      │
      ▼
   rsh-core f64 ───────────────► native Rust / WASM geometry evidence
      │
      ▼
   rsh-ffi ABI v1
      │
      ├────────► C++17 consumer ─────► report / JSON / schedule CSV
      │
      └────────► f64 schedule oracle ─► optional CUDA f32 kernel
                                           │
                                           ▼
                                  adapter residual sidecar
```

Neither C++ nor CUDA contains the Frenet–Serret integrator. The C++ executable
calls `rsh_ffi_verify`, which calls `rsh-core::build_and_verify`. The CUDA path
receives an f64 κ/τ schedule from `rsh_ffi_schedule`, evaluates the same controls
in f32 on the selected device, and compares every output point with that oracle.

## ABI v1

The public header is `include/rsh_ffi.h`. ABI v1 uses fixed-width integers,
`double` values, explicit structure sizes, and an ABI version field.

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

Status codes are:

| Code | Meaning |
|---:|---|
| 0 | verified report passed, or schedule completed |
| 1 | a report was produced but a geometry contract failed |
| 2 | input, layout, or runtime request was rejected |
| 3 | a Rust panic was contained at the FFI boundary |

Rust allocations cross the boundary only as opaque owned handles. The consumer
must release them through the matching ABI function. No caller is asked to free
Rust memory with `free`, `delete`, or a foreign allocator.

## Sealed layout

`conformance/ffi_v1_129.json` fixes the first ABI layout on 64-bit targets:

```text
RshConfigV1         = 56 bytes
RshSummaryV1        = 232 bytes
RshSchedulePointV1  = 32 bytes
```

The header contains matching C++ `static_assert` checks, while the Rust crate
exports runtime size probes. Structures include `struct_size` and `abi_version`
so later additive revisions can reject incompatible callers cleanly.

## C++17 consumer

The C++ adapter is built with CMake:

```bash
cmake -S native/cpp -B build/native -DCMAKE_BUILD_TYPE=Release
cmake --build build/native
ctest --test-dir build/native --output-on-failure
```

Example commands:

```bash
build/native/rsh-cpp info
build/native/rsh-cpp verify --samples 129 --json rsh_cpp_report.json
build/native/rsh-cpp schedule --samples 4096 --csv rsh_schedule.csv
build/native/rsh-cpp cuda-reference --samples 4096 --threshold 1e-4
```

`cuda-reference` is an explicitly labelled CPU f32 arithmetic reference for the
optional CUDA kernel. It is useful in ordinary CI, but it never claims actual
CUDA execution.

## Optional CUDA execution

A machine with a CUDA toolkit and supported NVIDIA device may build the adapter:

```bash
cmake -S native/cpp -B build/cuda \
  -DCMAKE_BUILD_TYPE=Release \
  -DRSH_ENABLE_CUDA=ON
cmake --build build/cuda --target rsh-cuda
build/cuda/rsh-cuda
```

The executable records the CUDA device name, compute capability, sample count,
block size, f32 residuals, and published threshold. Its output schema is
`RSH-CUDA-RESIDUAL-SIDECAR-V1`.

Actual CUDA execution is claimed only by that binary after a successful kernel
launch and device-to-host readback. The portable C++ arithmetic reference uses
`actual_cuda_execution: false`.

## Residual boundary

`conformance/cuda_schedule_v1_4096.json` publishes:

```text
grid samples       = 4096
CUDA block size    = 128
precision          = f32
residual threshold = 1e-4
```

A passing CUDA schedule residual does not create or replace a geometry receipt.
It validates only the sampled κ/τ field against the f64 Rust FFI oracle.

## CI acceptance

GitHub Actions:

1. formats, lints, and tests `rsh-ffi` as part of the Rust workspace;
2. builds the Rust ABI and C++17 consumer through CMake;
3. runs CTest commands for info, geometry verification, schedule export, and the
   f32 CUDA arithmetic reference;
4. executes `scripts/test_cpp_ffi.py` against the sealed ABI and CUDA profiles;
5. requires the C++ JSON report to retain the canonical native Rust receipt;
6. checks entry, exit, and centre residuals against the existing golden vectors;
7. validates the optional CUDA source without pretending that hosted CI executed
   an NVIDIA device kernel.

## Deferred work

A CUDA Frenet–Serret integrator remains out of scope. Such an implementation
would need a separately versioned integration scheme, re-orthonormalisation
policy, path-level vectors, frame residual limits, compiler flags, GPU model,
driver version, and adapter-specific evidence. Phase 5 deliberately provides
interop and schedule acceleration without duplicating the authoritative model.
