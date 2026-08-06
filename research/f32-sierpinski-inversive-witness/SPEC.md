# RSH-F32-SIERPINSKI-INVERSIVE-WITNESS-V1

## 1. Scope

This contract adds an exact rational sidecar witness to each
`RSH-F32-SIERPINSKI-CELL-V1` cell. It applies inversion about the circumcircle of
a unit equilateral triangle and then reflects the result across one of the three
triangle medians.

The ETQ fibre label `a ∈ {0,1,2}` selects the median. Applying the same witness
transformation twice must recover the original cell centroid exactly.

This is an inversion-reflection witness inspired by the mechanism used in
Clawson–Schmidt conjugation. It does **not** construct a complete quadrilateral,
a Miquel point, or a Clawson conjugate.

## 2. Source cell

The source identity remains:

```text
IEEE-754 binary32 raw word
↔ unsigned 32-bit integer
↔ 21-trit Sierpiński address
```

The source cell provides an exact centroid in barycentric coordinates:

```text
λ = (n0/d, n1/d, n2/d)
n0 + n1 + n2 = d
```

For depth 21, the unreduced cell-centroid denominator is `3 × 2^21`.

## 3. Inversion centre and constant

The inversion centre is the centroid of the reference equilateral triangle:

```text
M = (1/3, 1/3, 1/3)
```

The reference triangle has unit side length. Its circumradius squared is:

```text
c² = 1/3
```

The implementation uses only exact integer and rational arithmetic.

## 4. Fibre-selected reflection

The fibre label selects a median reflection by permuting barycentric components:

```text
a = 0: (0,1,2) → (0,2,1)   median through left vertex
a = 1: (0,1,2) → (2,1,0)   median through right vertex
a = 2: (0,1,2) → (1,0,2)   median through apex
```

These permutations are exact orthogonal symmetries of the equilateral triangle.

## 5. Exact transform

Given normalized barycentric numerators `n_i` and denominator `d`, define:

```text
q_i = 3 n_i - d
S   = q_0² + q_1² + q_2²
```

The point is the inversion centre only when `S = 0`; that singular input has no
finite conjugate and is rejected.

Let `π_a` be the fibre-selected reflection permutation. The conjugate is:

```text
n'_i = S + 6 d q_{π_a(i)}
d'   = 3 S
```

The result is reduced by the common integer gcd. Barycentric numerators may be
negative because inversion can place the conjugate outside the reference
triangle.

## 6. Radius-product invariant

For an equilateral triangle in barycentric coordinates:

```text
r² = ||λ - M||² = S / (18 d²)
```

If `r'²` is computed from the conjugate, the exact witness must satisfy:

```text
r² × r'² = c⁴ = 1/9
```

The contract publishes source radius squared, conjugate radius squared, and the
reduced product as canonical decimal-string rationals.

## 7. Involution invariant

Using the same fibre label twice must recover the normalized source centroid:

```text
T_a(T_a(λ)) = λ
```

Both the recovered barycentric coordinate and the Boolean verification field are
included in each witness record.

## 8. Canonical evidence

Exact integers are serialized as canonical decimal strings. A witness records:

- the source binary32 word and 21-trit address;
- the canonical SHA-256 of the source cell record;
- the fibre label, reflection axis, and permutation;
- source, conjugate, and double-application barycentric rationals;
- source and conjugate radius-squared rationals;
- the exact squared-radius product `1/9`;
- explicit product and double-application verification;
- mandatory non-claims.

A bundle contains at most 4,096 witnesses and has a canonical SHA-256 over the
complete unsigned bundle object.

## 9. Browser projection

The offline laboratory may render the triangle, inversion circle, selected
median, source point, conjugate point, and recovered point. Rendering converts
exact rationals to local display numbers only after the witness has been
validated.

Rendered coordinates are not identity and do not replace the exact rational
record.

## 10. CUDA boundary

A later CUDA experiment may compute or validate these witnesses only under a new
hardware contract. It must preserve:

- exact source `word_u32` values;
- fibre labels and ordered witness indices;
- complete readback;
- exact integer/rational comparison against this reference;
- device, launch, sanitizer, and repeatability evidence;
- no geometry-authority, compression, physical-storage, distributed, or
  universal-speedup claim.

The physical multi-device CUDA experiment is deferred to PR #21.

## 11. Mandatory non-claims

```text
actual_multi_device_execution: false
clawson_quadrilateral_constructed: false
compression_claim: false
coordinates_are_identity: false
distributed_execution: false
geometry_receipt_authority: false
physical_storage_demonstrated: false
```
