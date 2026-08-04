# RSH v2.5.0 — Constitutional Geometric Tissue

RSH v2.5.0 converts the Geometric System culmination package into a bounded,
deterministic Python reference runtime. The release adds multi-cell tissue
simulation, a machine-checkable constitution, chained tick receipts, functional
Q_f metrics, a dry-run refinement policy, and an initial Tier 2 NPU evidence
profile.

The underlying Robitaille–Slade Helix geometry contract remains **2.0.0**.
The new tissue contract is **1.0.0**.

## Added

- `rsh.constitution` with canonical constitution hashing and invariant checks;
- `rsh.tissue` with deterministic geometry-seeded cells, graph edges, phase
  coupling, binding diffusion, neighbour prediction, centroid normalization, and
  bounded work limits;
- a functional six-factor Q_f cohesion metric;
- domain-separated receipt chaining for every tissue tick;
- a final tissue report receipt tied to the authoritative Python geometry seed;
- explicit sidecar acceptance and CPU/WASM fallback metadata;
- `rsh.refinement`, a sealed dry-run policy for bounded parameter proposals;
- explicit human acknowledgement for changes to geometry samples, residual gates,
  or Q_f acceptance floors;
- `rsh constitution`, `rsh tissue`, and `rsh refine-dry-run` commands;
- JSON report and CSV trace exports for tissue runs;
- `conformance/tissue_v1_8x20.json`, the sealed default tissue profile;
- `conformance/npu_tier2_v1.json`, defining initial INT8, BF16, and FP16 NPU
  residual evidence gates;
- operational-awareness and Phase 6 architecture documentation;
- unit and CLI tests for deterministic replay, audit-chain integrity, sidecar
  fallback, proposal governance, conformance vectors, and terminology boundaries.

## Default tissue result

```text
cells                    8
ticks                    20
geometry samples         129
constitution hash        090416435f8ae2adc7555dab356eafef7aadfeabdb99c68e7c381ddf3bf9e544
seed geometry receipt    f33042335100b7a2bca8c5c97724782ecb820cd8f6704f8e7eb074c1ed9e9a00
first Q_f                0.2623914043443579
final Q_f                0.37926532158281384
tissue report receipt    732fc6ccc5af543881528da7f9ec7717817af97c07e7f7973512685ab67e2622
```

The receipt proves identity of the declared tissue report. Q_f is a functional
simulation metric and not an empirical or consciousness claim.

## Governed refinement

A refinement proposal is converted into an intent token and tested against a
baseline. The evaluator checks:

1. allowed fields;
2. configuration bounds and work limits;
3. declared contract escalation;
4. required human acknowledgement;
5. complete baseline and candidate tissue reports;
6. ordered objective improvement;
7. candidate audit-chain and constitution validity.

The output is a sealed `KEEP_CANDIDATE` or `REVERT` **dry-run recommendation**.
The evaluator does not edit source code, commit configuration, or launch a
recursive autonomous process.

## Sidecar and NPU boundary

WebGPU, CUDA, and NPU values may contribute only as declared residual sidecars.
A residual outside its published gate activates fallback. No accelerator creates
or replaces the geometry receipt.

The NPU profile is a conformance document rather than a vendor driver binding.
Actual NPU execution requires future hardware-specific implementation and
readback evidence.

## Terminology boundary

The culmination material used “awareness” and a popular-media “singularity”
analogy. RSH narrows those terms deliberately:

- operational awareness means state observation, prediction, validation,
  receipt sealing, and reporting;
- bound-safe asymptotic refinement means repeated accepted proposals under a
  fixed constitution;
- neither phrase implies sentience, qualia, unbounded takeoff, or autonomous
  source modification.

## Deferred

- Rust and WASM tissue implementations;
- browser tissue visualization;
- vendor-specific NPU drivers and hardware execution evidence;
- long-duration operating-system deployment;
- any full accelerator implementation that bypasses the f64 geometry seed or
  tick receipt chain.
