import Mathlib

namespace RSH.Admission

/-- Pointwise constitutional bounds on an interval. -/
def BoundsHold (κ τ : ℝ → ℝ) (t0 t1 κmax : ℝ) : Prop :=
  ∀ t, t0 ≤ t → t ≤ t1 →
    0 ≤ κ t ∧ κ t ≤ κmax ∧ 0 < τ t ∧ τ t < 1

/-- For strictly decreasing κ and τ, endpoint evidence certifies the full interval. -/
theorem endpoint_certificate
    {κ τ : ℝ → ℝ} {t0 t1 κmax : ℝ}
    (hκ : StrictAnti κ) (hτ : StrictAnti τ)
    (hκmax : κ t0 ≤ κmax) (hκmin : 0 ≤ κ t1)
    (hτmax : τ t0 < 1) (hτmin : 0 < τ t1) :
    BoundsHold κ τ t0 t1 κmax := by
  intro t ht0 ht1
  have hkUpper : κ t ≤ κ t0 := hκ.antitone ht0
  have hkLower : κ t1 ≤ κ t := hκ.antitone ht1
  have htUpper : τ t ≤ τ t0 := hτ.antitone ht0
  have htLower : τ t1 ≤ τ t := hτ.antitone ht1
  exact ⟨
    le_trans hκmin hkLower,
    le_trans hkUpper hκmax,
    lt_of_lt_of_le hτmin htLower,
    lt_of_le_of_lt htUpper hτmax
  ⟩

/-- A seed whose starting curvature is above the ceiling must be refused. -/
theorem refuse_if_start_above
    {κ τ : ℝ → ℝ} {t0 t1 κmax : ℝ}
    (ht : t0 ≤ t1) (habove : κmax < κ t0) :
    ¬ BoundsHold κ τ t0 t1 κmax := by
  intro h
  have hstart := h t0 le_rfl ht
  exact (not_lt_of_ge hstart.2.1) habove

/-- Strict antitonicity makes a curvature-bound crossing unique. -/
theorem crossing_unique
    {κ : ℝ → ℝ} (hκ : StrictAnti κ) {tstar κmax t : ℝ}
    (hstar : κ tstar = κmax) (ht : κ t = κmax) :
    t = tstar := by
  apply hκ.injective
  calc
    κ t = κmax := ht
    _ = κ tstar := hstar.symm

/-- Polynomial appearing in the analytic torsion derivative-sign certificate. -/
def tauDerivativeSignPolynomial (a t : ℝ) : ℝ :=
  a ^ 3 * t ^ 3 + 2 * a ^ 3 * t + 4 * a ^ 2 * t ^ 2 + 6 * a * t + 2

/-- The torsion derivative-sign polynomial is strictly positive for a>0 and t≥0. -/
theorem tauDerivativeSignPolynomial_pos
    {a t : ℝ} (ha : 0 < a) (ht : 0 ≤ t) :
    0 < tauDerivativeSignPolynomial a t := by
  dsimp [tauDerivativeSignPolynomial]
  positivity

end RSH.Admission
