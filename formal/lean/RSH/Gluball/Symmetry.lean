import RSH.Gluball.Centerline

namespace RSH.Gluball

noncomputable section

open Vec3

private theorem cos_major_period (t : ℝ) :
    Real.cos (p * (t + 2 * Real.pi)) = Real.cos (p * t) := by
  rw [show p * (t + 2 * Real.pi) = p * t + (2 : ℕ) * (2 * Real.pi) by
    norm_num [p]
    ring]
  simpa using Real.cos_add_nat_mul_two_pi (p * t) 2

private theorem sin_major_period (t : ℝ) :
    Real.sin (p * (t + 2 * Real.pi)) = Real.sin (p * t) := by
  rw [show p * (t + 2 * Real.pi) = p * t + (2 : ℕ) * (2 * Real.pi) by
    norm_num [p]
    ring]
  simpa using Real.sin_add_nat_mul_two_pi (p * t) 2

private theorem cos_minor_period (t : ℝ) :
    Real.cos (q * (t + 2 * Real.pi)) = Real.cos (q * t) := by
  rw [show q * (t + 2 * Real.pi) = q * t + (3 : ℕ) * (2 * Real.pi) by
    norm_num [q]
    ring]
  simpa using Real.cos_add_nat_mul_two_pi (q * t) 3

private theorem sin_minor_period (t : ℝ) :
    Real.sin (q * (t + 2 * Real.pi)) = Real.sin (q * t) := by
  rw [show q * (t + 2 * Real.pi) = q * t + (3 : ℕ) * (2 * Real.pi) by
    norm_num [q]
    ring]
  simpa using Real.sin_add_nat_mul_two_pi (q * t) 3

/-- The frozen `(2,3)` centreline closes after one full parameter turn. -/
theorem centerline_periodic (t : ℝ) : centerline (t + 2 * Real.pi) = centerline t := by
  apply Vec3.ext
  · simp [centerline, radial, cos_major_period, cos_minor_period]
  · simp [centerline, radial, sin_major_period, cos_minor_period]
  · simp [centerline, sin_minor_period]

private theorem minor_shift_cos (t : ℝ) :
    Real.cos (q * (t + 2 * Real.pi / 3)) = Real.cos (q * t) := by
  rw [show q * (t + 2 * Real.pi / 3) = q * t + (1 : ℕ) * (2 * Real.pi) by
    norm_num [q]
    ring]
  simpa using Real.cos_add_nat_mul_two_pi (q * t) 1

private theorem minor_shift_sin (t : ℝ) :
    Real.sin (q * (t + 2 * Real.pi / 3)) = Real.sin (q * t) := by
  rw [show q * (t + 2 * Real.pi / 3) = q * t + (1 : ℕ) * (2 * Real.pi) by
    norm_num [q]
    ring]
  simpa using Real.sin_add_nat_mul_two_pi (q * t) 1

private theorem major_shift (t : ℝ) :
    p * (t + 2 * Real.pi / 3) = p * t + 4 * Real.pi / 3 := by
  norm_num [p]
  ring

/-- Exact threefold rotational symmetry of the frozen GLUBALL v1.0.0 centreline. -/
theorem centerline_c3_symmetry (t : ℝ) :
    centerline (t + 2 * Real.pi / 3) = Vec3.rotateZ (4 * Real.pi / 3) (centerline t) := by
  apply Vec3.ext
  · simp [centerline, radial, Vec3.rotateZ, minor_shift_cos, minor_shift_sin, major_shift,
      Real.cos_add, Real.sin_add]
    ring
  · simp [centerline, radial, Vec3.rotateZ, minor_shift_cos, minor_shift_sin, major_shift,
      Real.cos_add, Real.sin_add]
    ring
  · simp [centerline, minor_shift_sin, Vec3.rotateZ]

end

end RSH.Gluball
