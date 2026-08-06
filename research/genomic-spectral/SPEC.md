# RSH-ETQ-GENOMIC-SPECTRAL-V1

## 1. Purpose and boundary

This contract defines a deterministic, inspectable **genomic feature-evidence**
surface layered above `RSH-ETQ-DNA-MIDI-EXPLORATORY-V1`. It is designed to
stabilise the biological input and spectral workload before any multi-device
CUDA implementation is attempted.

It does not predict genes, identify regulatory elements, diagnose disease,
classify pathogenicity, infer phenotype, or make an ETQ mapping biologically
canonical.

## 2. Input identity

The input is one FASTA record using the uppercase IUPAC DNA alphabet
`ACGTRYSWKMBDHVN`. Whitespace is ignored; gaps and multiple records are rejected.
The report records:

- SHA-256 of the normalized sequence;
- GA4GH refget `SQ.` accession derived from the first 24 bytes of SHA-512;
- reverse-complement SHA-256;
- a strand-canonical SHA-256 using lexicographic minimum of the forward and
  reverse-complement strings.

IUPAC ambiguity symbols remain present in identity. Exact A/C/G/T-only metrics
report an explicit ambiguous-base count and do not invent fractional bases.

## 3. Windows

Windows use declared positive integer `window_size` and `stride`. The final
partial window is included without padding. The sealed profile uses 303-base,
non-overlapping windows so that each full window spans exactly one ETQ event
cycle.

For zero-based sequence offset `q`:

```text
event = q mod 303
site = event mod 101
fibre = event mod 3
```

This is a positional receiver address, not a claim that DNA is canonically
indexed by ETQ.

## 4. Exact feature surface

Every window records integer evidence only:

- A/C/G/T and ambiguity counts;
- GC and CpG counts;
- all 16 dinucleotide counts and 64 trinucleotide counts;
- exact period-3 Voss-channel power;
- exact `[1,-2,1]` SCL second-difference energy;
- start and end ETQ addresses.

For channel indicator `x_i`, period-3 power is represented without floating
point as four times the unnormalised DFT power at frequency `1/3`:

```text
R2 = sum_i x_i * [2,-1,-1]_(i mod 3)
I  = sum_i x_i * [0, 1,-1]_(i mod 3)
P3_scaled = R2^2 + 3 I^2
```

SCL energy is computed independently per A/C/G/T channel:

```text
E_scl = sum_i (x_i - 2 x_(i+1) + x_(i+2))^2
```

## 5. VCF subset

The optional parser accepts a strict text subset of VCF 4.5:

- exactly one alternate allele;
- REF and ALT are distinct single canonical bases A/C/G/T;
- CHROM matches the FASTA record identifier;
- POS is a valid one-based sequence position;
- REF must match the normalized FASTA sequence.

Each SNV records transition/transversion class, local 3-mer context, ETQ
position address, containing analysis window, and exact deltas for window
period-3 power, SCL energy, GC count, and CpG count.

When a positive-strand one-based frame origin is supplied, the standard genetic
code is used to report a narrowly labelled frame-relative codon comparison. It
is not a transcript model or annotation authority.

## 6. SPECTRAL receiver

The Type-0 MIDI file is a deterministic **derived receiver** for window evidence.
It carries a contract marker and maps declared integer features to bounded note,
velocity, duration, channel, pan, and brightness controls. MIDI is excluded from
sequence identity and biological authority.

## 7. Canonical artifacts

```text
report.json
windows.csv
variants.csv
spectrum.mid
manifest.json
```

The canonical report uses recursively sorted compact UTF-8 JSON. Python and
browser JavaScript must reproduce identical report, CSV, and MIDI hashes for the
sealed profile.

## 8. Mandatory non-claims

```text
actual_multi_device_execution: false
biological_function_inferred: false
clinical_variant_interpretation: false
coding_region_annotation_authority: false
distributed_execution: false
etq_canonical_genomic_mapping: false
gene_prediction_demonstrated: false
geometry_receipt_authority: false
physical_dna_storage_demonstrated: false
spectral_feature_is_diagnostic: false
```
