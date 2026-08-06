# RSH-F32-SIERPINSKI-CELL-V1

## 1. Scope

This contract maps every IEEE-754 binary32 bit pattern to one exact depth-21
Sierpiński-triangle address and recovers the original 32-bit word without loss.
It is a deterministic software evidence format for future GPU payloads.

It does not compress the word, approximate the float, prove physical storage, or
make the rendered triangle coordinate authoritative.

## 2. Why depth 21

```text
3^20 = 3,486,784,401
2^32 = 4,294,967,296
3^21 = 10,460,353,203
```

Twenty trits cannot address every binary32 word. Twenty-one trits can. The
canonical address is the zero-padded, most-significant-first base-3
representation of the unsigned 32-bit word.

## 3. IEEE-754 identity

The input identity is the raw `u32` word, not a host-language floating-point
string. Sign, exponent, fraction, signed zero, infinities, and NaN payloads are
preserved exactly.

```text
word_u32 ↔ 21 address trits
```

Conversion of an ordinary numeric value to a word uses the host's standard
IEEE-754 binary32 conversion. Exact replay should exchange `word_u32` or
`word_hex`.

## 4. Sierpiński cell

Trits select the left, right, or apex contraction of a reference triangle. The
21-trit path identifies one depth-21 subtriangle.

The contract emits exact barycentric numerators for all three cell vertices with
common denominator `2^21`. It also emits the exact cell-centroid barycentric
numerators with denominator `3 × 2^21`.

Coordinates are derived evidence. The trit address and raw word are the exact
identity fields.

## 5. Lineage

The design deliberately preserves two pieces of Trent Slade/QSOL-IMC project
lineage:

1. the Quake III fast inverse-square-root family treats a binary32 value's raw
   bits as computational structure before numerical refinement;
2. NEXUS GPU work uses WGSL `bitcast<u32>(f32)` in deterministic state mixing,
   while VE-24 uses explicit triangular faces and cell state.

This contract combines bit-structural interpretation with triangular addressing.
It does **not** use the Quake magic constant as an approximation algorithm and
it does not import the NEXUS state machine into RSH.

The hexadecimal word `5f3759df` is retained only as a lineage fixture proving
that arbitrary 32-bit patterns round-trip.

## 6. Validation

Implementations must test:

- exact round trip for all IEEE-754 classes;
- signed-zero distinction;
- quiet/signaling NaN payload preservation at the word level;
- random 32-bit words;
- exact depth and barycentric denominators;
- cross-runtime canonical bundle hash;
- rejection of invalid trits, out-of-domain addresses, modified geometry
  evidence, and promoted claims.

## 7. CUDA boundary

A future CUDA adapter may emit or consume these cells only if it publishes:

- the exact source `word_u32` values;
- complete ordered readback;
- exact cell-address comparison;
- device and launch metadata;
- sanitizer and repeatability evidence;
- no compression, physical-storage, distributed, or geometry-authority claim.

Repeated division by three or an equivalent exact integer conversion may derive
the trits on device. The cell codec must not alter a numerical kernel's float.

## 8. Mandatory non-claims

```text
actual_multi_device_execution: false
compression_claim: false
coordinates_are_identity: false
distributed_execution: false
geometry_receipt_authority: false
physical_storage_demonstrated: false
```
