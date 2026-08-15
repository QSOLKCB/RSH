import RSH.Gluball.Parameters
import RSH.Gluball.Vector

namespace RSH.Gluball

noncomputable section

open Vec3

/-- Host-torus radial factor `A(t) = R + r cos(qt)`. -/
def radial (t : ℝ) : ℝ := majorRadius + minorRadius * Real.cos (q * t)

def radialPrime (t : ℝ) : ℝ := -minorRadius * q * Real.sin (q * t)

/-- Frozen GLUBALL v1.0.0 centreline. -/
def centerline (t : ℝ) : Vec3 :=
  ⟨radial t * Real.cos (p * t),
   radial t * Real.sin (p * t),
   minorRadius * Real.sin (q * t)⟩

/-- Closed-form derivative declared by the frozen GLUBALL v1.0.0 geometry. -/
def centerlineDerivative (t : ℝ) : Vec3 :=
  ⟨radialPrime t * Real.cos (p * t) - p * radial t * Real.sin (p * t),
   radialPrime t * Real.sin (p * t) + p * radial t * Real.cos (p * t),
   minorRadius * q * Real.cos (q * t)⟩

/-- Unit normal of the host torus along the centreline. -/
def torusNormal (t : ℝ) : Vec3 :=
  ⟨Real.cos (q * t) * Real.cos (p * t),
   Real.cos (q * t) * Real.sin (p * t),
   Real.sin (q * t)⟩

/-- The exact squared-speed expression from the GLUBALL geometry contract. -/
def speedSq (t : ℝ) : ℝ := p ^ 2 * radial t ^ 2 + q ^ 2 * minorRadius ^ 2

private theorem mul_parameter_hasDerivAt (a t : ℝ) :
    HasDerivAt (fun s : ℝ => a * s) a t := by
  simpa using HasDerivAt.const_mul a (hasDerivAt_id t)

private theorem sin_mul_parameter_hasDerivAt (a t : ℝ) :
    HasDerivAt (fun s : ℝ => Real.sin (a * s)) (a * Real.cos (a * t)) t := by
  simpa [mul_comm] using HasDerivAt.sin (mul_parameter_hasDerivAt a t)

private theorem cos_mul_parameter_hasDerivAt (a t : ℝ) :
    HasDerivAt (fun s : ℝ => Real.cos (a * s)) (-a * Real.sin (a * t)) t := by
  simpa [mul_comm] using HasDerivAt.cos (mul_parameter_hasDerivAt a t)

/-- The declared radial derivative is the actual derivative of `radial`. -/
theorem radial_hasDerivAt (t : ℝ) : HasDerivAt radial (radialPrime t) t := by
  change HasDerivAt
    ((fun _ : ℝ => majorRadius) + fun s : ℝ => minorRadius * Real.cos (q * s))
    (radialPrime t) t
  have h := (hasDerivAt_const t majorRadius).add
    (HasDerivAt.const_mul minorRadius (cos_mul_parameter_hasDerivAt q t))
  simpa [radialPrime, mul_comm, mul_left_comm, mul_assoc] using h

/-- The x component of `centerlineDerivative` is the derivative of the centreline x coordinate. -/
theorem centerline_x_hasDerivAt (t : ℝ) :
    HasDerivAt (fun s : ℝ => (centerline s).x) (centerlineDerivative t).x t := by
  change HasDerivAt
    (radial * fun s : ℝ => Real.cos (p * s))
    (radialPrime t * Real.cos (p * t) - p * radial t * Real.sin (p * t)) t
  have h := (radial_hasDerivAt t).mul (cos_mul_parameter_hasDerivAt p t)
  simpa [sub_eq_add_neg, mul_comm, mul_left_comm, mul_assoc] using h

/-- The y component of `centerlineDerivative` is the derivative of the centreline y coordinate. -/
theorem centerline_y_hasDerivAt (t : ℝ) :
    HasDerivAt (fun s : ℝ => (centerline s).y) (centerlineDerivative t).y t := by
  change HasDerivAt
    (radial * fun s : ℝ => Real.sin (p * s))
    (radialPrime t * Real.sin (p * t) + p * radial t * Real.cos (p * t)) t
  have h := (radial_hasDerivAt t).mul (sin_mul_parameter_hasDerivAt p t)
  simpa [mul_comm, mul_left_comm, mul_assoc] using h

