# Physical multi-device CUDA evidence campaign

## Status

`RSH-FRENET-MULTI-DEVICE-CUDA-V1` has now passed the protected trusted-hardware
acceptance boundary on five physical observations spanning three RTX models,
two CUDA compute-capability generations, two- and four-device topologies, and
four independent hosts.

The machine-readable campaign record is:

```text
conformance/observed/multi-device-cuda/2026-08-06/campaign.json
```

This is an **observed noncanonical hardware record**. It does not change the
canonical geometry receipt, the portable conformance gates, or the scientific
model.

## Fixed source and profile

Every accepted observation used:

```text
tested commit       f590b4b251ad039e0b4c650fb29b7db3330708ef
contract            RSH-FRENET-MULTI-DEVICE-CUDA-V1
samples             4097
intervals           4096
interval width      257
shards              16
block size          128
streams/device      1
repeat runs         3
```

Each workflow required:

- a full commit already contained in `main`;
- protected `rtx-hardware` environment approval;
- a trusted self-hosted runner;
- complete 4,097-point readback;
- comparison with both accepted parallel and shard-prefix references;
- three repeatable complete-path hashes;
- Compute Sanitizer `memcheck` and `racecheck`;
- redacted device correlation metadata;
- literal false distributed, universal-speedup and geometry-authority claims.

## Accepted observations

| Workflow run | Selected hardware | CUDA arch | Mean end-to-end time | Result |
|---|---|---:|---:|---|
| [31096520169](https://github.com/QSOLKCB/RSH/actions/runs/31096520169) | 2× RTX 3090 | `86` | 38.253 ms | PASS |
| [31102590955](https://github.com/QSOLKCB/RSH/actions/runs/31102590955) | 4× RTX 4060 Ti | `89` | 23.261 ms | PASS |
| [31110426341](https://github.com/QSOLKCB/RSH/actions/runs/31110426341) | 2× RTX 4070 Ti SUPER | `89` | 29.478 ms | PASS |
| [31113168005](https://github.com/QSOLKCB/RSH/actions/runs/31113168005) | 2 of 4× RTX 4070 Ti SUPER | `89` | 29.392 ms | PASS |
| [31113751699](https://github.com/QSOLKCB/RSH/actions/runs/31113751699) | 4 of 4× RTX 4070 Ti SUPER | `89` | 30.467 ms | PASS |

Across all fifteen physical CUDA executions, the complete path SHA-256 was:

```text
2e69076c868cfdf7e77d904f60f3b3a5cf95fc411c48b75328aec2bd7ca49379
```

The maximum reference residuals were identical in every accepted audit:

```text
parallel frame       1.9477898010877848e-06
parallel position    1.9637626254009888e-06
parallel schedule    4.196258607258585e-08
shard frame          1.9477898026698526e-06
shard position       1.9637626329505053e-06
shard schedule       4.196258607258585e-08
```

Every observation reported:

```text
status                         PASS
actual_cuda_execution          true
actual_multi_device_execution  true
single_host_execution          true
complete_path_readback         true
distributed_execution          false
universal_speedup_claim        false
geometry_receipt_authority     false
raw_device_uuid_published      false
```

## Controlled same-host 2 → 4 comparison

Runs `31113168005` and `31113751699` used the same four-card RTX 4070 Ti SUPER
host. The redacted correlation tokens for CUDA indices `0` and `1` match across
both artifacts.

| Selected devices | Individual runs (ms) | Mean |
|---|---|---:|
| `0,1` | 29.259772, 29.603148, 29.314301 | 29.392407 |
| `0,1,2,3` | 30.364491, 30.391641, 30.645536 | 30.467223 |

For this fixed 4,097-point, 16-shard profile, selecting four devices was:

```text
1.074816 ms slower
3.656780% slower
two/four mean-time ratio = 0.964722
```

The correct conclusion is narrow:

> On this host and profile, increasing selected RTX 4070 Ti SUPER devices from
> two to four preserved exact deterministic output but did not improve
> end-to-end execution time.

This is useful diagnostic timing evidence of the current workload's scaling
knee, not a failed correctness result. The workflow did not use a separate
warm-up/measurement benchmark protocol, so `speedup_claim` remains false.

## Why eight devices and NVLink are not claimed

The current V1 adapter does not use peer-to-peer device traffic:

```text
inter_device_peer_bytes  0
```

Its composition boundary is host mediated:

1. each device computes local shard prefixes and reductions;
2. one 32-byte reduction per shard is copied device-to-host;
3. the f32 shard-prefix scan runs on the host;
4. one 32-byte base per shard is copied host-to-device;
5. every final path record is copied device-to-host.

The local prefix kernel also intentionally uses one CUDA thread per shard. V1
was designed to establish physical multi-device correctness and complete
evidence before making an intra-shard speedup claim.

The same-host 2 → 4 result therefore suggests that an eight-device run of this
unchanged fixed profile is unlikely to improve end-to-end time. It does **not**
prove an eight-device result, because no accepted eight-device execution was
performed.

NVLink would not automatically improve V1: there are zero peer bytes for NVLink
to carry. A future peer-aware implementation would need a separately reviewed
policy, such as GPU-side shard composition, CUDA peer access or collectives,
larger profiles, more useful work per shard, and a fresh timing/evidence
campaign.

## Artifact preservation

The full Actions ZIPs contain complete CSV readback, sidecars, reference reports,
sanitizer output, build logs and internal `SHA256SUMS.txt` files. Actions
artifacts are retention-bound.

The checked-in campaign record therefore preserves, for every observation:

- workflow and artifact identifiers;
- run and artifact URLs;
- archive size and SHA-256;
- the original `audit.json` SHA-256 and complete-path CSV SHA-256;
- selected CUDA architecture and device indices;
- accepted claim fields, redacted device metadata, repeat timings and sanitizers;
- same-host correlation evidence;
- controlled comparison calculations.

This does not pretend that a digest is a substitute for the original bytes. The
archive digest and internal checksum map make any separately preserved copy of
the original artifact independently verifiable.

## Revalidation

Run:

```bash
python3 scripts/verify_multi_device_cuda_campaign.py
python3 -m unittest tests.test_multi_device_cuda_campaign -v
```

The verifier checks the campaign schema, fixed commit and contract, all accepted
claim boundaries, repeated path identity, the sealed campaign residual vector,
sanitizer status, archive/audit/path SHA-256 formatting, observed topology, and
the controlled same-host comparison.
