# Phase 14 — exploratory DNA–ETQ–MIDI codec

Phase 14 introduces `RSH-ETQ-DNA-MIDI-EXPLORATORY-V1` as a separately named
research surface. It converts complete DNA codons into deterministic ETQ-compatible
addresses, exact-recovery MIDI metadata, and a global tetrahedral address path.

## Why this is separate

ETQ-303 is an exact finite event protocol. RSH geometry contracts are scientific
and numerical evidence surfaces. Neither contract asserts DNA storage, so this
feature receives a new name, new conformance profile, and mandatory non-claims.

## Improvements over the source prototype

- strict validation replaces silent deletion of unsupported characters;
- incomplete codons are rejected rather than truncated;
- codon offset is the independent qutrit fibre, preserving all four DNA bases;
- MIDI contains enough metadata for exact recovery decoding;
- the Sierpinski recurrence is global rather than reset for each codon;
- four tetrahedral vertices replace the planar three-direction `x=z` map;
- Python and JavaScript reproduce the same report, CSV, and MIDI hashes;
- prototype GPU files are excluded in favour of existing accepted RSH contracts.

## Evidence

```text
conformance/dna_midi_etq_exploratory_v1.json
scripts/dna_midi_etq.py
scripts/test_dna_midi_etq.mjs
tests/test_dna_midi_etq.py
web/dna-midi/
```

The browser surface is dependency-free, installs its own subdirectory-scoped
service worker, and supports playback plus JSON, CSV, MIDI, and manifest export.

## Future boundary

A later multi-device CUDA experiment may use the codec output as a payload, but
that experiment must retain a separate contract and cannot promote the
exploratory tetrahedral projection to geometry authority.
