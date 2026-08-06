# RSH multi-device CUDA path experiment

`RSH-FRENET-MULTI-DEVICE-CUDA-V1` is a separately named, topology-bounded
hardware experiment over the accepted `RSH-FRENET-SHARD-PREFIX-V1` composition
boundary.

The first implementation targets one trusted host with at least two physical
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

## Mandatory portable non-claims

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
