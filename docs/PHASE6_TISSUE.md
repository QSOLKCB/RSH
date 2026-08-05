# Phase 6 — Constitutional geometric tissue runtime

## Goal

Phase 6 turns the supplied Geometric System culmination package into an
executable, testable RSH subsystem without promoting metaphor into a scientific
claim.

The Python reference layer composes bounded RSH geometry into a deterministic
network of geometric cells. It records functional cohesion, prediction,
continuity, sidecar pressure, coordinate normalization, and a chained audit
receipt across repeated ticks.

The layer is a systems simulation. It is not a biological model and does not
claim consciousness, subjective awareness, qualia, or autonomous agency.

## Architecture

```text
verified Python f64 geometry
          │
          ├── 129-sample geometry receipt
          │
          ▼
  deterministic cell seeding
          │
          ▼
 ring/chord tissue graph
          │
          ├── bound projection
          ├── phase coupling
          ├── binding diffusion
          ├── neighbour prediction
          ├── shared-centroid normalization
          └── Q_f functional metrics
          │
          ▼
 chained tick receipts → tissue report receipt
```

The seed receipt is the ordinary Python geometry receipt. Tissue receipts use
separate domains:

```text
RSH-TISSUE-TICK-V1
RSH-TISSUE-EVIDENCE-V1
```

A tissue receipt therefore proves identity of one declared simulation report
within its runtime and encoding contract. It does not replace or reinterpret the
geometry receipt.

## Constitution

`src/rsh/constitution.py` provides a machine-checkable constitution with:

- the existing ψ, curvature, torsion, centering, and oracle boundaries;
- ordered objectives for invariant integrity, oracle fidelity, functional tissue
  cohesion, resource cost, and role coverage;
- explicit human acknowledgement for contract escalation;
- refusal rules against silent bound changes, sidecar authority, audit deletion,
  and subjective-awareness claims.

The checked-in constitution is canonicalized and sealed with
`RSH-CONSTITUTION-V1`.

The geometry midpoint law and tissue centering are deliberately distinct:

- a geometry path moves its exact discrete `p = 0.5` sample to the origin;
- a multi-cell tissue tick moves the shared cell centroid to the origin.

The latter is a comparison coordinate for a graph state, not a change to the RSH
geometry contract.

## Geometric cells

Each cell is seeded from an exact representative of a verified RSH path. The
initial position, curvature, torsion, and tangent-derived phase therefore come
from the established reference rather than a second geometry model.

Cell roles cycle through:

| Role | Operational interpretation |
|---|---|
| `R` | transport / relay |
| `W` | witness / defensive reporting |
| `P` | propagation medium |

Roles are labels used by the functional coverage metric. They do not imply
biological tissue specialization.

## Tick order

Each deterministic tick performs:

1. local bounded advance;
2. curvature and torsion projection;
3. circular phase coupling;
4. graph-local binding diffusion;
5. neighbour prediction-error calculation;
6. shared-centroid normalization;
7. Q_f factor calculation;
8. tick receipt chaining.

The runtime is bounded by configuration limits on cell count, tick count,
geometry sample count, and total `cells × ticks` work.

## Q_f functional cohesion

Q_f is calculated from six normalized factors:

```text
Q_f = I × B × P × T × S × (1 − D)
```

where:

- `I` is circular phase coherence;
- `B` is binding-distribution cohesion;
- `P` is predictive stability;
- `T` is graph-edge continuity;
- `S` is role coverage;
- `D` is dissociation pressure from phase spread, bound fixes, and a declared
  sidecar residual.

Every factor is constrained to `[0, 1]`. Q_f is useful for deterministic
comparison inside this runtime only. It is not a consciousness score, life
metric, clinical measure, or empirical physical observable.

## Sidecars and fallback

The tissue configuration may record a declared `webgpu`, `cuda`, or `npu`
sidecar residual. The sidecar is accepted only when:

```text
residual <= residual_gate
```

A failed sidecar activates the recorded fallback path. The f64 geometry and
tissue report continue, so failed acceleration does not become a geometry
failure and never gains receipt authority.

