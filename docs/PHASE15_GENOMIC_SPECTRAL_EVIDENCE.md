# Phase 15 — deterministic genomic spectral evidence

Phase 15 inserts a biology-aware reference workload before the multi-device CUDA
experiment.

## Contract

```text
RSH-ETQ-GENOMIC-SPECTRAL-V1
```

It adds bounded single-record FASTA and strict VCF 4.5 SNV handling, GA4GH-style
sequence identity, 303-base genomic windows, exact k-mer surfaces, integer
period-3 Voss power, exact `[1,-2,1]` SCL energy, ETQ position addresses,
frame-relative fixture comparisons, deterministic MIDI, matching Python and
JavaScript implementations, and canonical evidence artifacts.

## Review hardening

The completed implementation additionally enforces:

- FASTA, sequence, VCF, window-count, and variant-count limits before large allocations;
- one exact VCF 4.5 header and exactly eight columns;
- unique SNV positions and one containing window per variant;
- frame-origin validation even when no variants are supplied;
- canonical report bytes that reproduce the manifest hash exactly;
- full conformance schema, contract, expected-field, and claim validation;
- text-node browser rendering for user-controlled identifiers;
- stale-artifact cleanup after rejected analyses;
- tempo-correct browser playback and replay cancellation;
- portable tests for malformed, oversized, overlapping, and authority-promoting inputs.

The sealed report, window CSV, variant CSV, and MIDI hashes remain unchanged.

## Why before multi-CUDA

The window records create a larger, independent, naturally partitionable payload
whose output is sealed by a readable CPU reference. A later CUDA contract can
partition windows or variants, compare every returned record to this reference,
and preserve ordered reconstruction using the accepted shard-prefix discipline.

## Proposed accelerator boundary

A later `RSH-ETQ-GENOMIC-SPECTRAL-CUDA-V1` may accelerate only declared window or
SNV metric kernels and must publish source identity, device/toolchain metadata,
complete output readback, per-record comparison, deterministic shard coverage,
sanitizer evidence, and repeatability. Multi-device execution becomes true only
after a protected physical run on at least two distinct CUDA devices.

## Authority boundary

This phase is computational feature extraction and sonification. It does not
perform clinical interpretation, gene prediction, transcript annotation,
experimental biology, physical DNA storage, or genomic diagnosis.
