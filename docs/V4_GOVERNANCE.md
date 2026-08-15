# RSH v4.0.0 — Epistemic and Conformance Governance

RSH v4 adds two machine-readable governance surfaces without changing the Robitaille–Slade geometry equations, the tissue contract, or the Lean theorem surface released in v3.0.0.

```text
RSH-EPISTEMIC-V1
RSH-CONFORMANCE-V1
```

The purpose is simple: make it difficult for a model, tool, adapter, or future maintainer to accidentally promote the wrong kind of evidence into a stronger scientific claim.

## RSH-EPISTEMIC-V1

The epistemic contract distinguishes state, evidence class, and claim tier.

States: `KNOWN`, `RETRIEVED`, `INFERRED`, `UNKNOWN`, `CONFLICT`, `FICTION`.

Evidence classes: `MODEL_PROPOSAL`, `TOOL_RECEIPT`, `MEASUREMENT`, `FORMAL_SYNTAX`, `PROOF_RECEIPT`, `REJECTED`.

Claim tiers: `PROPOSAL`, `HYPOTHESIS`, `EVIDENCE_BACKED`, `VERIFIED`, `BLOCKED`.

The classifier consumes explicit metadata only. It does **not** scan prose for words such as “proof”, “QED”, “therefore”, or similar cues. Formal-looking text remains `FORMAL_SYNTAX` until a declared proof system actually checks the stated proposition and a proof receipt is supplied.

Important consequences:

- model output is not execution evidence;
- formal syntax is not proof;
- unknown is not false;
- inference is not silently promoted to known;
- material conflict blocks promotion until resolved;
- fiction remains nonliteral;
- a receipt proves identity/execution under its declared contract, not empirical truth;
- a Lean proof certifies the proposition Lean checked, not an unrelated physical interpretation.

## RSH-CONFORMANCE-V1

Every canonical v4 conformance envelope binds experiment name, SHA-256 input identity, backend identity, implementation name/version, source revision, explicit fallback state, deterministic parameters, a non-negative `u64` seed, and declared portable observables.

The receipt is:

```text
SHA256("RSH-CONFORMANCE-V1\0" || canonical_utf8_json)
```

Canonical textual fields use a deliberately conservative printable-ASCII domain (U+0020 through U+007E, excluding quote and backslash) so independently implemented Python and Rust serializers cannot disagree over escaping while claiming the same canonical byte contract.

The canonical envelope deliberately excludes wall-clock time. Time may be recorded in a noncanonical observation sidecar, but changing the clock must not change the deterministic identity of an otherwise identical experiment.

### No silent fallback

A run that requested one backend but executed another must say so. `fallback_used=true` requires `fallback_from`, and conformance gates reject declared fallback by default unless the caller explicitly permits it.

A backend mismatch fails closed. “CUDA unavailable, used CPU instead” is useful diagnostic information; it is not evidence that CUDA executed.

### Cross-runtime comparison

Runtime identity is part of the receipt, so Python and Rust receipts are not required to be identical. Cross-runtime conformance compares the declared portable observables from equivalent experiment envelopes. This preserves runtime provenance instead of erasing it to manufacture equal hashes.

The sealed synthetic vector in `conformance/rsh_v4_governance_vector_v1.json` is consumed by both Python and Rust tests. It verifies canonical bytes, SHA-256 receipt generation, ordered ledger digest, and representative claim-promotion rules. The vector is a serialization/conformance fixture, not empirical or hardware evidence.

## Existing authority is unchanged

RSH v4 does not change:

- geometry model contract `2.0.0`;
- canonical Python geometry oracle;
- tissue contract `1.0.0`;
- `RSH-FORMAL-V1`;
- the v3.0.0 Lean source or axiom-audit policy;
- accelerator residual-sidecar status;
- physical/non-physical claim boundaries.

The Lean project intentionally remains versioned at v3.0.0 because v4 adds no new theorem to `RSH-FORMAL-V1`.

## Pattern provenance

The design was informed by substrate-descended epistemic/evidence patterns observed while auditing the GhostIT Android archive. RSH reimplements the useful concepts for its own research authority model. GhostIT application code, text heuristics, prototype cryptography, and runtime-specific shortcuts are not imported.

## GLUBALL comes after the v4 freeze

GLUBALL is deliberately absent from v4.0.0. After this release is merged, validated, and tagged as `v4.0.0`, a separate additive RSH release may pin GLUBALL `v1.0.0` at commit `80941183d14531093117e122da0fc32c13d2464b` and introduce `RSH-GLUBALL-FORMAL-V1`.

That future integration must use the v4 epistemic/conformance rules rather than bypassing them.
