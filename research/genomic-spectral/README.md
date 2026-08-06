# Genomic spectral evidence

`RSH-ETQ-GENOMIC-SPECTRAL-V1` is the reference genomics layer between the
DNA–ETQ–MIDI codec and future multi-device CUDA work.

It converts one bounded FASTA record and an optional strict eight-column VCF 4.5
SNV subset into deterministic window evidence, variant deltas, a SPECTRAL MIDI
receiver, and a SHA-256 manifest. Its job is to make the future accelerator
target scientifically legible and reproducible before parallel hardware is
introduced.

## Safety and determinism

The implementation rejects oversized FASTA/VCF input, more than 4,096 windows,
more than 4,096 SNVs, duplicate loci, malformed headers, overlapping-window
variant evidence, and invalid frame origins before publishing artifacts.
`report.json` is the exact canonical byte stream named by the manifest.

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
python3 -m unittest tests.test_genomic_spectral_etq -v
node scripts/test_genomic_spectral_etq.mjs
```

## Browser laboratory

Open `web/genomic-spectrum/index.html` directly. It runs without a server,
package manager, CDN, or network connection. User-provided identifiers are
rendered through text nodes rather than HTML, failed analyses clear stale
artifacts, and playback follows the same 480-PPQ / 120-BPM timing as MIDI export.

## Research references

- H. J. Jeffrey, “Chaos game representation of gene structure,” *Nucleic Acids
  Research* 18(8), 1990. DOI: 10.1093/nar/18.8.2163.
- S. Tiwari et al., “Prediction of probable genes by Fourier analysis of genomic
  sequences,” *Computer Applications in the Biosciences* 13(3), 1997. DOI:
  10.1093/bioinformatics/13.3.263.
- GA4GH refget specification v2.
- GA4GH VCF specification v4.5.
- NCBI IUPAC nucleotide codes and standard genetic code table 1.

These sources motivate conventional feature surfaces. They do not validate ETQ
as a genomic ontology or make spectral evidence diagnostic.
