# RSH v4.1.0 — GLUBALL Machine-Checked Geometry

RSH v4.1.0 adds the additive Lean theorem surface `RSH-GLUBALL-FORMAL-V1` while preserving the existing Robitaille–Slade theorem surface, geometry contracts, governance contracts, numerical research contracts, and implementation authority boundaries.

This release is pinned to:

- RSH v4.0.0: `79b8481639fb4187c41035de4e707545db93f59a`
- GLUBALL v1.0.0: `80941183d14531093117e122da0fc32c13d2464b`
- merged GLUBALL formalization: `124af8283dd69f78031d3a92249fdd7ea4a60508`
- v4.1.0 release-prep merge: `f6fc36fe0dd19af6bc6247d4e9f4a19f2500573e`
- Zenodo version DOI: `10.5281/zenodo.21959297`

## New theorem surface

The new theorem surface is:

```text
RSH-GLUBALL-FORMAL-V1
```

It coexists with, and does not replace or reinterpret:

```text
RSH-FORMAL-V1
```

The GLUBALL theorem modules live under `formal/lean/RSH/Gluball/` and are included in the existing proof-hole, project-axiom, build, and axiom-report audit.

## Machine-checked results

For the frozen GLUBALL `(2,3)` torus-curve contract with exact rational parameters corresponding to `R = 2.10`, `r = 0.85`, `rho = 0.34`, `p = 2`, and `q = 3`, Lean checks:

- exact parameter admissibility;
- the declared centreline and its componentwise derivatives;
- `HasDerivAt` linkage between the declared derivative and the actual centreline coordinates;
- the exact squared-speed identity;
- strict positivity of squared speed and non-vanishing derivative;
- host-torus normal unit norm;
- tangent/normal orthogonality;
- normalized tangent and binormal unit-norm properties;
- pairwise frame orthogonality;
- the exact squared tube-radius invariant;
- periodicity in the tube-angle coordinate;
- centreline closure;
- exact C3 rotational symmetry;
- exact uniform-floor sampling bounds;
- adjacent rendered-sample collision freedom when rendered cardinality does not exceed logical cardinality;
- finite `96 × 18` mesh-index wrap bounds.

## Derivative linkage hardening

The formalization does not merely define a vector and call it the derivative. Following review, the Lean development proves `radial_hasDerivAt`, the x/y/z centreline component derivative theorems, `centerline_hasComponentDerivAt`, and `centerline_regular_componentwise`.

This closes the gap between the written closed-form derivative and the actual curve being formalized.

## Audit provenance hardening

The theorem audit retains the immutable RSH v4 base pin and additionally records the actual audited source revision and workflow checkout revision. Pull-request workflows pass the PR head SHA explicitly so a synthetic GitHub merge ref cannot obscure which source revision was audited.

The audit continues to reject:

- `sorry`;
- `admit`;
- project-defined `axiom` declarations;
- project-defined `constant` declarations.

Lean remains pinned to 4.32.1 and Mathlib remains pinned to commit `520045ab14e26149ee970e2e617ca04b09bde5d6`.

## Preserved governance and scientific authority

RSH v4.1.0 preserves:

- geometry model contract `2.0.0`;
- tissue contract `1.0.0`;
- `RSH-FORMAL-V1`;
- `RSH-EPISTEMIC-V1`;
- `RSH-CONFORMANCE-V1`;
- `RSH-FRENET-NUMERICS-V1`;
- `RSH-FRENET-PARALLEL-V1`;
- the Python geometry oracle;
- runtime-specific conformance and accelerator residual-sidecar boundaries.

The GLUBALL browser renderer is not promoted to mathematical authority.

## Deliberate nonclaims

This release does not claim that Lean has proved:

- global thick-tube embeddedness or non-self-intersection;
- IEEE-754 or binary64 equivalence across runtimes;
- bit-identical browser rendering;
- GPU, WASM, Android, CUDA, WebGPU, or NPU implementation correctness outside their declared conformance surfaces;
- experimental or empirical physics;
- biological interpretation;
- consciousness, sentience, subjective awareness, or qualia;
- ternary/triality topology.

A proof receipt certifies the proposition checked by Lean. It does not silently become an empirical measurement.

## Release and archival metadata

The Python package and Rust workspace advance to `4.1.0`. `CITATION.cff`, `.zenodo.json`, and `release/manifest-v4.1.0.json` describe the additive formalization and preserve the exact RSH/GLUBALL source boundaries.

The reserved Zenodo version DOI for this release is:

```text
10.5281/zenodo.21959297
```

`CITATION.cff` and the machine-readable release manifest bind that DOI to v4.1.0 before the Git tag is created. The DOI reservation itself is archival identity metadata; it does not change any theorem statement or scientific authority boundary.

The v4.1.0 tag must resolve to the final merge commit containing the release manifest and DOI pin after portable CI and the Lean theorem audit are green.

## Reproduce the theorem audit

```bash
cd formal/lean
lake update
lake exe cache get
bash audit.sh
```

## Authors and contribution

- **Dr. J. Robitaille** — author
- **Trent Slade** — author
- **ChatGPT 5.6 Sol** — contributor (formalization implementation and proof-engineering assistance)

The AI contribution is recorded as a contributor role rather than a human creator/author.
