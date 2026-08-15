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
