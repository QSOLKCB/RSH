# RSH v4.0.0 — Epistemic & Conformance Governance

RSH v4.0.0 adds explicit machine-readable epistemic and conformance governance while preserving the v3.0.0 mathematical theorem surface and the existing geometry/tissue contracts.

## New contract surfaces

- **`RSH-EPISTEMIC-V1`** separates epistemic state, evidence class, and permitted claim tier.
- **`RSH-CONFORMANCE-V1`** binds deterministic experiment receipts to explicit backend/runtime identity and enforces a no-silent-fallback boundary.

## Epistemic rules

v4 makes the following repository rules executable rather than merely rhetorical:

- model output is not execution evidence;
- formal syntax is not proof;
- unknown is not false;
- inferred material is not silently promoted to known;
- unresolved conflict blocks promotion;
- receipts establish declared identity/execution evidence, not physical truth;
- proof receipts certify the proposition checked by the proof system, not unrelated empirical interpretations.

No natural-language keyword or regex proof detector is used. Proof status must be supplied as explicit evidence metadata.

## Deterministic conformance envelopes

`src/rsh/governance.py` and the new `rsh-governance` Rust crate implement the same v1 envelope and sealed cross-runtime vector.

Each receipt binds experiment identity, SHA-256 input identity, backend, implementation name/version, source revision, explicit fallback state, deterministic parameters, seed, and portable observables.

Receipts use domain-separated SHA-256 over compact canonical UTF-8 JSON. Wall-clock time is excluded from canonical identity. Canonical text is restricted to printable ASCII excluding quote and backslash and the seed is restricted to `u64`, eliminating cross-runtime ambiguity in the v1 serializer contract.

A requested backend may not silently fall back to another backend. If fallback occurs it must be declared, and default conformance gates reject it unless explicitly permitted.

## Cross-runtime evidence

Python and Rust consume the same sealed governance vector:

`conformance/rsh_v4_governance_vector_v1.json`

Because runtime identity is intentionally bound into receipts, different runtimes are not falsely required to produce the same receipt. Cross-runtime acceptance compares the declared portable observables while retaining runtime-specific provenance.

## Preserved v3 authority

RSH v4.0.0 does **not** modify:

- geometry model contract `2.0.0`;
- tissue contract `1.0.0`;
- `RSH-FORMAL-V1`;
- the Lean v3.0.0 theorem files or proof-hole/axiom audit;
- the Python geometry oracle;
- accelerator residual-sidecar authority;
- physical, biological, consciousness, sentience, or empirical claim boundaries.

## Pattern provenance

The governance design is informed by substrate-descended patterns observed in the GhostIT Android archive. RSH independently reimplements the useful evidence/epistemic concepts. No GhostIT application code, text-proof heuristics, prototype cryptography, or fallback implementation is imported.

## Deferred GLUBALL integration

GLUBALL is intentionally **not** part of v4.0.0.

After v4.0.0 is merged, validated, and tagged, a later additive release may pin GLUBALL `v1.0.0` at commit:

`80941183d14531093117e122da0fc32c13d2464b`

and introduce the separate theorem surface:

`RSH-GLUBALL-FORMAL-V1`

The Robitaille–Slade helix and `RSH-FORMAL-V1` remain intact.

## Validation

Portable validation remains:

```bash
python -m unittest discover -s tests -v
cargo fmt --all -- --check
cargo clippy --locked --workspace --all-targets -- -D warnings
cargo test --locked --workspace
```

The v4 release contract additionally checks both machine-readable governance contracts, the release manifest, the sealed Python/Rust vector, software version separation, and the frozen `RSH-FORMAL-V1` marker.
