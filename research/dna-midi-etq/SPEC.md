# RSH-ETQ-DNA-MIDI-EXPLORATORY-V1

## 1. Scope

This contract defines an exact finite software codec. It accepts text over the
alphabet `{A,C,G,T}` whose length is a positive multiple of three, produces a
canonical record sequence, a CSV mapping, a Type-0 MIDI stream, and a SHA-256
manifest, and proves deterministic recovery of the input from the MIDI metadata.

It does not define DNA synthesis, sequencing, biological storage density,
mutation correction, physical lattice assembly, or a new ETQ-303 canonical
mapping.

## 2. Input

1. ASCII DNA symbols are case-insensitive.
2. Unicode whitespace is removed.
3. Every remaining character must be one of `A`, `C`, `G`, `T`.
4. Empty input is rejected.
5. Incomplete codons are rejected; no padding or silent truncation occurs.
6. Raw input text is limited to 48,000 characters before normalization.
7. The normalized sequence is limited to 12,000 bases before coordinate,
   record, MIDI, table, or audio allocations are created.

## 3. Codon site

Codons use lexicographic base-4 order under `A < C < G < T`:

```text
AAA = 0
AAC = 1
...
TTT = 63
```

The resulting `j` is an exploratory site index inside ETQ's preserved
`0 ≤ j < 101` site domain.

## 4. Fibre and ETQ event address

For base index `i`, the fibre label is the codon offset:

```text
a = i mod 3
```

The event index is the Chinese-remainder inverse:

```text
k = (2 × (a - (j mod 3))) mod 3
n = j + 101 × k
```

The inverse address is:

```text
j = n mod 101
a = n mod 3
```

All 303 `(j,a)` addresses are tested for bijective round trip.

## 5. Tetrahedral IFS

The vertices are:

```text
A = (0, 0, 0)
C = (1, 0, 0)
G = (1/2, √3/2, 0)
T = (1/2, √3/6, √(2/3))
```

The initial point is their centroid. Each base updates the global point by
`p_next=(p_current+vertex)/2`. Coordinates are serialized as fixed 12-decimal
strings to preserve cross-runtime canonical bytes.

## 6. MIDI

- format: 0
- track count: 1
- division: 480 PPQ
- tempo: 120 BPM
- start interval: 120 ticks per base
- MIDI channel: fibre label `0..2`
- note pitch: deterministic C-major register mapping
- note duration: 180 ticks for positive SCL lanes; 240 for the `-2` lane
- schema marker: track-name meta event containing the contract identifier

Every note-on must be immediately preceded on its channel by one fresh ordered
metadata sequence:

```text
CC20, CC21, CC22, CC23, CC24, CC74
```

Consumed metadata is cleared after each note. Stale, missing, duplicated,
reordered, unrelated, or excess controls are rejected. The decoder also requires
all three notes in a codon to declare one shared site index and validates the
codon, base, fibre, and ETQ event address.

## 7. Canonical evidence

The canonical report is UTF-8 JSON with recursive lexicographic object-key order,
no insignificant whitespace, and coordinates already encoded as fixed-decimal
strings. The emitted `report.json` contains exactly the bytes hashed by the
manifest. The manifest records SHA-256 for:

- normalized sequence bytes;
- canonical report bytes;
- CSV bytes including final LF;
- MIDI bytes.

Python and JavaScript implementations must reproduce the same sealed hashes.
Text evidence is emitted as explicit UTF-8/LF bytes so platform newline policies
cannot change the declared artifacts.

## 8. Authority boundary

The codec report is an exploratory data artifact. It cannot replace an RSH
geometry receipt, ETQ release artifact, physical measurement, biological assay,
or hardware-execution audit.
