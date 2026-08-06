# Exact f32 Sierpiński cells

`RSH-F32-SIERPINSKI-CELL-V1` assigns every possible IEEE-754 binary32 bit pattern
to one depth-21 Sierpiński-triangle cell.

```text
f32 raw bits → u32 → 21 canonical trits → exact triangular cell
```

The conversion is bit-for-bit reversible. It preserves signed zero, infinities,
subnormals, and NaN payload words. The triangle does not create extra storage
capacity: this is an address representation, not compression.

## Why it exists

PR #19 seals the genomic/spectral reference workload before multi-device CUDA.
This cell contract gives later GPU work a deterministic topological address for
every projected `f32` value without allowing the accelerator to redefine the
underlying feature model.

It is the responsible cousin of the famous Quake III bit-level inverse-square-
root trick: the raw float word is treated as structure, but there is no magic
constant, approximation, or Newton step. NEXUS lineage is also retained through
its GPU `f32` bitcasts and triangular-cell work.

## Run

```bash
python3 scripts/f32_sierpinski_cell.py \
  --word 0x5f3759df \
  --value 1.0 \
  --output target/f32-cells.json

python3 scripts/f32_sierpinski_cell.py \
  --verify-profile conformance/f32_sierpinski_cell_v1.json

python3 -m unittest tests.test_f32_sierpinski_cell -v
node scripts/test_f32_sierpinski_cell.mjs
```

The JavaScript module is available at:

```text
web/genomic-spectrum/f32-cell.js
```

It is dependency-free and suitable for the existing offline laboratory or a
future GPU evidence viewer.
