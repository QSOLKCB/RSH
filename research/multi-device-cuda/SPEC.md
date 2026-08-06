# RSH-FRENET-MULTI-DEVICE-CUDA-V1

## 1. Scope

This contract defines a physical, topology-bounded CUDA experiment on one host
with at least two CUDA device instances. It accelerates the accepted
`RSH-FRENET-SHARD-PREFIX-V1` composition policy and compares the complete result
with both `RSH-FRENET-PARALLEL-V1` and the f64 shard-prefix reconstruction.

It does not define distributed-node execution, geometry authority, or a universal
performance claim.

## 2. Sealed topology

The first profile uses:

```text
samples                  4097
intervals                4096
interval width            257
shards                     16
final shard intervals     241
minimum CUDA devices        2
maximum CUDA devices        8
streams per device           1
host count                   1
```

Shards are contiguous, ordered, complete, and assigned round-robin to the
selected device list. Device indices must be unique.

## 3. Local device phase

Each assigned CUDA device computes, in its declared nonblocking stream:

1. midpoint schedule values for every interval in the shard;
2. the f32 normalized-quaternion interval transform using the accepted
   `small-angle-sinc-polynomial-f32-v1` construction;
3. the sequential local inclusive SE(3) prefixes;
4. one 32-byte shard reduction.

The sequential local kernel is deliberate. The experiment tests physical
multi-device composition and evidence transfer before claiming an intra-shard
speedup.

## 4. Composition traffic

After all local kernels complete:

1. exactly one 32-byte reduction per shard is copied to the host;
2. the host applies `hillis-steele-exclusive-shard-se3-f32-v1` over immutable
   source passes;
3. exactly one 32-byte base per shard is copied to its assigned device;
4. no peer-to-peer device traffic is required by V1;
5. each device applies its base to every local prefix and emits its path records.

Complete final readback is mandatory evidence collection and is separate from
the reduction/base traffic allowed between composition phases.

## 5. Complete readback

The GPU emits all 4,097 records, including sample zero. Every record contains:

```text
position x/y/z
curvature
frame tangent x/y/z
torsion
frame normal x/y/z
normalised parameter p
frame binormal x/y/z
arc parameter s
```

The host assembles records in canonical sample order and subtracts the discrete
midpoint position. No missing, duplicated, stale, padded, or reordered record is
accepted.

## 6. Reference comparisons

The trusted harness produces fresh references from the exact tested commit:

```text
rsh-parallel-cli run
rsh-parallel-cli reconstruct
```

The complete CUDA CSV is compared component by component with both references.
The first profile retains the existing parallel f32 gates:

```text
position component       5e-4
frame component          5e-4
schedule component       1e-4
frame norm               5e-5
frame orthogonality      5e-5
```

No gate is tightened from a single hardware observation.

## 7. Device evidence and privacy

The raw sidecar records:

- detected and used device counts;
- selected CUDA indices and logical slots;
- device name, compute capability, and total memory;
- one domain-separated 64-bit redaction token derived from the device UUID;
- CUDA driver, runtime, compile version, and compiled architectures;
- complete shard-to-device/stream assignments;
- declared reduction, base, peer, and final-readback byte counts.

The raw UUID is never serialized. The redaction token is evidence correlation
metadata, not a cryptographic identity or geometry receipt.

## 8. Repeatability and sanitizers

The trusted profile requires:

- three complete executions;
- byte-identical complete path CSV hashes across all three runs;
- stable sidecar evidence outside timing and run-number fields;
- Compute Sanitizer memcheck;
- Compute Sanitizer racecheck;
- retention of rejection evidence when execution completes but a gate fails.

## 9. Trusted execution boundary

Portable pull-request CI executes only the dependency-free f32 logical-device
mirror, validator unit tests, source checks, and workflow-policy checks.

Physical execution is permitted only through a manual protected workflow that:

- runs on a labelled trusted multi-GPU host;
- verifies the actor has `admin` or `maintain` permission;
- checks out an exact full commit already contained in `main`;
- builds declared CUDA architectures;
- requires at least two selected CUDA devices;
- uploads redacted deterministic evidence;
- never runs on public pull requests.

## 10. Claims

Portable and unexecuted evidence must retain:

```text
actual_cuda_execution: false
actual_multi_device_execution: false
distributed_execution: false
universal_speedup_claim: false
geometry_receipt_authority: false
```

A trusted accepted artifact may set the first two fields true only after actual
kernel launch, synchronization, complete device readback, reference comparison,
repeatability, and sanitizer gates pass. Distributed execution, universal
speedup, and geometry authority remain false in V1.

## 11. Optional exact-cell payloads

Future profiles may carry `RSH-F32-SIERPINSKI-CELL-V1` or
`RSH-F32-SIERPINSKI-INVERSIVE-WITNESS-V1` records as sidecar payloads. They do not
change the Frenet interval, scan, assembly, path, or authority contracts.
