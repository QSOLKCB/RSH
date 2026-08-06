# Phase 15B — exact f32 Sierpiński cells

Phase 15B extends the pre-CUDA evidence foundation with
`RSH-F32-SIERPINSKI-CELL-V1`.

## Purpose

The genomic spectral workload contains exact integer reference features. A
future GPU adapter will project selected kernel inputs and outputs to binary32.
Before multi-device execution is attempted, every such raw 32-bit cell can now
be represented by an exact depth-21 triangular address and reconstructed
bit-for-bit.

## Construction

```text
binary32 word domain: 2^32
address alphabet:      {0,1,2}
address depth:         21
cell count available:  3^21
```

The address is simply the canonical base-3 form of the word, padded to 21 trits.
Each trit selects one corner contraction in the Sierpiński IFS. Exact
barycentric cell vertices are emitted with denominator `2^21`.

## Project lineage

This formalizes a relationship already present in Trent Slade/QSOL-IMC work:
raw `f32` bit patterns were used as deterministic structure in NEXUS GPU
receipts, and NEXUS VE-24 used triangular faces and lattice cells. It is also
mathematically adjacent to the Quake III inverse-square-root trick's bit-level
view of a float, while remaining lossless and approximation-free.

## PR #20 deferral

The physical multi-device CUDA experiment remains deferred until:

- PR #19 review findings are resolved;
- Python and JavaScript cell codecs agree on the sealed hash;
- malformed/tampered cell evidence is rejected;
- the exact relationship between genomic reference features and projected GPU
  cells is documented;
- CI is green.

PR #20 will consume this contract rather than inventing a private kernel-only
encoding.

## Non-claims

The cells are not compression, biological geometry, physical memory, or geometry
receipts. They do not demonstrate multi-device or distributed execution.
