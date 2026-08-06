# Exact f32 Sierpiński inversive witnesses

`RSH-F32-SIERPINSKI-INVERSIVE-WITNESS-V1` gives each exact depth-21
`f32` Sierpiński cell an independent geometric involution witness.

```text
binary32 raw word
→ exact 21-trit cell
→ exact barycentric centroid
→ fibre-selected inversion + median reflection
→ exact conjugate
→ second application returns the source
```

The inversion circle is the circumcircle of a unit equilateral triangle, so its
radius squared is the rational value `1/3`. The implementation proves the
squared-radius product `1/9` and exact double-application recovery without using
floating-point geometry.

## Project lineage

The source-cell contract treats raw IEEE-754 bits as structure, preserving the
lossless cousin relationship to the Quake III bit-level float trick and Trent
Slade/QSOL-IMC NEXUS work. This phase adds the inversion-plus-reflection idea
found in the supplied geometry transcript.

The name is deliberately narrower than “Clawson conjugate.” No complete
quadrilateral or Miquel configuration is constructed.

## Run

```bash
python3 scripts/f32_sierpinski_inversive_witness.py \
  --word 0x5f3759df --fibre 0 \
  --output target/inversive-witness.json

python3 scripts/f32_sierpinski_inversive_witness.py \
  --verify-profile conformance/f32_sierpinski_inversive_witness_v1.json

python3 -m unittest tests.test_f32_sierpinski_inversive_witness -v
node scripts/test_f32_sierpinski_inversive_witness.mjs
```

The offline laboratory is published under:

```text
https://qsolkcb.github.io/RSH/inversive-witness/
```

## Sealed fixture

The profile reuses the 15 IEEE-754 edge and lineage words from the cell
conformance profile and exercises all three reflection axes.

```text
bundle SHA-256
c356948f6967d89c3dbb248bfb0e66e557a6d5a753502ecfd844cfe4e383dc99
```

## Boundary

This witness is an exact software evidence sidecar. It does not increase storage
capacity, establish physical geometry, construct a Clawson quadrilateral, or
claim actual multi-device execution. The physical CUDA phase is reserved for
PR #21.
