# Phase 12 — Deterministic shard-prefix path reconstruction

## Status

**Local deterministic reconstruction implemented.** This phase proves that a
complete `RSH-FRENET-PARALLEL-V1` path can be partitioned into contiguous shard
work units, reconstructed through an ordered prefix over shard reductions, and
read back as the same declared f64 path within the published tolerance.

It does not claim multi-device, networked, or distributed execution.

## Contract

```text
RSH-FRENET-SHARD-PREFIX-V1
```

The shard contract is separate from:

- the canonical geometry contract;
- `RSH-FRENET-NUMERICS-V1`;
- `RSH-FRENET-PARALLEL-V1`;
- the WebGPU and CUDA hardware evidence surfaces.

It consumes the same midpoint Rodrigues interval definition and compares the
fully reconstructed path with the accepted native f64 parallel path.

## Two-level prefix construction

For local interval transforms

```text
L_0, L_1, ..., L_(N-2)
```

the interval range is divided into ordered contiguous shards. Each shard emits:

```text
start_interval
end_interval_exclusive
local inclusive prefixes
local reduction
non-authoritative deterministic fingerprint
```

### Local prefix policy

```text
sequential-local-inclusive-se3-v1
```

For one shard containing `L_a ... L_b`, the local prefixes are:

```text
L_a
L_a ⊗ L_(a+1)
...
L_a ⊗ ... ⊗ L_b
```

The final local prefix is the shard reduction.

### Shard prefix policy

```text
hillis-steele-exclusive-shard-se3-v1
```

Shard reductions are scanned with the same immutable-source doubling order used
by the accepted parallel contract. The inclusive scan is shifted by one shard to
produce the exclusive base transform for each shard:

```text
B_0 = identity
B_1 = R_0
B_2 = R_0 ⊗ R_1
...
```

### Assembly policy

```text
ordered-base-compose-local-prefix-v1
```

Every global interval prefix is reconstructed as:

```text
B_shard ⊗ local_prefix
```

An identity prefix is inserted for sample zero, producing exactly one prefix for
every requested sample. The complete result is then converted to the ordinary
parallel point representation and centred by moving the exact discrete midpoint
to the origin.

## Shard evidence bundle

`rsh-parallel reconstruct` can emit three files:

```text
report JSON
shard bundle JSON
complete path CSV
```

The bundle uses:

```text
RSH-FRENET-SHARD-BUNDLE-V1
RSH-FRENET-SHARD-WORK-V1
```

Each shard includes a domain-separated deterministic FNV-1a 64-bit fingerprint.
That fingerprint catches accidental mutation, truncation, or reordering inside
this local research workflow. It is deliberately named a fingerprint rather
than a receipt:

```text
fnv1a64-domain-separated-evidence-only-v1
```

It is not cryptographic provenance and does not create geometry authority.

## Validation

The sealed profile is:

```text
conformance/frenet_shard_prefix_v1_4097.json
```

It uses:

```text
4,097 samples
4,096 intervals
257 intervals per shard
16 shards
4 shard-prefix doubling passes
241 intervals in the irregular final shard
```

The implementation checks:

- complete ordered interval coverage;
- monotonically indexed shards;
- exact local-prefix count per shard;
- finite transforms;
- local tail/reduction agreement;
- shard and manifest fingerprints;
- complete reconstructed prefix count;
- full position, frame, curvature, and torsion agreement with
  `RSH-FRENET-PARALLEL-V1`;
- midpoint centering;
- frame norm and orthogonality;
- schedule bounds;
- deterministic replay;
- rejection of missing, reordered, tampered, or authority-promoting shards.

The maximum full-path component residual must remain no greater than `1e-11`.

## Commands

```bash
cargo run --locked -p rsh-parallel-cli -- \
  reconstruct \
  --samples 4097 \
  --interval-width 257 \
  --json shard-prefix-report.json \
  --csv shard-prefix-path.csv \
  --shards-json shard-prefix-bundle.json

node scripts/test_shard_prefix_reconstruction.mjs \
  conformance/frenet_shard_prefix_v1_4097.json \
  shard-prefix-report.json \
  shard-prefix-bundle.json \
  shard-prefix-path.csv
```

## What this unlocks

The repository now has the deterministic host-side algorithm needed before a
multi-device experiment:

1. independent contiguous shard work units;
2. local prefixes and reductions;
3. ordered shard-prefix composition;
4. application of shard bases to local paths;
5. complete path assembly and centering;
6. full comparison with the accepted f64 parallel contract.

A future multi-device adapter still needs actual device assignment, transfer,
synchronization, failure handling, complete readback, residual evidence, and
replayable hardware metadata.

## Evidence boundary

Every report preserves:

```text
actual_local_shard_execution: true
actual_multi_device_execution: false
distributed_execution: false
speedup_claim: false
geometry_receipt_authority: false
```

Local shard reconstruction proves composition correctness. It does not prove a
network, multiple physical devices, acceleration, or a new scientific oracle.
