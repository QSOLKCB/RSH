# Phase 16 — exact f32 Sierpiński inversive witnesses

Phase 16 introduces `RSH-F32-SIERPINSKI-INVERSIVE-WITNESS-V1` after the merged
Phase 15B exact-cell foundation.

## Purpose

The cell contract proves that an IEEE-754 binary32 word can be recovered exactly
from a depth-21 ternary Sierpiński address. Phase 16 adds a second, independent
geometric check over the exact cell centroid:

```text
source centroid
→ circumcircle inversion
→ ETQ-fibre-selected median reflection
→ exact conjugate
→ repeat
→ exact source centroid
```

The transform is represented entirely by integer and rational arithmetic.

## Accepted invariants

Every witness must prove:

1. source word and trit address still identify one accepted cell;
2. the source-cell canonical SHA-256 matches that exact cell record;
3. the selected median permutation matches fibre `0`, `1`, or `2`;
4. source and conjugate squared radii multiply to `1/9`;
5. applying the same transform twice returns the normalized source barycentric
   coordinate exactly;
6. all mandatory non-claims remain literal JSON booleans.

## Cross-runtime surface

The implementation includes:

```text
scripts/f32_sierpinski_inversive_witness.py
web/inversive-witness/model.js
conformance/f32_sierpinski_inversive_witness_v1.json
tests/test_f32_sierpinski_inversive_witness.py
scripts/test_f32_sierpinski_inversive_witness.mjs
```

Python and JavaScript reproduce the sealed bundle hash:

```text
c356948f6967d89c3dbb248bfb0e66e557a6d5a753502ecfd844cfe4e383dc99
```

## Offline laboratory

The browser laboratory draws:

- the unit equilateral reference triangle;
- its circumcircle and centroid;
- the median selected by the fibre label;
- the source cell centroid;
- the exact conjugate projected for display;
- the double-application recovery marker.

The UI exports canonical witness JSON. Display coordinates remain non-authority
projections derived after exact validation.

## Post-merge Phase 15B hardening

The same PR also closes four review findings discovered after PR #19 merged:

- word iterables are bounded before complete materialization;
- Python accepts only literal Boolean claim values;
- field labels are constrained to printable ASCII for matching canonical hashes;
- superseded browser analyses cannot overwrite newer genomic evidence.

## Naming boundary

The transformation uses the inversion-plus-reflection mechanism discussed in
the supplied Clawson geometry transcript. RSH does not call the result a Clawson
conjugate because no complete quadrilateral or Miquel point is constructed.

## Next phase

Physical multi-device CUDA is deferred to PR #21. That adapter may consume these
witnesses only under a separately named hardware contract with complete ordered
readback and actual-device evidence.
