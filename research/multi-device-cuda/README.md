# RSH multi-device CUDA path experiment

`RSH-FRENET-MULTI-DEVICE-CUDA-V1` is a separately named, topology-bounded
hardware experiment over the accepted `RSH-FRENET-SHARD-PREFIX-V1` composition
boundary.

The implementation targets one trusted host with two to eight selected physical
CUDA devices. It does not claim distributed-node execution.

## Required execution phases

1. enumerate physical CUDA devices and record redacted device metadata;
2. partition the complete interval range into deterministic contiguous shards;
3. assign every shard to one declared device and one stream;
4. compute interval transforms, local inclusive prefixes, and one reduction per
   shard on the assigned device;
5. transfer only shard reductions to the host composition phase;
6. compute the declared ordered exclusive shard bases;
7. transfer each required base to its assigned device;
8. apply the base to every local prefix;
9. read back every position and frame component in canonical interval order;
10. compare the complete path with the accepted single-device parallel and
    shard-prefix references;
11. preserve rejected evidence if execution completes but any gate fails.

Final complete readback is evidence collection and is distinct from the
reduction/base traffic permitted between composition phases.

## Physical acceptance

The protected hardware workflow has produced five accepted observations on:

```text
2× RTX 3090
4× RTX 4060 Ti
2× RTX 4070 Ti SUPER
2 of 4× RTX 4070 Ti SUPER
4 of 4× RTX 4070 Ti SUPER
```

All fifteen physical repeat executions produced the same complete-path SHA-256,
passed both reference comparisons, completed full readback, and passed Compute
Sanitizer memcheck and racecheck.

The checked-in observed campaign is:

```text
conformance/observed/multi-device-cuda/2026-08-06/campaign.json
```

See [the physical evidence report](../../docs/MULTI_DEVICE_CUDA_EVIDENCE.md).

## Controlled scaling observation

A same-host RTX 4070 Ti SUPER comparison selected two devices and then all four
devices while holding the source commit, host, installed GPU set, CUDA
architecture, profile and workflow fixed.

Four selected devices preserved exact deterministic output but were about
`3.656780%` slower than two selected devices for the fixed 4,097-point,
16-shard profile. This is a local diagnostic timing observation, not a published speedup
benchmark or universal performance claim.

V1 reports:

```text
inter_device_peer_bytes: 0
```

Reductions and bases pass through the host, so NVLink or peer-to-peer transport
was not used. An NVLink-aware or GPU-side composition design would be a new
implementation policy requiring separate review and fresh evidence.

## Mandatory portable non-claims

Portable CI and logical-device evidence retain:

```text
actual_cuda_execution: false
actual_multi_device_execution: false
distributed_execution: false
universal_speedup_claim: false
geometry_receipt_authority: false
```

Only an accepted trusted run from an exact commit already contained in `main`,
on a host exposing at least two physical CUDA devices, may set
`actual_cuda_execution: true` and `actual_multi_device_execution: true`.

No accepted observation sets:

```text
distributed_execution: true
universal_speedup_claim: true
geometry_receipt_authority: true
```
