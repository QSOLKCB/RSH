import Mathlib

namespace RSH.Gluball

/-- Additive Lean theorem-surface marker for the frozen GLUBALL handoff. -/
def formalContract : String := "RSH-GLUBALL-FORMAL-V1"

/-- Frozen upstream GLUBALL release imported by this theorem surface. -/
def sourceRelease : String := "v1.0.0"

/-- Exact commit targeted by the frozen GLUBALL v1.0.0 release. -/
def sourceCommit : String := "80941183d14531093117e122da0fc32c13d2464b"

/-- RSH release boundary on which the additive formalization is based. -/
def rshBaseRelease : String := "v4.0.0"

def rshBaseCommit : String := "79b8481639fb4187c41035de4e707545db93f59a"

/-- Torus-knot winding numbers from `GLUBALL-KNOT-V1`. -/
def p : ℝ := 2
def q : ℝ := 3

/-- Exact rational forms of the frozen decimal geometry parameters. -/
def majorRadius : ℝ := 21 / 10
def minorRadius : ℝ := 17 / 20
def tubeRadius : ℝ := 17 / 50

/-- Frozen renderer mesh cardinalities; these are execution metadata, not topology. -/
def uSegments : ℕ := 96
def vSegments : ℕ := 18

theorem majorRadius_pos : 0 < majorRadius := by norm_num [majorRadius]
theorem minorRadius_pos : 0 < minorRadius := by norm_num [minorRadius]
theorem majorRadius_gt_minorRadius : minorRadius < majorRadius := by norm_num [majorRadius, minorRadius]
theorem tubeRadius_pos : 0 < tubeRadius := by norm_num [tubeRadius]
theorem tubeRadius_lt_minorRadius : tubeRadius < minorRadius := by norm_num [tubeRadius, minorRadius]
theorem p_pos : 0 < p := by norm_num [p]
theorem q_pos : 0 < q := by norm_num [q]

end RSH.Gluball