`conformance/npu_tier2_v1.json` defines initial evidence gates for INT8, BF16,
and FP16 NPU fields. It is a profile, not a hardware driver implementation.

## Operational awareness

The culmination package used the term “awareness” for a loop of sensing,
prediction, integration, witnessing, intent, action, sealing, refinement, and
reporting. RSH adopts only the operational meaning:

```text
observe state → predict → validate → act within bounds → seal → report
```

No subjective state is inferred from that loop. Documentation and the
constitution explicitly refuse a subjective-awareness or qualia claim.

## Governed refinement

`src/rsh/refinement.py` implements a dry-run proposal evaluator. It:

1. canonicalizes a proposal into an intent token;
2. rejects unknown or out-of-bound changes;
3. detects escalation of geometry samples, residual gates, or Q_f floors;
4. requires explicit human acknowledgement for declared escalation;
5. runs baseline and candidate tissue reports;
6. compares the ordered objective vectors lexicographically;
7. emits a sealed `KEEP_CANDIDATE` or `REVERT` recommendation.

The evaluator never edits source, writes a committed configuration, waits for a
human asynchronously, or launches a recursive agent. “Keep” means the dry-run
candidate improved the declared objective ordering; it is not an autonomous
commit.

Example proposal:

```json
{
  "schema": "RSH-REFINEMENT-PROPOSAL-V1",
  "id": "increase-binding-diffusion",
  "changes": {
    "binding_diffusion": 0.2
  },
  "rationale": "Test whether graph cohesion improves.",
  "escalates_contract": false,
  "human_ack": false
}
```

## Commands

Python reference:

```bash
rsh constitution

rsh tissue \
  --cells 8 \
  --ticks 20 \
  --json rsh_tissue.json \
  --trace rsh_tissue.csv

rsh refine-dry-run proposal.json \
  --json refinement_decision.json
```

Native Rust conformance runtime:

```bash
cargo run --locked -p rsh-tissue-cli -- info
cargo run --locked -p rsh-tissue-cli -- \
  run --json rsh_tissue_rust.json --csv rsh_tissue_rust.csv
cargo run --locked -p rsh-tissue-cli -- \
  conformance --json rsh_tissue_rust_conformance.json
```

The browser runs the shared Rust runtime through WebAssembly at:

```text
https://qsolkcb.github.io/RSH/tissue.html
```

## Default conformance profile

`conformance/tissue_v1_8x20.json` fixes the default configuration and observable
reference values. Exact Python tissue receipts are scoped to CPython 3.12:

```text
reference runtime        CPython 3.12
cells                    8
ticks                    20
geometry samples         129
seed geometry receipt    f33042335100b7a2bca8c5c97724782ecb820cd8f6704f8e7eb074c1ed9e9a00
final Q_f                0.37926532158281384
reference tissue receipt 732fc6ccc5af543881528da7f9ec7717817af97c07e7f7973512685ab67e2622
```

CPython 3.10, 3.12, and 3.14 must each replay identically within the same runtime.
Across Python minor versions, the conformance suite compares constitution and
geometry seeds exactly, then checks Q_f factors, dissociation, and centering under
an absolute `1e-12` tolerance. Byte-identical tissue tick or report receipts are
not claimed across Python minor versions because floating-point library details
may change the canonical report bytes.

## Rust and WASM conformance

RSH v2.7.0 implements the planned second runtime:

- `rsh-tissue` contains the shared Rust simulation;
- `rsh-tissue-cli` executes the native runtime;
- `rsh-tissue-wasm` exposes the same implementation through a raw WASM ABI;
- `scripts/test_tissue_wasm.mjs` executes fresh Python, native Rust, and WASM
  reports and compares all portable tick and final-cell observables.

The sealed cross-runtime tolerance is `1e-12`. Receipt byte identity is not
assumed across Python, native Rust, or WASM because their geometry seed receipts,
math libraries, and serialization paths can differ. Same-runtime replay and
receipt-chain integrity remain mandatory.

See [Phase 9 Rust/WASM tissue conformance](PHASE9_TISSUE_CONFORMANCE.md).
