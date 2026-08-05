# Phase 9 — Rust and WebAssembly tissue conformance

## Goal

Phase 9 completes the implementation boundary left open by the v2.5.0 Python
tissue reference. The deterministic tissue algorithm is now implemented once in
Rust and exposed through a raw WebAssembly adapter for browser execution.

The Python implementation remains the readable tissue authority. Rust and WASM
are accepted by reproducing the sealed default profile and the complete portable
observable report within the declared tolerance.

## Runtime structure

```text
Python tissue reference
        │
        ├── tissue_v1_8x20.json
        │
        ▼
Rust rsh-tissue library
        │
        ├── native rsh-tissue CLI
        └── rsh-tissue-wasm raw ABI
                    │
                    ▼
        executable cross-runtime harness
```

`rsh-tissue-wasm` calls `rsh-tissue`; it does not contain a second simulation.
The browser adapter therefore shares the same cell graph, tick ordering, Q_f
metric, audit-chain logic, and bound projection as the native Rust runtime.

## Ported contract

The Rust implementation reproduces:

1. verified RSH geometry seeding;
2. deterministic representative sample selection;
3. ring and chord tissue edges;
4. curvature and torsion projection;
5. circular phase coupling;
6. graph-local binding diffusion;
7. neighbour prediction error;
8. shared-centroid normalization;
9. Q_f functional cohesion;
10. chained tick and report receipts.

The machine-checkable constitution is reconstructed and hashed in Rust. The
computed value must match the Python reference hash:

```text
090416435f8ae2adc7555dab356eafef7aadfeabdb99c68e7c381ddf3bf9e544
```

## Receipt policy

Receipts prove deterministic report identity within a runtime and serialization
contract. Python, native Rust, and Rust/WASM may use different geometry seed or
report receipts even when their portable numerical observables agree. Native and
WASM execution can also differ at the final floating-point bits because their
math implementations are distinct compilation targets.

The conformance profile therefore requires:

- deterministic replay inside each runtime;
- native Rust-to-WASM portable-observable agreement within `1e-12`;
- Python-to-Rust/WASM portable-observable agreement within `1e-12`;
- no receipt-identity claim across Python, native Rust, or WASM.

The canonical Python tissue receipt remains recorded in the profile. A Rust or
WASM receipt does not replace it.

## Raw WASM ABI

```text
rsh_tissue_abi_version()
rsh_tissue_run(cells, ticks, geometry_samples, ds,
               phase_coupling, binding_diffusion,
               sidecar_backend, sidecar_residual,
               residual_gate, qf_floor)
rsh_tissue_output_ptr()
rsh_tissue_output_len()
```

Status codes:

- `0`: report passed;
- `1`: report executed but failed one or more contract checks;
- `2`: invalid input or runtime error.

The adapter applies stricter output-size limits than the general native tissue
contract so browser reports remain bounded.

## Executable conformance

`scripts/test_tissue_wasm.mjs`:

- executes the compiled WASM module;
- validates the ABI and memory span;
- compares every portable WASM observable with the native Rust report;
- compares every portable native and WASM observable against Python;
- verifies the sealed Python Q_f values and receipts;
- reports runtime receipts without requiring cross-runtime identity;
- checks authority and terminology boundaries.

CI generates fresh Python and native Rust reports before running the harness. No
checked-in generated report is trusted as a substitute for execution.

## Scientific boundary

Q_f remains a functional simulation metric. The Rust and WASM ports do not add a
biological interpretation, subjective-awareness claim, autonomous source
modification, or accelerator receipt authority.