/-- The z component of `centerlineDerivative` is the derivative of the centreline z coordinate. -/
theorem centerline_z_hasDerivAt (t : ℝ) :
    HasDerivAt (fun s : ℝ => (centerline s).z) (centerlineDerivative t).z t := by
  change HasDerivAt
    (fun s : ℝ => minorRadius * Real.sin (q * s))
    (minorRadius * q * Real.cos (q * t)) t
  simpa [mul_comm, mul_left_comm, mul_assoc] using
    HasDerivAt.const_mul minorRadius (sin_mul_parameter_hasDerivAt q t)

/-- The declared vector is the actual centreline derivative, component by component. -/
theorem centerline_hasComponentDerivAt (t : ℝ) :
    HasDerivAt (fun s : ℝ => (centerline s).x) (centerlineDerivative t).x t ∧
    HasDerivAt (fun s : ℝ => (centerline s).y) (centerlineDerivative t).y t ∧
    HasDerivAt (fun s : ℝ => (centerline s).z) (centerlineDerivative t).z t := by
  exact ⟨centerline_x_hasDerivAt t, ⟨centerline_y_hasDerivAt t, centerline_z_hasDerivAt t⟩⟩

theorem derivative_sqNorm (t : ℝ) :
    Vec3.sqNorm (centerlineDerivative t) = speedSq t := by
  have hp := Real.sin_sq_add_cos_sq (p * t)
  have hq := Real.sin_sq_add_cos_sq (q * t)
  simp [centerlineDerivative, Vec3.sqNorm, Vec3.dot, speedSq, radialPrime]
  ring_nf at hp hq ⊢
  have hps : Real.sin (p * t) ^ 2 = 1 - Real.cos (p * t) ^ 2 := by
    nlinarith [hp]
  have hqs : Real.sin (t * q) ^ 2 = 1 - Real.cos (t * q) ^ 2 := by
    nlinarith [hq]
  rw [hps, hqs]
  ring

theorem speedSq_pos (t : ℝ) : 0 < speedSq t := by
  unfold speedSq q minorRadius
  positivity

theorem derivative_ne_zero (t : ℝ) : centerlineDerivative t ≠ Vec3.zero := by
  intro h
  have hs := derivative_sqNorm t
  rw [h] at hs
  simp [Vec3.sqNorm, Vec3.dot, Vec3.zero] at hs
  exact (ne_of_gt (speedSq_pos t)) hs.symm

/-- The centreline has the declared component derivatives, and that derivative vector never vanishes. -/
theorem centerline_regular_componentwise (t : ℝ) :
    centerlineDerivative t ≠ Vec3.zero ∧
    HasDerivAt (fun s : ℝ => (centerline s).x) (centerlineDerivative t).x t ∧
    HasDerivAt (fun s : ℝ => (centerline s).y) (centerlineDerivative t).y t ∧
    HasDerivAt (fun s : ℝ => (centerline s).z) (centerlineDerivative t).z t := by
  refine ⟨derivative_ne_zero t, ?_⟩
  exact centerline_hasComponentDerivAt t

theorem torusNormal_sqNorm (t : ℝ) : Vec3.sqNorm (torusNormal t) = 1 := by
  have hp := Real.sin_sq_add_cos_sq (p * t)
  have hq := Real.sin_sq_add_cos_sq (q * t)
  simp [torusNormal, Vec3.sqNorm, Vec3.dot]
  ring_nf at hp hq ⊢
  have hps : Real.sin (p * t) ^ 2 = 1 - Real.cos (p * t) ^ 2 := by
    nlinarith [hp]
  have hqs : Real.sin (t * q) ^ 2 = 1 - Real.cos (t * q) ^ 2 := by
    nlinarith [hq]
  rw [hps, hqs]
  ring

theorem derivative_dot_torusNormal (t : ℝ) :
    Vec3.dot (centerlineDerivative t) (torusNormal t) = 0 := by
  have hp := Real.sin_sq_add_cos_sq (p * t)
  simp [centerlineDerivative, torusNormal, Vec3.dot, radialPrime]
  ring_nf at hp ⊢
  have hps : Real.sin (p * t) ^ 2 = 1 - Real.cos (p * t) ^ 2 := by
    nlinarith [hp]
  rw [hps]
  ring

end

end RSH.Gluball
