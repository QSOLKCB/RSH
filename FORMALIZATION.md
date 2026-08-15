# RSH Formalization

RSH maintains separately versioned machine-checked theorem surfaces. The existing Robitaille–Slade theorem surface remains:

```text
RSH-FORMAL-V1
```

The additive GLUBALL integration introduces:

```text
RSH-GLUBALL-FORMAL-V1
```

The two surfaces coexist. The GLUBALL work does **not** replace, reinterpret, or weaken `RSH-FORMAL-V1`.

`RSH-GLUBALL-FORMAL-V1` is packaged for archival release in RSH v4.1.0. The release number is software/archive metadata; the theorem-surface identifiers remain the authority boundary for the propositions Lean actually checks.

## Authors and contribution

- **Dr. J. Robitaille** — author
- **Trent Slade** — author
- **ChatGPT 5.6 Sol Thinking** — contributor (formalization implementation and proof-engineering assistance)

The AI contribution is recorded as a contributor role, not as a human creator/author.

## Frozen source boundaries

`RSH-GLUBALL-FORMAL-V1` is based on two published release boundaries:

```text
RSH v4.0.0
79b8481639fb4187c41035de4e707545db93f59a

GLUBALL v1.0.0
80941183d14531093117e122da0fc32c13d2464b
```

The imported GLUBALL geometry is the frozen GLUBALL `v1.0.0` `(2,3)` torus-curve contract at the exact commit above, with exact rational parameter values corresponding to:

```text
R   = 2.10
r   = 0.85
rho = 0.34
p   = 2
q   = 3
```

The formal development models those decimal constants as exact rationals. It does not import the browser renderer as mathematical authority.

## RSH-FORMAL-V1

The original theorem surface, introduced in RSH v3.0.0, remains unchanged. It includes machine-checked propositions for:

- exact inversive witness geometry;
- the exact invariant `r²(T_f(c)) r²(c) = 1/9`;
- involutive fibre transformations;
- `2^32 < 3^21` and the associated unsigned-32 / 21-trit capacity embedding;
- six Frenet–Serret orthonormal-constraint compatibility identities;
- exact midpoint translation;
- monotone admission/refusal/uniqueness results;
- positivity of the torsion derivative-sign polynomial used by the analytic-spine certificate.

These existing statements remain under `formal/lean/RSH/` and retain the marker `RSH-FORMAL-V1`.

## RSH-GLUBALL-FORMAL-V1

The additive theorem surface lives under:

```text
formal/lean/RSH/Gluball/
```

### Exact parameter admissibility

Lean checks the frozen parameter inequalities exactly, including:

- `R > r > 0`;
- `0 < rho < r`;
- positive winding numbers `p = 2`, `q = 3`.

### Centreline and regularity

For

\[
A(t)=R+r\cos(qt)
\]

and

\[
C(t)=(A(t)\cos(pt),A(t)\sin(pt),r\sin(qt)),
\]

Lean formalizes the declared derivative, proves `HasDerivAt` for each centreline component, and therefore connects the closed-form derivative to the actual curve rather than treating it as an independent trusted definition. It also proves the squared-speed identity

\[
\|C'(t)\|^2=p^2A(t)^2+q^2r^2.
\]

Because the second term is strictly positive for the frozen parameters, Lean proves the squared speed is positive and therefore `C'(t)` is never the zero vector.

### Host-torus frame

For the host-torus normal

\[
N(t)=(\cos(qt)\cos(pt),\cos(qt)\sin(pt),\sin(qt)),
\]

Lean proves:

- `||N(t)||² = 1`;
- `C'(t) · N(t) = 0`;
- the normalized tangent has unit squared norm;
- the normalized cross-product binormal has unit squared norm;
- tangent, normal, and binormal are pairwise orthogonal.

The GLUBALL frame therefore does not depend on introducing a Frenet-normal assumption.

### Tube surface

For

\[
G(t,v)=C(t)+\rho\bigl(N(t)\cos v+B(t)\sin v\bigr),
\]

Lean proves the exact squared tube-radius invariant

\[
\|G(t,v)-C(t)\|^2=\rho^2,
\]

and periodicity in the tube angle `v`.

### Closure and C3 symmetry

Lean proves the frozen centreline identities:

\[
C(t+2\pi)=C(t)
\]

and

\[
C(t+2\pi/3)=R_z(4\pi/3)C(t).
\]

The C3 statement is an exact rotational-symmetry theorem for the declared centreline; it is not a claim about physical threefold symmetry in nature.

### Deterministic sampling

The theorem-facing model of `GLUBALL-SAMPLING-V1` uses exact natural-number division:

```text
uniformFloor(L,R,i) = floor(i * L / R)
```

Lean proves:

- the zero rendered index maps to zero;
- every declared rendered index maps below the logical cardinality;
- when `R <= L`, adjacent rendered indices advance by at least one logical index and are therefore collision-free;
- the frozen mesh wrap operations remain inside their `96` and `18` index ranges.

Ternary/triality metadata remains explicitly non-topological and is not promoted into this theorem surface.

## Deliberate nonclaims

Neither theorem surface claims that Lean has established:

- IEEE-754/binary64 execution equivalence for Python, Rust, JavaScript, Kotlin, WASM, C++, CUDA, WebGPU, or Android;
- bit-identical browser rendering or encoded PNG/WebM output;
- empirical or experimental physics;
- biological, consciousness, sentience, or qualia interpretations;
- global embeddedness/non-self-intersection of the complete thick GLUBALL tube.

Global tube embeddedness remains a separate theorem target and is **not** smuggled into the release by the local frame/radius proofs.

RSH v4 governance continues to distinguish proof receipts, tool receipts, measurements, model proposals, and inference. A successful Lean build proves only the propositions checked by the Lean kernel.

## Reproducibility

The formal project remains pinned to:

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

The audit fails on `sorry`, `admit`, or project-defined `axiom`/`constant` declarations across the root `RSH.lean` module and the complete `RSH/` module tree. It builds the complete library and prints Lean's axiom report for both advertised theorem surfaces.

## Formal source map

```text
formal/lean/RSH/Algebra.lean            Exact rational vector algebra
formal/lean/RSH/ExactSpatial.lean       Exact inversive witness and word-capacity theorems
formal/lean/RSH/FrenetSerret.lean       Exact frame-constraint compatibility and centring
formal/lean/RSH/Admission.lean          Monotone admission/refusal/uniqueness theorems
formal/lean/RSH/Main.lean               RSH-FORMAL-V1 marker

formal/lean/RSH/Gluball/Parameters.lean Frozen release pins and exact parameters
formal/lean/RSH/Gluball/Vector.lean     Exact real three-vector algebra
formal/lean/RSH/Gluball/Centerline.lean Centreline, derivative, speed, host normal
formal/lean/RSH/Gluball/Frame.lean      Tangent/binormal normalization and orthogonality
formal/lean/RSH/Gluball/Surface.lean    Tube surface and radius invariant
formal/lean/RSH/Gluball/Symmetry.lean   Closure and exact C3 rotation
formal/lean/RSH/Gluball/Sampling.lean   Exact uniform-floor and wrap properties
formal/lean/RSH/Gluball/Main.lean       RSH-GLUBALL-FORMAL-V1 assembly

formal/lean/RSH/AxiomAudit.lean          Published theorem axiom report
formal/lean/audit.sh                     Proof-hole, axiom, build, and report gate
```

## Citation boundary

For Zenodo, Dr. J. Robitaille and Trent Slade are the software/research creators. `ChatGPT 5.6 Sol Thinking` is recorded separately as a contributor. This preserves the distinction between human authorship and AI-assisted proof engineering.
