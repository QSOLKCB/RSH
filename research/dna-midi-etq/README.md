# DNA–ETQ–MIDI exploratory codec

`RSH-ETQ-DNA-MIDI-EXPLORATORY-V1` is a bounded deterministic codec and offline
browser laboratory derived from the conceptual seed in `QSOL-IMC-DNA-SPEC.zip`.
It maps complete DNA codons into an ETQ-303-compatible address surface, emits a
metadata-bearing Type-0 MIDI file, verifies exact DNA → MIDI → DNA recovery, and
projects the sequence through a global tetrahedral iterated-function system.

The prototype archive is recorded as lineage evidence only. Its alternate
`parallel-gpu.js` and WGSL files are **not imported**. RSH retains the accepted
single-device and shard-prefix implementations instead of creating a second
implementation under the same contract name.

## Contract

For each complete codon:

- the alphabetic codon index `j ∈ [0, 63]` is used as an exploratory site within
  the ETQ site domain `[0, 100]`;
- the base position inside that codon is the independent fibre label
  `a ∈ {0, 1, 2}`;
- the ETQ event index is

```text
n = j + 101 × ((2 × (a - (j mod 3))) mod 3)
```

This preserves the exact Chinese-remainder address relationship without
collapsing `A` and `T` onto the same qutrit value. Base identity remains encoded
by the codon and is also written into MIDI control metadata.

## Global tetrahedral projection

The four DNA symbols select the four vertices of a regular tetrahedron. Starting
at the centroid, every base applies

```text
p_next = (p_current + vertex(base)) / 2
```

across the **whole sequence**. The state is not reset at codon boundaries. The
result is a genuine three-dimensional Sierpinski-tetrahedron address path rather
than the planar `x = z` projection in the source prototype.

## Exact MIDI round trip

The Type-0 MIDI stream uses 480 PPQ and 120 BPM. Each note is preceded by:

| Control | Meaning |
|---|---|
| CC 20 | codon site index |
| CC 21 | base digit (`A=0, C=1, G=2, T=3`) |
| CC 22 | ETQ event-index base-128 MSB |
| CC 23 | ETQ event-index base-128 LSB |
| CC 24 | Gaussian phase exponent |
| CC 74 | audible brightness mapping |

The MIDI channel is the codon offset/fibre label. The decoder rejects missing,
reordered, inconsistent, or tampered metadata.

## Run

```bash
python3 scripts/dna_midi_etq.py \
  --sequence ATGGCCAAAGCGTTCGACGGCTAG \
  --output target/dna-midi

python3 scripts/dna_midi_etq.py \
  --verify-profile conformance/dna_midi_etq_exploratory_v1.json

python3 -m unittest tests.test_dna_midi_etq -v
node scripts/test_dna_midi_etq.mjs
```

The offline laboratory is deployed at:

```text
https://qsolkcb.github.io/RSH/dna-midi/
```

## Non-claims

```text
physical_dna_storage_demonstrated: false
biological_error_correction_demonstrated: false
sierpinski_embedding_is_physical_geometry: false
etq_canonical_dna_mapping: false
actual_multi_device_execution: false
distributed_execution: false
geometry_receipt_authority: false
```
