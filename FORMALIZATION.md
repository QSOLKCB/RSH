# RSH v3.0.0 Formalization

RSH v3.0.0 introduces `RSH-FORMAL-V1`, the first machine-checked theorem surface for the Robitaille–Slade Helix project.

## Authors and contribution

- **Dr. J. Robitaille** — author
- **Trent Slade** — author
- **ChatGPT 5.6 Sol Thinking** — contributor (formalization implementation and proof engineering assistance)

The AI contribution is recorded as a contributor role, not as a human creator/author.

## Scope

The Lean development is intentionally narrower than the complete RSH software platform. It formalizes theorem-shaped invariants that can be stated independently of Python, Rust, WebAssembly, CUDA, WebGPU, operating-system behavior, binary64 rounding, or receipt serialization.

The release theorem surface is named:

```text
RSH-FORMAL-V1
```

and lives under `formal/lean/`.

## Machine-checked results

### 1. Exact inversive witness geometry

The formalization models the three fibre-selected median reflections used by `RSH-F32-SIERPINSKI-INVERSIVE-WITNESS-V1` and the centred rational transformation

\[
T_f(c)=\frac{6}{\lVert c\rVert^2}P_f(c),
\]

where `P_f` is one of the three involutive coordinate reflections.

Lean proves:

- every selected reflection is an involution;
- every selected reflection preserves squared norm;
- the transformed squared norm is exactly `36 / ||c||²` when `||c||² != 0`;
- with `radiusSq(c) = ||c||² / 18`, the exact product invariant is

  \[
  r^2(T_f(c))\,r^2(c)=\frac{1}{9};
  \]

- applying the same transformation twice recovers the exact source point:

  \[
  T_f(T_f(c))=c.
  \]

These proofs are over exact rational arithmetic. They do not rely on floating-point tolerances.

### 2. Unsigned-32 / 21-trit address capacity

Lean proves the exact arithmetic fact

```text
2^32 < 3^21
```

and constructs an injective embedding of the RSH unsigned-32 word domain into the numeric capacity represented by 21 ternary digits.

This is a capacity/injectivity theorem. It does **not** yet formalize the implementation's concrete base-3 digit extraction procedure; that remains a later theorem surface.

### 3. Frenet–Serret orthonormal-constraint compatibility

For an exact orthonormal frame `(T,N,B)` and the Frenet–Serret vector field

\[
T'=\kappa N,\qquad
N'=-\kappa T+\tau B,\qquad
B'=-\tau N,
\]

Lean proves the six algebraic compatibility identities corresponding to preservation of the three unit-norm and three pairwise-orthogonality constraints.

This establishes that the exact Frenet–Serret vector field is tangent to the orthonormal-frame constraint surface. It does not claim bit-for-bit correctness of the binary64 midpoint integrator or its numerical re-orthonormalization policy.

### 4. Exact midpoint translation identity

Lean proves the coordinate-normalization identity

\[
p-p=0,
\]

which is the theorem-facing core of RSH's exact discrete midpoint translation convention. The software still bears responsibility for selecting the intended discrete midpoint sample.

### 5. Admission logic

For strictly decreasing curvature and torsion schedules, Lean proves:

- endpoint bounds certify the complete closed interval;
- if the initial curvature already exceeds the constitutional ceiling, the interval cannot satisfy the contract;
- a crossing of a strictly decreasing curvature function with a fixed ceiling is unique.

The analytic-spine module also formalizes and proves positivity of the polynomial used by RSH's torsion derivative-sign certificate for `a > 0` and `t >= 0`.

## What v3.0.0 does not claim

The formalization deliberately does not claim:

- that Lean has certified IEEE-754/binary64 execution of the Python or Rust numerical implementations;
- that receipts or hashes establish physical truth;
- that CUDA, WebGPU, NPU, WASM, or C++ implementations become scientific authority;
- that the complete analytic derivative of the reference-spine curvature has already been formalized;
- that existence of the numerical value of the unique curvature crossing has been proved from the full closed-form analytic spine in Lean;
- that the tissue model is biological, conscious, sentient, or a model of qualia;
- that experimental physics has been validated by these software theorems.

The existing RSH authority hierarchy remains unchanged: machine proofs certify stated mathematical propositions; runtime conformance certifies declared implementation observables; neither silently promotes a physical interpretation.

## Reproducibility

The formal project pins:

```text
Lean:    4.32.1
Mathlib: 520045ab14e26149ee970e2e617ca04b09bde5d6 (v4.32.1)
```

Build and audit:

```bash
cd formal/lean
lake update
lake exe cache get
bash audit.sh
```

The audit fails on `sorry`, `admit`, or project-defined `axiom`/`constant` declarations across both the root `RSH.lean` module and the `RSH/` module tree, builds the complete library, and prints Lean's axiom report for the advertised release theorem surface. By default, the generated report is written under `${TMPDIR:-/tmp}` rather than into the source tree; CI likewise writes it under the runner temp directory before publishing the report to the job summary.

## Formal source map

```text
formal/lean/RSH/Algebra.lean       Exact rational vector algebra
formal/lean/RSH/ExactSpatial.lean Exact inversive witness and word-capacity theorems
formal/lean/RSH/FrenetSerret.lean Exact frame-constraint compatibility and centring
formal/lean/RSH/Admission.lean    Monotone admission/refusal/uniqueness theorems
formal/lean/RSH/Main.lean         RSH-FORMAL-V1 theorem surface
formal/lean/RSH/AxiomAudit.lean   Published theorem axiom report
formal/lean/audit.sh              Proof-hole, axiom, build, and report gate
```

## Citation boundary

For Zenodo, Dr. J. Robitaille and Trent Slade are the software/research creators. `ChatGPT 5.6 Sol Thinking` is recorded separately as a contributor. This preserves the distinction between human authorship and AI-assisted proof engineering.
