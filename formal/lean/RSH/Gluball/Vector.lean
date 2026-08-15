import Mathlib

namespace RSH.Gluball

noncomputable section

/-- Minimal exact three-vector over the reals for theorem-facing GLUBALL geometry. -/
structure Vec3 where
  x : ℝ
  y : ℝ
  z : ℝ

namespace Vec3

@[ext] theorem ext {a b : Vec3} (hx : a.x = b.x) (hy : a.y = b.y) (hz : a.z = b.z) : a = b := by
  cases a
  cases b
  simp_all


def zero : Vec3 := ⟨0, 0, 0⟩
def add (a b : Vec3) : Vec3 := ⟨a.x + b.x, a.y + b.y, a.z + b.z⟩
def sub (a b : Vec3) : Vec3 := ⟨a.x - b.x, a.y - b.y, a.z - b.z⟩
def scale (s : ℝ) (v : Vec3) : Vec3 := ⟨s * v.x, s * v.y, s * v.z⟩
def dot (a b : Vec3) : ℝ := a.x * b.x + a.y * b.y + a.z * b.z
def sqNorm (v : Vec3) : ℝ := dot v v

def cross (a b : Vec3) : Vec3 :=
  ⟨a.y * b.z - a.z * b.y,
   a.z * b.x - a.x * b.z,
   a.x * b.y - a.y * b.x⟩

def rotateZ (θ : ℝ) (v : Vec3) : Vec3 :=
  ⟨Real.cos θ * v.x - Real.sin θ * v.y,
   Real.sin θ * v.x + Real.cos θ * v.y,
   v.z⟩

@[simp] theorem add_zero (v : Vec3) : add v zero = v := by ext <;> simp [add, zero]
@[simp] theorem sub_self (v : Vec3) : sub v v = zero := by ext <;> simp [sub, zero]
@[simp] theorem scale_zero (v : Vec3) : scale 0 v = zero := by ext <;> simp [scale, zero]
@[simp] theorem scale_one (v : Vec3) : scale 1 v = v := by ext <;> simp [scale]

theorem dot_comm (a b : Vec3) : dot a b = dot b a := by
  simp [dot]
  ring

theorem dot_scale_left (s : ℝ) (a b : Vec3) : dot (scale s a) b = s * dot a b := by
  simp [dot, scale]
  ring

theorem dot_scale_right (a : Vec3) (s : ℝ) (b : Vec3) : dot a (scale s b) = s * dot a b := by
  simp [dot, scale]
  ring

theorem sqNorm_scale (s : ℝ) (v : Vec3) : sqNorm (scale s v) = s ^ 2 * sqNorm v := by
  simp [sqNorm, dot, scale]
  ring

theorem sqNorm_add (a b : Vec3) :
    sqNorm (add a b) = sqNorm a + 2 * dot a b + sqNorm b := by
  simp [sqNorm, dot, add]
  ring

theorem sqNorm_linear_combo (a b : Vec3) (c s : ℝ) :
    sqNorm (add (scale c a) (scale s b)) =
      c ^ 2 * sqNorm a + 2 * c * s * dot a b + s ^ 2 * sqNorm b := by
  simp [sqNorm, dot, add, scale]
  ring

theorem cross_dot_left (a b : Vec3) : dot (cross a b) a = 0 := by
  simp [dot, cross]
  ring

theorem cross_dot_right (a b : Vec3) : dot (cross a b) b = 0 := by
  simp [dot, cross]
  ring

theorem sqNorm_cross (a b : Vec3) :
    sqNorm (cross a b) = sqNorm a * sqNorm b - dot a b ^ 2 := by
  simp [sqNorm, dot, cross]
  ring

theorem sqNorm_nonneg (v : Vec3) : 0 ≤ sqNorm v := by
  unfold sqNorm dot
  nlinarith [mul_self_nonneg v.x, mul_self_nonneg v.y, mul_self_nonneg v.z]

end Vec3

end

end RSH.Gluball
