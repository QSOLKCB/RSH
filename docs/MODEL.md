# RSH mathematical model

## Constants

The model fixes

\[
\psi = \sqrt{2+\sqrt{5}}
\]

and the curvature ceiling

\[
0 \leq \kappa(s) \leq \sqrt{2}-1.
\]

Torsion remains strictly inside

\[
0 < \tau(s) < 1.
\]

The default schedules are

\[
\kappa(s)=0.85(\sqrt{2}-1)\left[0.92+0.08\cos(0.35\psi s)\right],
\]

\[
\tau(s)=0.22+0.13\left[1+\sin(0.25\psi s)\right].
\]

The parameter values are defaults, not universal physical constants.

## Frenet–Serret construction

For tangent \(T\), normal \(N\), binormal \(B\), and path \(x\), RSH integrates

\[
x' = T,
\qquad
T' = \kappa N,
\qquad
N' = -\kappa T + \tau B,
\qquad
B' = -\tau N.
\]

A midpoint/Heun update is used. The frame is re-orthonormalised after every
step to limit floating-point drift.

## Centre convention

The discrete sample count is odd, so \(p=0.5\) exists exactly. After integration,
the path is translated by the negative of that sample's position. Therefore the
central sample is exactly the coordinate origin.

This is an explicit coordinate normalisation. `centre_error = 0` verifies that
the requested normalisation was applied correctly; it is not evidence that an
unconstrained system spontaneously found the origin.

## Exact bounded logical sampling

For a logical cardinality \(L\) and a rendered count \(N\), representative index
\(i\) is

\[
q_i = \left\lfloor \frac{iL}{N}\right\rfloor,
\qquad 0 \le i < N.
\]

The implementation uses integer multiplication and division, and never creates
an allocation proportional to \(L\).
