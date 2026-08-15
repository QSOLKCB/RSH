import RSH.Gluball.Parameters

namespace RSH.Gluball

/-- Exact natural-number model of `GLUBALL-SAMPLING-V1` uniform-floor sampling. -/
def uniformFloor (logicalCount renderedCount renderedIndex : ℕ) : ℕ :=
  renderedIndex * logicalCount / renderedCount

@[simp] theorem uniformFloor_zero (logicalCount renderedCount : ℕ) :
    uniformFloor logicalCount renderedCount 0 = 0 := by
  simp [uniformFloor]

/-- Every declared rendered index maps inside the logical field. -/
theorem uniformFloor_lt_logical
    {logicalCount renderedCount renderedIndex : ℕ}
    (hLogical : 0 < logicalCount)
    (hRendered : 0 < renderedCount)
    (hIndex : renderedIndex < renderedCount) :
    uniformFloor logicalCount renderedCount renderedIndex < logicalCount := by
  apply (Nat.div_lt_iff_lt_mul hRendered).2
  have h := Nat.mul_lt_mul_of_pos_right hIndex hLogical
  simpa [uniformFloor, Nat.mul_comm, Nat.mul_left_comm, Nat.mul_assoc] using h

/-- When `renderedCount ≤ logicalCount`, each adjacent rendered slot advances by at least one logical index. -/
theorem uniformFloor_succ_le
    {logicalCount renderedCount renderedIndex : ℕ}
    (hRendered : 0 < renderedCount)
    (hBound : renderedCount ≤ logicalCount) :
    uniformFloor logicalCount renderedCount renderedIndex + 1 ≤
      uniformFloor logicalCount renderedCount (renderedIndex + 1) := by
  have hnum : renderedIndex * logicalCount + renderedCount ≤
      (renderedIndex + 1) * logicalCount := by
    calc
      renderedIndex * logicalCount + renderedCount ≤
          renderedIndex * logicalCount + logicalCount := Nat.add_le_add_left hBound _
      _ = (renderedIndex + 1) * logicalCount := by ring
  have hdiv :
      (renderedIndex * logicalCount + renderedCount) / renderedCount ≤
        ((renderedIndex + 1) * logicalCount) / renderedCount :=
    Nat.div_le_div_right hnum
  rw [Nat.add_div_right (renderedIndex * logicalCount) renderedCount]
  simpa [uniformFloor] using hdiv

/-- Adjacent rendered indices are collision-free under the canonical domain restriction. -/
theorem uniformFloor_succ_lt
    {logicalCount renderedCount renderedIndex : ℕ}
    (hRendered : 0 < renderedCount)
    (hBound : renderedCount ≤ logicalCount) :
    uniformFloor logicalCount renderedCount renderedIndex <
      uniformFloor logicalCount renderedCount (renderedIndex + 1) := by
  exact Nat.lt_of_succ_le (uniformFloor_succ_le hRendered hBound)

/-- Frozen mesh indices wrap into their declared finite ranges. -/
theorem u_wrap_lt (i : ℕ) : i % uSegments < uSegments := by
  exact Nat.mod_lt _ (by norm_num [uSegments])

theorem v_wrap_lt (j : ℕ) : j % vSegments < vSegments := by
  exact Nat.mod_lt _ (by norm_num [vSegments])

end RSH.Gluball
