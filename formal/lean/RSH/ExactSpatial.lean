import RSH.Algebra

namespace RSH.ExactSpatial

open RSH Vec3Q

/-- The three fibre-selected median reflections used by the exact witness contract. -/
inductive Fibre where
  | left
  | right
  | apex
  deriving DecidableEq, Repr

def reflect : Fibre → Vec3Q → Vec3Q
  | .left, v => ⟨v.x, v.z, v.y⟩
  | .right, v => ⟨v.z, v.y, v.x⟩
  | .apex, v => ⟨v.y, v.x, v.z⟩

theorem reflect_involutive (f : Fibre) (v : Vec3Q) : reflect f (reflect f v) = v := by
  cases f <;> ext <;> rfl

theorem reflect_scale (f : Fibre) (s : ℚ) (v : Vec3Q) :
    reflect f (scale s v) = scale s (reflect f v) := by
  cases f <;> ext <;> rfl

theorem sqNorm_reflect (f : Fibre) (v : Vec3Q) : sqNorm (reflect f v) = sqNorm v := by
  cases f <;> simp [reflect, sqNorm, dot] <;> ring

/-- Exact centred-coordinate form of the Python inversion-plus-reflection map. -/
def transform (f : Fibre) (c : Vec3Q) : Vec3Q :=
  scale (6 / sqNorm c) (reflect f c)

/-- The exact squared circumcentric radius used by the witness contract. -/
def radiusSq (c : Vec3Q) : ℚ := sqNorm c / 18

theorem sqNorm_transform (f : Fibre) (c : Vec3Q) (hc : sqNorm c ≠ 0) :
    sqNorm (transform f c) = 36 / sqNorm c := by
  rw [transform, sqNorm_scale, sqNorm_reflect]
  field_simp [hc]
  ring

theorem transform_has_nonzero_norm (f : Fibre) (c : Vec3Q) (hc : sqNorm c ≠ 0) :
    sqNorm (transform f c) ≠ 0 := by
  rw [sqNorm_transform f c hc]
  exact div_ne_zero (by norm_num) hc

/-- RSH-F32-SIERPINSKI-INVERSIVE-WITNESS-V1 radius-product invariant. -/
theorem radius_product_invariant (f : Fibre) (c : Vec3Q) (hc : sqNorm c ≠ 0) :
    radiusSq c * radiusSq (transform f c) = (1 : ℚ) / 9 := by
  rw [radiusSq, radiusSq, sqNorm_transform f c hc]
  field_simp [hc]
  ring

/-- Applying the same fibre-selected inversion/reflection twice is exactly identity. -/
theorem transform_involutive (f : Fibre) (c : Vec3Q) (hc : sqNorm c ≠ 0) :
    transform f (transform f c) = c := by
  have hqt := sqNorm_transform f c hc
  change scale (6 / sqNorm (transform f c)) (reflect f (transform f c)) = c
  rw [hqt, transform, reflect_scale, reflect_involutive, scale_scale]
  have hs : (6 / (36 / sqNorm c)) * (6 / sqNorm c) = (1 : ℚ) := by
    field_simp [hc]
    ring
  rw [hs, scale_one]

/-- Convert ordinary barycentric coordinates to the centred coordinates used above. -/
def toCentered (b : Vec3Q) : Vec3Q :=
  ⟨3 * b.x - 1, 3 * b.y - 1, 3 * b.z - 1⟩

def fromCentered (c : Vec3Q) : Vec3Q :=
  ⟨(c.x + 1) / 3, (c.y + 1) / 3, (c.z + 1) / 3⟩

theorem centered_roundtrip (b : Vec3Q) : fromCentered (toCentered b) = b := by
  ext <;> simp [fromCentered, toCentered]

theorem barycentric_roundtrip (c : Vec3Q) : toCentered (fromCentered c) = c := by
  ext <;> simp [fromCentered, toCentered] <;> ring

/-- 21 ternary digits have strictly more address capacity than an unsigned 32-bit word. -/
def wordCapacity : Nat := 2 ^ 32
def trit21Capacity : Nat := 3 ^ 21

theorem wordCapacity_lt_trit21Capacity : wordCapacity < trit21Capacity := by
  native_decide

def Word32 := {n : Nat // n < wordCapacity}
def Trit21Code := {n : Nat // n < trit21Capacity}

def encodeWord (w : Word32) : Trit21Code :=
  ⟨w.1, lt_trans w.2 wordCapacity_lt_trit21Capacity⟩

theorem encodeWord_injective : Function.Injective encodeWord := by
  intro a b h
  have hv : (encodeWord a).1 = (encodeWord b).1 :=
    congrArg (fun x : Trit21Code => x.1) h
  apply Subtype.ext
  exact hv

theorem encodeWord_value_roundtrip (w : Word32) : (encodeWord w).1 = w.1 := rfl

end RSH.ExactSpatial
