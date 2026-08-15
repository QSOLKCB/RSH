import RSH.Gluball.Frame

namespace RSH.Gluball

noncomputable section

open Vec3

/-- Radius-`rho` offset in the host-normal/binormal plane. -/
def tubeOffset (t v : ℝ) : Vec3 :=
  Vec3.scale tubeRadius
    (Vec3.add
      (Vec3.scale (Real.cos v) (torusNormal t))
      (Vec3.scale (Real.sin v) (binormal t)))

/-- Frozen GLUBALL tube surface parameterization. -/
def surfacePoint (t v : ℝ) : Vec3 := Vec3.add (centerline t) (tubeOffset t v)

theorem normal_dot_binormal (t : ℝ) : Vec3.dot (torusNormal t) (binormal t) = 0 := by
  rw [Vec3.dot_comm]
  exact binormal_dot_normal t

/-- The tube offset has exactly the declared squared radius. -/
theorem tubeOffset_sqNorm (t v : ℝ) : Vec3.sqNorm (tubeOffset t v) = tubeRadius ^ 2 := by
  rw [tubeOffset, Vec3.sqNorm_scale, Vec3.sqNorm_linear_combo,
    torusNormal_sqNorm, binormal_sqNorm, normal_dot_binormal]
  have h := Real.sin_sq_add_cos_sq v
  nlinarith

theorem surface_sub_centerline (t v : ℝ) :
    Vec3.sub (surfacePoint t v) (centerline t) = tubeOffset t v := by
  apply Vec3.ext <;> simp [surfacePoint, Vec3.sub, Vec3.add]

/-- Exact squared tube-radius invariant for `GLUBALL-KNOT-V1`. -/
theorem surface_radius_sq (t v : ℝ) :
    Vec3.sqNorm (Vec3.sub (surfacePoint t v) (centerline t)) = tubeRadius ^ 2 := by
  rw [surface_sub_centerline, tubeOffset_sqNorm]

theorem tubeOffset_v_periodic (t v : ℝ) : tubeOffset t (v + 2 * Real.pi) = tubeOffset t v := by
  apply Vec3.ext <;> simp [tubeOffset, Vec3.scale, Vec3.add]

/-- The tube coordinate closes exactly in its angular `v` parameter. -/
theorem surface_v_periodic (t v : ℝ) : surfacePoint t (v + 2 * Real.pi) = surfacePoint t v := by
  simp [surfacePoint, tubeOffset_v_periodic]

end

end RSH.Gluball
