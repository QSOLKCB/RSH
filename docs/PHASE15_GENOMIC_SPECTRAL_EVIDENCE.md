# Phase 15 — deterministic genomic spectral evidence

Phase 15 inserts a biology-aware reference workload before the planned
multi-device CUDA experiment.

## Extension selected

The extension is `RSH-ETQ-GENOMIC-SPECTRAL-V1`, a separately named contract that
adds:

- single-record FASTA and IUPAC DNA normalization;
- GA4GH-style sequence-derived accessions and strand identity;
- 303-base genomic windows with deterministic ETQ position addresses;
- exact dinucleotide and trinucleotide frequency surfaces;
- exact period-3 Voss spectral power without floating-point identity;
- exact `[1,-2,1]` SCL channel energy inherited as a declared ETQ receiver
  feature rather than a biological law;
- a strict VCF 4.5 biallelic SNV subset;
- exact per-variant feature deltas and optional frame-relative codon comparison;
- deterministic JSON, CSV, MIDI, and manifest artifacts;
- matching Python and browser JavaScript implementations.

## Why before multi-CUDA

Accelerating Phase 14 directly would mainly parallelise symbolic codon mapping.
The Phase 15 window records create a larger, independent, embarrassingly
parallel payload whose output is already sealed by a readable CPU reference.
A later CUDA contract can partition windows or variants, compare every returned
record to this reference, and preserve ordered reconstruction using the existing
RSH shard-prefix discipline.

The future accelerator must not change normalization, tail policy, exact integer
metrics, variant parsing, report serialization, or claim flags.

## Sealed profile

```text
sequence length       606 bases
window size / stride  303 / 303
windows               2
SNVs                   2
frame origin           1
```

The fixture includes one transversion producing a frame-relative `stop-gained`
label and one transition producing `missense`. These labels are fixture-level
comparisons under an explicitly supplied frame, not gene annotation.

## Proposed future CUDA boundary

A later `RSH-ETQ-GENOMIC-SPECTRAL-CUDA-V1` may accelerate only declared window
or SNV metric kernels and must publish:

- exact source sequence accession and profile hash;
- device, driver, toolkit, architecture, precision, grid, and launch metadata;
- complete output readback;
- per-record comparison with the Phase 15 reference;
- deterministic shard coverage and ordered assembly;
- sanitizer and repeatability evidence;
- `actual_multi_device_execution` true only after physical execution;
- `geometry_receipt_authority`, `clinical_variant_interpretation`, and
  `spectral_feature_is_diagnostic` false.

## Authority boundary

This phase is computational feature extraction and sonification. It does not
perform clinical interpretation, gene prediction, transcript annotation,
experimental biology, physical DNA storage, or genomic diagnosis.
