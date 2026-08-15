import RSH.Gluball.Centerline

namespace RSH.Gluball

open Vec3

/-- Positive speed reconstructed from the exact squared-speed identity. -/
def speed (t : ℝ) : ℝ := Real.sqrt (speedSq t)

theorem speed_pos (t : ℝ) : 0 < speed t := by
  exact Real.sqrt_pos.2 (speedSq_pos t)

theorem speed_ne_zero (t : ℝ) : speed t ≠ 0 := ne_of_gt (speed_pos t)

theorem speed_sq (t : ℝ) : speed t ^ 2 = speedSq t := by
  exact Real.sq_sqrt (le_of_lt (speedSq_pos t))

/-- Unit tangent used by the GLUBALL rendering frame. -/
def tangent (t : ℝ) : Vec3 := Vec3.scale (1 / speed t) (centerlineDerivative t)

/-- Cross-product direction before normalization. -/
def binormalRaw (t : ℝ) : Vec3 := Vec3.cross (centerlineDerivative t) (torusNormal t)

/-- Unit binormal. Orthogonality makes its normalization factor equal to the centreline speed. -/
def binormal (t : ℝ) : Vec3 := Vec3.scale (1 / speed t) (binormalRaw t)

theorem tangent_sqNorm (t : ℝ) : Vec3.sqNorm (tangent t) = 1 := by
  rw [tangent, Vec3.sqNorm_scale, derivative_sqNorm, ← speed_sq]
  field_simp [speed_ne_zero]

theorem tangent_dot_normal (t : ℝ) : Vec3.dot (tangent t) (torusNormal t) = 0 := by
  rw [tangent, Vec3.dot_scale_left, derivative_dot_torusNormal]
  ring

theorem binormalRaw_sqNorm (t : ℝ) : Vec3.sqNorm (binormalRaw t) = speedSq t := by
  rw [binormalRaw, Vec3.sqNorm_cross, derivative_sqNorm, torusNormal_sqNorm,
    derivative_dot_torusNormal]
  ring

theorem binormal_sqNorm (t : ℝ) : Vec3.sqNorm (binormal t) = 1 := by
  rw [binormal, Vec3.sqNorm_scale, binormalRaw_sqNorm, ← speed_sq]
  field_simp [speed_ne_zero]

theorem binormal_dot_normal (t : ℝ) : Vec3.dot (binormal t) (torusNormal t) = 0 := by
  rw [binormal, Vec3.dot_scale_left, binormalRaw, Vec3.cross_dot_right]
  ring

theorem tangent_dot_binormal (t : ℝ) : Vec3.dot (tangent t) (binormal t) = 0 := by
  rw [tangent, binormal, Vec3.dot_scale_left, Vec3.dot_scale_right]
  rw [binormalRaw, Vec3.dot_comm, Vec3.cross_dot_left]
  ring

end RSH.Gluball
