import Mathlib

namespace RSH

/-- Exact three-vector over the rationals, used by theorem-facing RSH contracts. -/
structure Vec3Q where
  x : ℚ
  y : ℚ
  z : ℚ
  deriving DecidableEq, Repr

namespace Vec3Q

def zero : Vec3Q := ⟨0, 0, 0⟩
def add (a b : Vec3Q) : Vec3Q := ⟨a.x + b.x, a.y + b.y, a.z + b.z⟩
def sub (a b : Vec3Q) : Vec3Q := ⟨a.x - b.x, a.y - b.y, a.z - b.z⟩
def scale (s : ℚ) (v : Vec3Q) : Vec3Q := ⟨s * v.x, s * v.y, s * v.z⟩
def dot (a b : Vec3Q) : ℚ := a.x * b.x + a.y * b.y + a.z * b.z
def sqNorm (v : Vec3Q) : ℚ := dot v v

@[simp] theorem scale_zero (v : Vec3Q) : scale 0 v = zero := by ext <;> simp [scale, zero]
@[simp] theorem scale_one (v : Vec3Q) : scale 1 v = v := by ext <;> simp [scale]
@[simp] theorem add_zero (v : Vec3Q) : add v zero = v := by ext <;> simp [add, zero]
@[simp] theorem sub_self (v : Vec3Q) : sub v v = zero := by ext <;> simp [sub, zero]

theorem scale_scale (a b : ℚ) (v : Vec3Q) : scale a (scale b v) = scale (a * b) v := by
  ext <;> simp [scale] <;> ring

theorem dot_comm (a b : Vec3Q) : dot a b = dot b a := by
  simp [dot]
  ring

theorem dot_add_right (a b c : Vec3Q) : dot a (add b c) = dot a b + dot a c := by
  simp [dot, add]
  ring

theorem dot_add_left (a b c : Vec3Q) : dot (add a b) c = dot a c + dot b c := by
  rw [dot_comm, dot_add_right]
  rw [dot_comm c a, dot_comm c b]

theorem dot_scale_right (a : Vec3Q) (s : ℚ) (b : Vec3Q) : dot a (scale s b) = s * dot a b := by
  simp [dot, scale]
  ring

theorem dot_scale_left (s : ℚ) (a b : Vec3Q) : dot (scale s a) b = s * dot a b := by
  rw [dot_comm, dot_scale_right]
  rw [dot_comm b a]

theorem sqNorm_scale (s : ℚ) (v : Vec3Q) : sqNorm (scale s v) = s ^ 2 * sqNorm v := by
  simp [sqNorm, dot, scale]
  ring

end Vec3Q
end RSH
