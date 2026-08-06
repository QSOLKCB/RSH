# Genomic spectral evidence

`RSH-ETQ-GENOMIC-SPECTRAL-V1` is the reference genomics layer proposed between
the DNA–ETQ–MIDI codec and future multi-device CUDA work.

It converts a single FASTA record and an optional strict biallelic-SNV VCF subset
into deterministic window evidence, variant deltas, a SPECTRAL MIDI receiver,
and a SHA-256 manifest. Its primary job is to make the future accelerator target
scientifically legible and reproducible before parallel hardware is introduced.

## Why this follows the codec

The Phase 14 codec proves exact symbolic recovery and ETQ receiver addressing.
It deliberately does not answer genomic questions. Phase 15 adds conventional
sequence-analysis surfaces—k-mer frequency structure, period-3 evidence,
IUPAC-aware identity, and auditable SNV perturbations—without altering Phase 14.

## Run

```bash
python3 scripts/genomic_spectral_etq.py \
  --fasta sequence.fa \
  --vcf variants.vcf \
  --window-size 303 \
  --stride 303 \
  --frame-origin 1 \
  --output target/genomic-spectral
```

Verify the sealed cross-runtime profile:

```bash
python3 scripts/genomic_spectral_etq.py \
  --verify-profile conformance/genomic_spectral_v1_606.json
node scripts/test_genomic_spectral_etq.mjs
```

## Browser laboratory

Open `web/genomic-spectrum/index.html` directly. It runs without a server,
package manager, CDN, or network connection and can export all five artifacts.

## Research references

- H. J. Jeffrey, “Chaos game representation of gene structure,” *Nucleic Acids
  Research* 18(8), 1990. DOI: 10.1093/nar/18.8.2163.
- S. Tiwari et al., “Prediction of probable genes by Fourier analysis of genomic
  sequences,” *Computer Applications in the Biosciences* 13(3), 1997. DOI:
  10.1093/bioinformatics/13.3.263.
- GA4GH refget specification v2.
- GA4GH VCF specification v4.5.
- NCBI IUPAC nucleotide codes and standard genetic code table 1.

These sources motivate the conventional feature surfaces. They do not validate
ETQ as a genomic ontology or make spectral evidence diagnostic.
