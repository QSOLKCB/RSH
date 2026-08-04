# RSH v2.4.1 — CUDA validation hardening

RSH v2.4.1 converts the successful external RTX 5060 Ti audit into repeatable,
hardware-aware repository tooling. The numerical model and its 2.0.0 contract do
not change.

## Added

- configurable CUDA architecture selection through
  `RSH_CUDA_ARCHITECTURES`;
- runtime controls for CUDA samples, block size, threshold, device, and repeat
  identifier;
- richer CUDA provenance including device UUID, driver/runtime API versions,
  compile version, compiled architectures, grid size, and host pointer width;
- a `1e-6` diagnostic observation band while retaining the `1e-4` hard gate;
- `scripts/cuda_preflight.sh`, a non-mutating environment readiness report;
- `scripts/test_cuda.py`, a strict sidecar, repeatability, and sanitizer harness;
- `scripts/package_evidence.py`, a deterministic evidence packer without
  recursive self-hashes;
- unit tests for sidecar validation, repeatability comparison, and deterministic
  evidence packaging;
- a dispatch-only self-hosted CUDA workflow;
- a checked-in noncanonical RTX 5060 Ti / sm_120 observation;
- complete CUDA validation and known-toolchain documentation.

## Observed hardware result

The external follow-up audit executed the actual CUDA kernel at commit
`6ab304c0ac7c541c15ba7ada935bc0c4ae8da950`:

```text
GPU                       NVIDIA GeForce RTX 5060 Ti
CUDA / nvcc               13.1.115
Compute capability        12.0
Grid                      4096 samples
Block                     128 threads
CUDA maximum residual     4.0915928645191e-08
Published hard gate       1.0e-04
Repeatability             3 matching selected outputs
Compute Sanitizer         0 memcheck errors, 0 race hazards
```

The result remains an adapter observation, not a geometry receipt and not a
universal residual golden value.

## Security boundary

The hardware GitHub workflow uses only `workflow_dispatch` and a labelled
self-hosted runner. It is intentionally absent from `pull_request` triggers so
untrusted public PR code cannot execute on private GPU hardware.

## Compatibility note

The observed Ubuntu 26.04/glibc 2.43 environment required a temporary local CUDA
13.1 header compatibility adjustment. RSH does not modify vendor headers or
system drivers. The preflight and documentation make this limitation explicit
instead of hiding it inside an agent transcript.
