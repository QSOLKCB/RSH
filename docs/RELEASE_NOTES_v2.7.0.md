# RSH v2.7.0 — Rust/WASM tissue conformance

RSH v2.7.0 completes the planned cross-runtime implementation of the
constitutional geometric tissue contract.

## Highlights

- Added `rsh-tissue`, a native Rust port of the v2.5.0 Python tissue reference.
- Added `rsh-tissue-cli` for native report, CSV, and conformance output.
- Added `rsh-tissue-wasm`, a raw browser ABI over the shared Rust implementation.
- Extended `tissue_v1_8x20.json` with explicit Rust/WASM receipt and observable
  policies.
- Added an executable Node harness that compares fresh Python, native Rust, and
  compiled WASM reports.
- Added complete tick-metric and final-cell comparison under the sealed `1e-12`
  observable tolerance.
- Added same-runtime deterministic receipt replay and audit-chain regression
  tests.
- Added Rust reconstruction and verification of the canonical constitution hash.

## Default profile

```text
cells                    8
ticks                    20
geometry samples         129
first Q_f                0.2623914043443579
final Q_f                0.37926532158281384
observable tolerance     1e-12
```

The Python tissue receipt remains the canonical reference receipt for the
published CPython 3.12 profile. Native Rust and WASM generate their own runtime
evidence and are accepted by executable conformance rather than by pretending
all floating-point report bytes are universally identical.

## Authority boundary

This release does not change geometry model contract 2.0.0 or tissue contract
1.0.0. It does not promote Q_f into a biological or subjective-awareness metric,
and it does not give WASM, WebGPU, CUDA, or NPU outputs geometry-receipt
authority.
