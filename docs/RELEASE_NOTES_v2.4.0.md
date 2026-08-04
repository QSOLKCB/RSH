# RSH v2.4.0 — Native ABI and CUDA Adapter Boundary

RSH v2.4.0 adds a versioned native interoperability layer without forking the
scientific implementation. C and C++ consumers now call the same verified Rust
core used by the native CLI and WebAssembly laboratory. CUDA remains an optional
f32 schedule accelerator checked against an f64 oracle supplied through that ABI.

## Added

- `rsh-ffi`, a Rust `cdylib`/`staticlib`/`rlib` exposing ABI v1;
- `include/rsh_ffi.h`, with fixed-layout C structures and C++ `static_assert`s;
- panic containment and thread-local error reporting at the foreign-function
  boundary;
- explicit ownership handles and matching release functions for Rust-allocated
  JSON and schedule buffers;
- a dependency-free C++17 command-line consumer;
- CMake integration that builds the Rust ABI before linking the C++ adapter;
- an optional CUDA κ/τ schedule kernel with adapter-specific readback residuals;
- a portable CPU f32 arithmetic reference that never claims CUDA execution;
- sealed native and CUDA schedule profiles;
- executable Python conformance checks for the compiled C++ consumer;
- a dedicated GitHub Actions job for the ABI, CMake, CTest, and adapter profiles.

## Native ABI commands

```bash
cmake -S native/cpp -B build/native -DCMAKE_BUILD_TYPE=Release
cmake --build build/native
build/native/rsh-cpp verify --samples 129 --json rsh_cpp_report.json
build/native/rsh-cpp schedule --samples 4096 --csv rsh_schedule.csv
```

## Optional CUDA command

```bash
cmake -S native/cpp -B build/cuda \
  -DCMAKE_BUILD_TYPE=Release \
  -DRSH_ENABLE_CUDA=ON
cmake --build build/cuda --target rsh-cuda
build/cuda/rsh-cuda
```

The optional CUDA sidecar reports the selected device, compute capability,
4096-point grid, block size, f32 residuals, and the published `1e-4` threshold.

## Authority boundary

- Python remains the readable scientific oracle.
- `rsh-core` remains the geometry and receipt authority.
- The C ABI is an adapter over `rsh-core`, not another integrator.
- The C++ executable consumes the ABI and does not reproduce the equations.
- CUDA evaluates only the κ/τ schedule field and receives its f64 comparison
  oracle from Rust.
- Neither a C++ report wrapper nor a CUDA residual sidecar replaces the canonical
  geometry report.

## Conformance

The v2.4.0 suite requires:

- ABI version and fixed structure sizes to match `ffi_v1_129.json`;
- the compiled C++ adapter to reproduce the 129-sample entry, centre, and exit
  observables within the existing tolerances;
- the C++ JSON report to retain the native Rust receipt
  `9cccdea9db0e0cb4c30accab275a672efb9c69fed022f5087f273a87aa28f253`;
- the 4096-point f32 arithmetic reference to remain below `1e-4` against the Rust
  FFI f64 schedule;
- actual CUDA execution to be labelled only when a device kernel was launched,
  synchronized, and read back successfully.

## Not included

A second C++ geometry implementation and a CUDA Frenet–Serret integrator are
intentionally absent. Either would require a separately versioned numerical
contract and stronger path-level evidence rather than merely another fast code
path.
