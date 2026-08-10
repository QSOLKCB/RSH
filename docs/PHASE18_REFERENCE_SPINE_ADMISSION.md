# Phase 18 — Analytic reference spine and restricted-seed admission

## Status

Active first slice under the separately named research/evidence contract:

```text
RSH-REFERENCE-SPINE-V1
RSH-GAMMASEED-ADMISSION-V1
RSH-REFERENCE-SPINE-AUDIT-V1
```

This phase does **not** replace or revise the canonical RSH geometry contract.
The readable Python geometry oracle continues to construct its bounded path from
prescribed curvature and torsion schedules.  The analytic spine in this phase is
a separate reference/evidence surface.

## Frozen source seed

The audited analytic reference is

\[
r_*(t)=e^{\psi t}(\cos t,\sin t,t),
\qquad
\psi=\sqrt{2+\sqrt5},
\]

on the source seed interval

\[
0\le t\le 2\pi.
\]

The source record identifies `GammaSeed-restricted-v1` with

```text
baec1aa01299bb465be50e9685988f1d27c41fb97c40a4e2058660dc63ce2681
```

RSH records that identifier as source metadata.  RSH's own admission and audit
receipts use new domain-separated receipt namespaces and do not claim to
reproduce the source record's serialization or hash derivation.

## Closed-form curvature and torsion

Let `a = psi`.  Direct differentiation gives

\[
\kappa(t)^2=
\frac{(a^2+1)(a^2t^2+2a^2+2at+2)e^{-2at}}
{(a^2t^2+a^2+2at+2)^3},
\]

and

\[
\tau(t)=
\frac{(at+1)e^{-at}}
{a^2t^2+2a^2+2at+2}.
\]

For `a > 0` and `t >= 0`, both are strictly decreasing.  In particular,

\[
\frac{d}{dt}\kappa(t)^2
=
-\frac{2a(a^2+1)e^{-2at}P(t)}
{(a^2t^2+a^2+2at+2)^4},
\]

where

\[
P(t)=a^4t^4+3a^4t^2+2a^4+6a^3t^3+11a^3t
+14a^2t^2+11a^2+16at+8,
\]

and every term is non-negative with a positive constant term.  Likewise,

\[
\tau'(t)=
-\frac{ae^{-at}Q(t)}
{(a^2t^2+2a^2+2at+2)^2},
\]

with

\[
Q(t)=a^3t^3+2a^3t+4a^2t^2+6at+2>0.
\]

This monotonicity lets the interval admission certificate use endpoint extrema
rather than an unsealed sampling heuristic.

## Curvature correction and unique crossing

At the source origin,

```text
kappa(0) ~= 0.4755038230472298
sqrt(2)-1 ~= 0.4142135623730951
```

so the full source interval violates the RSH curvature constitution.

Because curvature is strictly decreasing on `t >= 0`, the equation

\[
\kappa(t_*)=\sqrt2-1
\]

has a unique crossing on `[0, 2*pi]`.  Deterministic binary64 bisection gives

```text
t_star ~= 0.04797981890307021
```

The admissible analytic seed is therefore

\[
[t_*,2\pi].
\]

Torsion is positive and decreasing throughout the seed and remains strictly
below one, so the correction is driven by the curvature ceiling rather than the
torsion window.

## Admission semantics

`RSH-GAMMASEED-ADMISSION-V1` records for a requested sub-interval:

- the frozen source-seed hash;
- `psi` and the constitutional curvature/torsion bounds;
- the unique `t_star` crossing;
- endpoint extrema justified by analytic monotonicity;
- separate curvature and torsion pass fields;
- `ADMIT` or `REFUSE` disposition;
- a domain-separated deterministic receipt;
- `geometry_contract_modified: false`;
- `geometry_receipt_authority: false`.

The default audit intentionally evaluates both cases:

```text
[0, 2*pi]       -> REFUSE
[t_star, 2*pi]  -> ADMIT
```

An audit passes when the full-domain refusal, restricted-domain admission,
unique crossing, and authority boundaries are all reproduced.

## CLI

Run the audit directly from a source checkout:

```bash
python3 rsh_runner.py spine-admission
python3 rsh_runner.py spine-admission --json rsh_spine_admission.json
```

The command exits successfully only when the audit itself passes.  A successful
audit therefore does **not** mean that the full source interval is admitted; it
means the expected full-domain refusal and restricted-domain admission were both
reproduced.

## Authority boundary

This phase does not modify:

- `RSH-GEOMETRY-EVIDENCE-V2`;
- the prescribed canonical `kappa(s)` or `tau(s)` schedules;
- midpoint Frenet–Serret integration;
- midpoint coordinate normalisation;
- geometry receipt authority;
- tissue, numerical, parallel, CUDA, or other existing contracts.

The analytic reference spine may later seed a separately named dynamical
regulator contract only after that regulator's equations and theorem claims are
hardened independently.

## Required next steps before dynamical closure

Do not promote the dissertation's regulator claims directly into production.
The next contract must first resolve and freeze:

1. the difference between the stated core operator
   `R = psi + n*tau/kappa` and the regularized/observed operator using
   `kappa + epsilon_0` and `-lambda*sigma(r)`;
2. the printed `n` evolution term whose current `(kappa-kappa)` factor is
   identically zero unless one symbol is intended to be `kappa_*`;
3. the exact positive/negative-part convention in the torsion correction;
4. the definition and regularity assumptions for `T(r)` and `sigma(r)`;
5. the distinction between the open constitutional torsion interval `(0,1)`
   and projection onto its closure;
6. a valid source of transverse contraction before claiming a Hurwitz
   Frenet–Serret normal block or exponential tube stability.

Until those points are sealed, regulator and Lyapunov results remain a queued
research contract rather than geometry authority.
