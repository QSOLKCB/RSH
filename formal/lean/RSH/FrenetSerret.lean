import RSH.Algebra

namespace RSH.FrenetSerret

open RSH Vec3Q

/-- Exact algebraic orthonormal-frame contract. -/
structure Frame where
  t : Vec3Q
  n : Vec3Q
  b : Vec3Q
  tt : dot t t = 1
  nn : dot n n = 1
  bb : dot b b = 1
  tn : dot t n = 0
  tb : dot t b = 0
  nb : dot n b = 0

@[simp] theorem Frame.nt (f : Frame) : dot f.n f.t = 0 := by
  rw [dot_comm]
  exact f.tn

@[simp] theorem Frame.bt (f : Frame) : dot f.b f.t = 0 := by
  rw [dot_comm]
  exact f.tb

@[simp] theorem Frame.bn (f : Frame) : dot f.b f.n = 0 := by
  rw [dot_comm]
  exact f.nb

/-- Frenet–Serret vector field: T' = κN. -/
def dT (κ : ℚ) (f : Frame) : Vec3Q := scale κ f.n

/-- Frenet–Serret vector field: N' = -κT + τB. -/
def dN (κ τ : ℚ) (f : Frame) : Vec3Q :=
  add (scale (-κ) f.t) (scale τ f.b)

/-- Frenet–Serret vector field: B' = -τN. -/
def dB (τ : ℚ) (f : Frame) : Vec3Q := scale (-τ) f.n

/-- The Frenet–Serret field is tangent to the unit-T constraint. -/
theorem tangent_norm_compat (κ : ℚ) (f : Frame) :
    dot (dT κ f) f.t + dot f.t (dT κ f) = 0 := by
  simp [dT, dot_scale_left, dot_scale_right, f.tn]

/-- The Frenet–Serret field is tangent to the unit-N constraint. -/
theorem normal_norm_compat (κ τ : ℚ) (f : Frame) :
    dot (dN κ τ f) f.n + dot f.n (dN κ τ f) = 0 := by
  simp [dN, dot_add_left, dot_add_right, dot_scale_left, dot_scale_right, f.tn, f.nb]

/-- The Frenet–Serret field is tangent to the unit-B constraint. -/
theorem binormal_norm_compat (τ : ℚ) (f : Frame) :
    dot (dB τ f) f.b + dot f.b (dB τ f) = 0 := by
  simp [dB, dot_scale_left, dot_scale_right, f.nb]

/-- Compatibility of the T·N = 0 constraint. -/
theorem tangent_normal_compat (κ τ : ℚ) (f : Frame) :
    dot (dT κ f) f.n + dot f.t (dN κ τ f) = 0 := by
  simp [dT, dN, dot_add_right, dot_scale_left, dot_scale_right, f.tt, f.nn, f.tb]

/-- Compatibility of the T·B = 0 constraint. -/
theorem tangent_binormal_compat (κ τ : ℚ) (f : Frame) :
    dot (dT κ f) f.b + dot f.t (dB τ f) = 0 := by
  simp [dT, dB, dot_scale_left, dot_scale_right, f.nb, f.tn]

/-- Compatibility of the N·B = 0 constraint. -/
theorem normal_binormal_compat (κ τ : ℚ) (f : Frame) :
    dot (dN κ τ f) f.b + dot f.n (dB τ f) = 0 := by
  simp [dN, dB, dot_add_left, dot_scale_left, dot_scale_right, f.tb, f.bb, f.nn]

/-- Exact coordinate normalisation used by the canonical discrete RSH path. -/
def translateBy (offset p : Vec3Q) : Vec3Q := sub p offset

theorem exact_center_translation (p : Vec3Q) : translateBy p p = zero := by
  exact sub_self p

end RSH.FrenetSerret
