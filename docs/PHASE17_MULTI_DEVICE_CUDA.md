# Phase 17 — physical multi-device CUDA path experiment

## Purpose

Phase 17 introduces `RSH-FRENET-MULTI-DEVICE-CUDA-V1`, the first RSH contract
that can accept physical execution across more than one CUDA device on one host.
It accelerates the already accepted deterministic shard-prefix composition
boundary; it does not define a new geometry model.

The implementation remains a draft until portable review is complete. A physical
claim can be accepted only after merge, through the protected trusted workflow,
from an exact commit already contained in `main`.

## Portable reference

`scripts/multi_device_cuda_reference.py` supplies a dependency-free f32 mirror
with logical device slots. It reproduces:

- the 4,097-point sealed path topology;
- 4,096 intervals partitioned into sixteen contiguous shards;
- the irregular 241-interval final shard;
- round-robin assignment across two logical devices;
- local inclusive quaternion-SE(3) prefixes;
- the four-pass exclusive shard-base scan;
- complete ordered path reconstruction and midpoint centring;
- comparison with sequential f32 and independent f64 Rodrigues references.

The portable profile deliberately records:

```text
actual_cuda_execution: false
actual_multi_device_execution: false
distributed_execution: false
universal_speedup_claim: false
geometry_receipt_authority: false
```

Sealed profile:

```text
conformance/frenet_multi_device_cuda_v1_4097.json
```

## Physical adapter

The CUDA implementation is split into three auditable surfaces:

```text
native/cuda/rsh_multi_device_kernels.cuh
native/cuda/rsh_multi_device_support.hpp
native/cuda/rsh_multi_device_path_cuda.cu
```

The adapter:

1. enumerates CUDA devices and validates a unique selected index list;
2. creates one nonblocking stream per selected device;
3. assigns contiguous shards round-robin;
4. computes interval transforms, local prefixes and reductions on the assigned
   device;
5. copies one 32-byte reduction per shard to the host;
6. computes the declared f32 exclusive shard bases on the host;
7. copies one 32-byte base per shard to its assigned device;
8. emits and reads back every 64-byte path record;
9. midpoint-centres the complete path;
10. records frame, schedule, coverage, centre and tail-integrity gates.

The local prefix kernel uses one CUDA thread per shard in V1. This is an explicit
policy choice: Phase 17 establishes physical multi-device composition and
complete evidence before making an intra-shard speedup claim.

## Device privacy

The sidecar records device name, selected index, compute capability, memory and a
domain-separated 64-bit redaction token. The raw CUDA UUID is read only to derive
that token and is never serialized or uploaded.

The token supports stable correlation inside this contract. It is not a
cryptographic receipt, hardware identity authority or geometry receipt.

## Evidence harness

`scripts/test_multi_device_cuda.py` performs:

- fresh `rsh-parallel-cli run` and `reconstruct` references from the tested
  commit;
- strict sidecar schema, topology, transfer and claim validation;
- parsing and validation of all seventeen CSV columns and every row;
- complete component comparison with both accepted references;
- three physical runs with byte-identical complete-path hashes;
- stable sidecar comparison outside timing and run-number fields;
- Compute Sanitizer memcheck and racecheck;
- deterministic accepted or rejected evidence packaging.

A CUDA process that launches and reads back data but fails a gate produces a
`REJECTED` audit. Completed failed execution is not silently discarded.

## CI and trusted execution

Portable pull-request validation:

```text
.github/workflows/multi-device-cuda.yml
```

It runs the logical-device mirror, validator regressions, sealed hashes, source
checks, CMake configuration and workflow-policy gates. It cannot make a physical
CUDA claim.

Protected physical workflow:

```text
.github/workflows/multi-device-cuda-hardware.yml
```

It is manual only and requires:

- repository `QSOLKCB/RSH` and branch `main`;
- `admin` or `maintain` dispatch permission;
- protected `rtx-hardware` environment approval;
- a trusted runner labelled `multi-gpu` and `rsh-trusted`;
- an exact full commit already contained in `main`;
- two to eight selected physical CUDA device indices;
- declared numeric CUDA architectures;
- complete readback, repeatability and required sanitizer evidence.

The workflow has no pull-request, issue, comment, fork or schedule trigger.

## Build and run

Portable evidence:

```bash
python3 -m unittest \
  tests.test_multi_device_cuda_reference \
  tests.test_multi_device_cuda_harness -v

python3 scripts/multi_device_cuda_reference.py \
  --verify-profile conformance/frenet_multi_device_cuda_v1_4097.json
```

Physical build on a suitable trusted host:

```bash
cmake -S native/cpp -B build/multi-cuda \
  -DCMAKE_BUILD_TYPE=Release \
  -DRSH_ENABLE_CUDA=ON \
  -DRSH_CUDA_ARCHITECTURES="120"

cmake --build build/multi-cuda \
  --target rsh-multi-cuda --parallel
```

Direct execution requires complete CSV evidence:

```bash
build/multi-cuda/rsh-multi-cuda \
  --devices 0,1 \
  --samples 4097 \
  --interval-width 257 \
  --output-csv multi-device-path.csv
```

## Acceptance boundary

A merged source file, successful portable workflow, CUDA compilation, device
enumeration or kernel launch is not enough. `actual_multi_device_execution` may
be true only when at least two selected CUDA devices execute assigned shards,
all streams synchronize, all path records are read back, every comparison gate
passes, repeated path hashes match and required sanitizer evidence passes.

Phase 17 never sets:

```text
distributed_execution: true
universal_speedup_claim: true
geometry_receipt_authority: true
```
