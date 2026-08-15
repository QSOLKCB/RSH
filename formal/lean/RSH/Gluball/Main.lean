import RSH.Gluball.Parameters
import RSH.Gluball.Vector
import RSH.Gluball.Centerline
import RSH.Gluball.Frame
import RSH.Gluball.Surface
import RSH.Gluball.Symmetry
import RSH.Gluball.Sampling

namespace RSH.Gluball

/-- Human-readable boundary marker: this theorem surface formalizes the frozen GLUBALL
geometry/sampling contract only. It does not assert physical interpretation or global
tube embeddedness. -/
def claimBoundary : String :=
  "frozen GLUBALL geometry and deterministic sampling; no empirical or global-embeddedness claim"

end RSH.Gluball
