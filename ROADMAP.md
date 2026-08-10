# RSH active research roadmap

This file defines the active and queued RSH programme. The chronological
implementation record remains in [`docs/ROADMAP.md`](docs/ROADMAP.md); completed
phase documents remain under [`docs/`](docs/).

RSH is evolving from a geometry implementation into a cross-runtime scientific
evidence platform. That expansion does **not** collapse all subjects into one
model. Exact identity, numerical conformance, hardware observations, regulated
dynamics, physical simulation, experimental measurements, visualisation, and
sonification remain separately named evidence surfaces.

## Non-negotiable boundaries

1. The readable Python geometry implementation remains the canonical scientific
   oracle for the original Robitaille–Slade geometry contract.
2. Rust, WASM, WGSL, C++, CUDA, NPU, external solvers, and browser laboratories
   are accepted only through declared contracts and conformance gates.
3. Receipts prove evidence identity for a declared runtime and serialization
   path. They do not prove physical truth.
4. Exact Sierpiński cells and inversive witnesses are symbolic/exact sidecars.
   They are not complete physical meshes, compression proofs, material models,
   cavitation models, or geometry-receipt authority.
5. A simulated acoustic pressure field is not proof of cavitation. Cavitation
   claims require declared nuclei/bubble models and, where claimed, calibrated
   experimental evidence.
6. Display coordinates and sonification are non-authoritative presentations of
   validated evidence. They never feed back into scientific metrics.
7. Performance, parallelism, model complexity, or hardware execution never
   promotes an adapter into scientific authority.
8. The analytic Robitaille reference spine and any later dynamical regulator are
   separately named research/evidence surfaces. They do not silently revise the
   canonical prescribed-schedule geometry contract, and theorem labels are not
   promoted until their hypotheses and operators are sealed.

Preserve explicit false fields such as:

```text
geometry_receipt_authority: false
actual_multi_device_execution: false
distributed_execution: false
universal_speedup_claim: false
physical_storage_demonstrated: false
experimental_validation_complete: false
```

## Status key

| Status | Meaning |
|---|---|
| **Complete** | Implemented, documented, and exercised by the required validation matrix. |
| **Active** | Current development track with an explicit contract and evidence plan. |
| **Queued** | Accepted direction, not yet under implementation. |
| **Exploratory** | Research question without a sealed implementation contract. |
| **Continuous** | Ongoing maintenance or expansion work. |

# I. Completed platform foundations

## 1. Canonical geometry and cross-runtime execution

**Status: Complete**

RSH now includes:

- the dependency-light Python reference and installed CLI;
- canonical Rust geometry and native CLI;
- compiled raw WASM interfaces;
- WGSL schedule and full-path numerical sidecars;
- a versioned C ABI and C++17 consumer;
- optional CUDA schedule execution and trusted hardware evidence;
- separately named tissue, numerical, parallel, genomic, and exact-cell
  contracts;
- offline browser laboratories with downloadable evidence.

The historical details and release phases remain in
[`docs/ROADMAP.md`](docs/ROADMAP.md).

## 2. Rust/WASM tissue conformance

**Status: Complete in v2.7.0**

- Python, native Rust, and compiled WASM observables are compared under the
  sealed tissue tolerance;
- receipts remain runtime-scoped identities;
- the functional `Q_f` metric retains its no-consciousness/no-qualia boundary;
- refinement remains a bounded dry-run recommendation requiring human
  acknowledgement;
- the offline laboratory runs the accepted shared Rust/WASM implementation.

## 3. Parallel Frenet and deterministic shard-prefix reconstruction

**Status: Complete — single-device hardware validated**

`RSH-FRENET-PARALLEL-V1` and `RSH-FRENET-SHARD-PREFIX-V1` provide:

- midpoint Rodrigues SE(3) interval transforms;
- deterministic inclusive prefix composition;
- native Rust and compiled WASM references;
- normalized-quaternion WGSL execution with complete path readback;
- deterministic contiguous shard work units;
- local shard prefixes and reductions;
- exclusive shard-base composition;
- complete ordered reconstruction and midpoint centering;
- rejection of missing, overlapping, reordered, malformed, non-finite, or
  authority-promoting evidence;
- real RTX 5060 Ti WebGPU and `sm_120` CUDA observations under recorded gates.

The accepted shard contract proves local composition correctness. It does not by
itself prove multi-device or distributed execution.

## 4. Trusted RTX hardware workflow

**Status: Complete — protected dispatch passed**

The trusted workflow now provides:

- manual protected execution on labelled self-hosted RTX hardware;
- accepted-ancestor checks against `main`;
- pinned CUDA build environments;
- repeatability, CPU-reference, memcheck, racecheck, and full-readback gates;
- redacted deterministic artifacts;
- stable hardware identifiers excluded from public artifacts and logs;
- no privileged execution of untrusted public-pull-request code.

The physical multi-device CUDA campaign has also been accepted and recorded on
`main` through PR #25. It is no longer a queued prerequisite. Future trusted
acoustic, multi-GPU, or experimental workflows must preserve the same separation
between portable CI and privileged evidence generation.

## 5. DNA–ETQ–MIDI exploratory codec

**Status: Complete — PR #18**

`RSH-ETQ-DNA-MIDI-EXPLORATORY-V1` provides:

- strict bounded DNA input and complete-codon policy;
- exact ETQ-compatible event addressing;
- a global four-vertex tetrahedral address path;
- deterministic Python/JavaScript parity;
- exact MIDI metadata recovery and tamper rejection;
- canonical JSON, CSV, MIDI, and manifest evidence;
- an offline visual and sonification laboratory;
- explicit biological, physical-storage, distributed, and authority non-claims.

## 6. Genomic spectral evidence and exact binary32 cells

**Status: Complete — PR #19**

`RSH-ETQ-GENOMIC-SPECTRAL-V1` and
`RSH-F32-SIERPINSKI-CELL-V1` provide:

- bounded FASTA/VCF processing and deterministic genomic windows;
- exact preservation of every IEEE-754 binary32 raw word;
- the bijection `u32 ↔ 21 canonical trits ↔ exact triangular cell`;
- exact integer barycentric vertices and centroids;
- signed-zero, subnormal, infinity, quiet-NaN, and signalling-NaN fixtures;
- bounded iterable consumption and exact literal-boolean claim validation;
- Python/JavaScript canonical evidence parity;
- display coordinates declared as derived and non-identifying.

The three-child Sierpiński set is retained as an exact symbolic address space. It
is not a complete physical surface or volume index.

## 7. Exact f32 Sierpiński inversive witnesses

**Status: Complete — PR #20**

`RSH-F32-SIERPINSKI-INVERSIVE-WITNESS-V1` provides:

- exact rational inversion about the unit equilateral triangle circumcircle,
  with `c² = 1/3`;
- ETQ-fibre-selected reflection across one of three medians;
- exact conjugate barycentric coordinates;
- the invariant `r² × r'² = 1/9`;
- exact recovery after applying the same transformation twice;
- Python and JavaScript/BigInt conformance;
- tamper and singular-centre rejection;
- a self-contained offline witness laboratory;
- explicit rejection of Clawson-quadrilateral, physical-storage, compression,
  CUDA, distributed, and geometry-authority claims.

# II. Immediate execution programme

## 8. Analytic reference spine and dynamical-closure programme

This programme adds the recent Robitaille finite-dimensional work without
silently modifying the original RSH geometry oracle. The order is deliberately
conservative: first make the analytic seed and admission correction
machine-checkable; then harden the regulator specification; only then implement
Lyapunov/regulator claims and cross-runtime ports.

### 8.1 Restricted analytic reference spine and admission certificate

**Status: Active — implementation started in the current PR**

Introduce:

```text
RSH-REFERENCE-SPINE-V1
RSH-GAMMASEED-ADMISSION-V1
RSH-REFERENCE-SPINE-AUDIT-V1
```

The analytic reference spine is

\[
r_*(t)=e^{\psi t}(\cos t,\sin t,t),
\qquad \psi=\sqrt{2+\sqrt5}.
\]

Required evidence:

- closed-form binary64 evaluation of `r_*(t)`, curvature, and torsion;
- analytic monotonicity evidence for curvature and torsion on `t >= 0`;
- deterministic solution of the unique crossing
  `kappa(t_star) = sqrt(2)-1`;
- explicit full-seed `[0, 2*pi] -> REFUSE` because
  `kappa(0) ~= 0.475503823 > sqrt(2)-1`;
- explicit restricted-seed `[t_star, 2*pi] -> ADMIT`, with
  `t_star ~= 0.04797981890307`;
- frozen source-seed hash recorded as source metadata rather than falsely
  reproduced as an RSH receipt;
- new domain-separated point, admission, and audit receipts;
- `geometry_contract_modified: false` and
  `geometry_receipt_authority: false` in every admission surface;
- a dependency-free CLI/JSON audit and deterministic regression tests.

The canonical RSH prescribed-schedule path, geometry contract, and geometry
receipt remain unchanged.

### 8.2 Dynamical-closure specification hardening

**Status: Queued — P0, must precede regulator implementation**

Freeze a separately named contract such as
`RSH-ROBITAILLE-DYNAMICAL-CLOSURE-V1` only after resolving the current source
ambiguities:

1. distinguish the stated core operator
   `R_core = psi + n*tau/kappa` from any regularized/observed operator using
   `kappa + epsilon_0` and `-lambda*sigma(r)`;
2. resolve the printed `n` equation whose current `(kappa-kappa)` factor is
   identically zero unless one symbol is intended to be `kappa_*`;
3. freeze the positive/negative-part convention used by the torsion correction;
4. define `T(r)` and `sigma(r)` together with their regularity and locality
   assumptions;
5. distinguish strict constitutional admission `0 < tau < 1` from safety in the
   projected closure `[0,1]`;
6. supply a valid damping/contraction mechanism before claiming that the
   ordinary Frenet–Serret normal block is Hurwitz or that shape error contracts
   exponentially.

Until these points are resolved, theorem names from the dissertation are source
claims under audit, not machine-certified RSH theorems.

### 8.3 Python regulator and Lyapunov evidence

**Status: Queued — after 8.2 is sealed**

Candidate first implementation:

- readable dependency-light Python reference over state `(r, kappa, tau, n)`;
- explicit projected Euler policy with a separately named numerical contract;
- `V_0`, observation residual, `V_O`, shape error, projection state, and strict
  versus closure-safe admission recorded per step;
- empirical verification of any proposed discrete Lyapunov inequality on sealed
  fixtures;
- rejected evidence retained whenever monotonicity, admission, or step-size
  gates fail;
- no automatic promotion from observed decay to a theorem claim;
- no mutation of the canonical geometry receipt.

Only after the mathematical hypotheses are proved and encoded may fields such as
`tube_stability_theorem_verified` or `exponential_decay_theorem_verified` become
eligible for a true value.

### 8.4 Rust/WASM/browser regulator conformance

**Status: Queued — after the Python regulator contract is sealed**

Candidate surfaces:

```text
rsh-regulator
rsh-regulator-cli
rsh-regulator-wasm
web/regulator.html
```

Required rules:

- Rust reproduces the declared regulator observables rather than redefining the
  mathematics;
- WASM calls the shared Rust implementation rather than creating another
  JavaScript regulator;
- complete state and Lyapunov readback under declared residual gates;
- optional WebGPU/CUDA work remains an accelerator sidecar only;
- regulator receipts remain separate from geometry and tissue receipt domains;
- the tissue layer may later consume accepted regulator evidence only through an
  explicit one-way contract.

## 9. Fuzzing and malformed-evidence hardening

**Status: Active / Continuous**

- shard range, order, overlap, missing-prefix, missing-tail, and fingerprint
  mutation fuzzing;
- reference-spine interval, receipt, boundary, and source-seed mutation tests;
- future regulator state, projection, step-size, and Lyapunov-report fuzzing;
- exact-cell trit, rational, claim, count, and canonical-hash mutation fuzzing;
- MIDI metadata and genomic-window malformed-input fuzzing;
- tissue configuration and audit-chain fuzzing;
- C ABI ownership, length, layout, and malformed-input fuzzing;
- WASM pointer/length and structured-error boundary fuzzing;
- reduction of every discovered failure into a deterministic regression;
- no untrusted public-PR execution on privileged hardware.

# III. Cross-field evidence foundation

The cross-field programme begins only after preserving the existing contracts.
Its first deliverables are evidence and spatial semantics, not a large physics
solver.

## 10. Contract and schema registry

**Status: Queued — P0**

Introduce:

```text
RSH-CONTRACT-REGISTRY-V1
RSH-EVIDENCE-ENVELOPE-V1
RSH-UNIT-QUANTITY-V1
```

Required work:

- JSON Schema 2020-12 schemas with stable identifiers;
- an explicit semantic-version and supersession policy;
- interoperable canonical-JSON test vectors, preferably RFC 8785 where its
  numeric domain is appropriate;
- decimal-string or exact-integer policies outside safe binary64 handling;
- exact literal-boolean non-claim validation;
- SI quantity kind, unit, uncertainty, and calibration-source records;
- source commit, software, runtime, input, output, and agent/activity provenance;
- RO-Crate/W3C PROV-compatible research packaging;
- in-toto/SLSA-compatible build attestations and SPDX software inventories;
- negative fixtures for Unicode, key order, unsafe integers, non-finite values,
  duplicate fields, and malformed envelopes.

This foundation must remain dependency-light inside core RSH. Heavy provenance
or packaging tools should operate as adapters over a small stable schema.

## 11. Large scientific field evidence

**Status: Queued — P0**

JSON remains appropriate for control manifests and compact receipts, not for
large three- or four-dimensional fields.

Define:

- Zarr v3 as the preferred chunked multidimensional field format;
- HDF5 as accepted portable interchange;
- a compact canonical manifest recording array type, shape, chunks, endianness,
  units, coordinate frame, missing-value policy, and hashes;
- deterministic chunk reconstruction and missing/tampered-chunk tests;
- a declared boundary between array identity and visual downsampling.

## 12. Exact spatial consolidation

**Status: Queued — P0**

Create a shared Rust/WASM exact-spatial layer rather than indefinitely
maintaining separate Python and JavaScript exact-geometry implementations.

Candidate crate and contracts:

```text
rsh-exact-spatial
RSH-REACTOR-SPATIAL-CELL-V1
RSH-SIERPINSKI-PATCH-MAP-V1
```

The spatial registry must distinguish:

| Geometry | Identity | Coverage policy |
|---|---|---|
| Existing symbolic f32 cell | depth-21 three-child Sierpiński address | retained cells only; central gaps are explicit |
| Physical triangular boundary | patch UUID plus four-child refinement path | complete patch coverage |
| Cartesian/voxel volume | octree cell ID, Morton order with optional Hilbert sidecar | complete bounded volume |
| Tetrahedral FEM volume | mesh UUID, element UUID, refinement path | complete declared mesh |
| Spherical shell | hierarchical triangular mesh | complete declared shell |

An exact Sierpiński centroid may map onto a physical triangular patch through a
declared affine barycentric map. The reverse map must return a rejected or
`none` result for a point in a removed central triangle; it must never fabricate
an address.

ETQ fibre labels remain occupied by their existing contract semantics and must
not be silently reused as transducer-channel identities.

# IV. Versioned ultrasonic and cavitation research

This programme is optional cross-field work. It extends the RSH evidence
architecture without changing the original geometry contracts.

## 13. Reactor, medium, and source-array contracts

**Status: Queued — P0**

Introduce:

```text
RSH-REACTOR-GEOMETRY-V1
RSH-ULTRASONIC-MEDIUM-V1
RSH-ULTRASONIC-SOURCE-ARRAY-V1
```

Required semantics:

- vessel geometry, coordinate frame, boundaries, mesh, and material regions;
- temperature, static pressure, density, sound speed, viscosity, surface
  tension, vapour pressure, attenuation, dissolved-gas metadata, and uncertainty;
- independent `transducer_lane` identifiers;
- transducer position, orientation, aperture, waveform, phase, amplitude,
  frequency, duty cycle, and calibration reference;
- exact hashes linking geometry, medium, source schedule, and solver request.

Idealized source boundaries and measured transducer responses must be named
separately.

## 14. Single-bubble dynamics kernel

**Status: Queued — P0**

Introduce `RSH-CAVITATION-BUBBLE-V1` with the escalation ladder:

```text
Rayleigh collapse
→ Rayleigh–Plesset
→ Keller–Miksis
→ optional Gilmore / Gilmore–NASG
```

Every escalation retains the simpler model as a regression surface.

Implementation plan:

- readable Python/SciPy reference;
- dependency-light Rust implementation where practical;
- bounded WASM execution for browser fixtures;
- exact equation/model identifier and assumptions;
- declared medium and drive references;
- solver method, tolerances, maximum step, event policy, and failure state;
- radius, wall velocity, wall acceleration, extrema, and collapse-event output;
- static equilibrium, Rayleigh collapse, weak sinusoidal oscillation, and
  tolerance-convergence fixtures;
- rejection of nonphysical states and non-convergent executions.

Mandatory distinctions include:

```text
spherical_symmetry_assumed: true
bubble_interactions_modelled: false
collapse_temperature_is_measured: false
chemical_yield_predicted: false
```

## 15. Acoustic field solver adapters

**Status: Queued — P0**

Introduce `RSH-ULTRASONIC-FIELD-V1` as an adapter contract rather than building a
large monolithic in-house solver.

Preferred first comparisons:

- k-Wave/k-Wave-python for heterogeneous, absorbing, nonlinear time-domain
  ultrasound;
- DOLFINx/PETSc or openCFS for frequency-domain Helmholtz verification;
- a minimal bounded in-house plane-wave or cavity fixture only for analytical
  regression, not as the main production solver;
- j-Wave only after its forward solutions pass independent comparison;
- MFEM as a later high-order GPU path.

Every field report must record:

```text
equation and model identifier
solver backend and exact version
container or environment digest
input geometry, medium, and source hashes
precision
mesh/grid and coordinate frame
time step or frequency discretisation
PML/boundary configuration
absolute and relative tolerances
iteration or convergence history
complete field-manifest hash
hardware execution state
mandatory non-claims
```

Required analytical fixtures:

- plane wave;
- spherical spreading;
- rigid cavity mode;
- standing wave;
- equal-phase and opposite-phase source pairs;
- homogeneous attenuation slab.

Time-domain and frequency-domain outputs should be compared after projection to a
declared common sampling grid. Byte identity is not expected across independent
solvers.

## 16. One-way field-to-bubble execution

**Status: Queued — P1**

Introduce an explicit sampling contract connecting a validated acoustic field to
one or more bubble trajectories.

Required evidence:

- field report hash;
- physical spatial-cell or mesh-element identity;
- declared interpolation/sampling policy;
- nuclei or initial-radius distribution;
- one-way-coupling statement;
- complete trajectory arrays and hashes;
- uncertainty ensemble where input parameters are uncertain.

A one-way drive does not claim bubble feedback on the acoustic field.

## 17. Coupled cavitation field

**Status: Queued — P1**

Introduce:

```text
RSH-CAVITATION-POPULATION-V1
RSH-CAVITATION-COUPLED-FIELD-V1
```

Scope:

- nuclei-size and population distributions;
- gas content and uncertainty;
- nonlinear bubble dissipation and attenuation;
- iterative field/population coupling;
- explicit residual history and convergence gates;
- zero-bubble and weak-amplitude linear limits;
- intentionally non-convergent fixtures retained as rejected evidence;
- independent comparison with published or separately implemented reactor cases.

No pressure threshold alone may set `physical_cavitation_demonstrated: true`.

# V. Validation, presentation, and later multiphysics

## 18. Experimental evidence programme

**Status: Exploratory until contracts and equipment are declared**

Introduce `RSH-ULTRASONIC-EXPERIMENT-V1` before claiming model-to-world agreement.

Suggested sequence:

| Experiment | Main evidence | Purpose |
|---|---|---|
| Hydrophone raster map | raw waveform and calibrated pressure spectrum | field shape and amplitude |
| Standing-wave cavity | nodes, antinodes, modal frequencies | boundaries and phase |
| Calorimetry | temperature-time trace and absorbed power | aggregate energy deposition |
| Passive cavitation detection | harmonic, subharmonic, broadband spectra | cavitation-regime comparison |
| Chemical dosimetry | protocol-specific product concentration | chemical-effect validation |
| High-speed imaging | selected bubble radius/position trajectories | bubble-model validation |
| Multi-transducer sweep | phase/frequency/amplitude grid | control-prediction validation |
| Erosion/material test | mass loss or surface measurement | material-response validation |

Every experiment requires instrument identity, calibration, protocol, raw-data
retention, environmental conditions, uncertainty, and processing provenance.

## 19. Browser field and cavitation laboratory

**Status: Queued after stable field and bubble contracts**

Introduce `RSH-ULTRASONIC-LAB-V1` with:

- vtk.js or another bounded field/mesh viewer;
- pressure, intensity, bubble-trajectory, convergence, and uncertainty views;
- complete evidence and manifest downloads;
- worker-based parsing for large bounded files;
- generation tokens so stale asynchronous analyses cannot overwrite newer data;
- subdirectory-scoped offline caches that coexist with other laboratories;
- explicit display transformations and downsampling records.

Sonification may map validated evidence to audio:

| Evidence variable | Bounded mapping |
|---|---|
| Pressure RMS | loudness |
| Bubble radius or resonance | pitch |
| Wall velocity | spectral brightness |
| Harmonic/ultraharmonic content | pitched overtones |
| Subharmonic component | low partial or modulation |
| Broadband emission | bounded noise component |
| Spatial coordinate | stereo or ambisonic position |
| Solver uncertainty | controlled modulation depth |
| Rejected run | distinct status cue, never musical success |

Audio remains a deterministic presentation derived from accepted evidence. It is
not evidence itself.

## 20. Source-array optimisation

**Status: Queued after independently validated forward fields**

Introduce `RSH-ULTRASONIC-CONTROL-V1` with:

- bounded objectives and physical constraints;
- j-Wave gradients only after forward agreement;
- derivative-free fallback around an accepted forward solver;
- uncertainty ensembles and robustness metrics;
- recommendation-only output requiring human acceptance;
- no universal optimality claim.

## 21. Streaming, thermal, chemical, and piezoelectric coupling

**Status: Exploratory / long-term**

Use specialist solvers through process or adapter boundaries rather than placing
all multiphysics inside the RSH exact core.

Candidate tools:

- preCICE for partitioned coupling;
- OpenFOAM for streaming, flow, heat, and species transport;
- openCFS or Elmer for piezoelectric, structural, thermal, and acoustic coupling;
- Cantera for declared reaction networks and thermochemistry;
- MFEM or DOLFINx for additional high-order or weak-form research.

Each coupled run requires separate model identifiers, unit contracts, residual
histories, rejected states, and independent validation.

## 22. Bubble-cloud and HPC research

**Status: Exploratory / long-term**

Possible later tracks:

- volume-averaged bubbly-liquid equations;
- Eulerian–Lagrangian bubble populations;
- interacting-bubble streaming;
- cloud-scale nonlinear attenuation;
- high-order GPU field methods;
- distributed domain decomposition;
- trusted multi-GPU/HPC execution with complete partition and reconstruction
  evidence.

These tracks follow single-bubble, field, coupling, and experimental validation;
they do not replace those simpler regression surfaces.

# VI. Field-agnostic extensions

The evidence architecture should support other fields without erasing their
physical distinctions.

Candidate separately named tracks:

```text
RSH-FIELD-DOMAIN-V1
RSH-FIELD-SOURCE-V1
RSH-FIELD-SOLUTION-V1
RSH-FIELD-COUPLING-V1
RSH-FIELD-EXPERIMENT-V1
```

Potential applications:

- electromagnetics and RF;
- piezoelectric and vibroacoustic systems;
- acoustofluidic streaming;
- thermal processing;
- reaction and species transport;
- differentiable digital twins;
- lattice-Boltzmann cavitation comparisons;
- graph signal processing for sensor/actuator networks;
- biomedical ultrasound under separate safety and regulatory boundaries;
- erosion and materials testing;
- scientific sonification.

Acoustic pressure, electromagnetic field strength, concentration, temperature,
and graph state must never share an untyped generic scalar.

# VII. Evidence packaging and CI policy

## 23. Evidence bundle layout

A large-field research bundle should follow a structure such as:

```text
run/
  manifest.json
  schemas/
  provenance/
    ro-crate-metadata.json
    prov.jsonld
  attestations/
  geometry/
  source/
  mesh/
  field.zarr/
  bubbles.zarr/
  validation/
  visualisation/
  SPDX.json
  SHA256SUMS
```

The canonical manifest identifies every non-JSON artifact by cryptographic hash,
format, version, units, coordinate frame, and role.

## 24. Recommended CI jobs

```text
reference-spine-admission
regulator-python
schema-and-canonicalisation
exact-spatial
fuzz-and-property-tests
bubble-python
bubble-rust
bubble-wasm
acoustic-small-fixtures
cross-solver-linear
field-data-format
browser-ultrasonic-lab
provenance-and-attestations
licence-and-sbom
trusted-multi-device-cuda
trusted-acoustic-gpu
experimental-evidence-validation
```

`regulator-python` remains a future job until the dynamical-closure contract is
sealed. Ordinary pull requests run bounded deterministic fixtures only. Large
3-D, GPU, multi-GPU, distributed, or physical experiments run on trusted
manual/scheduled infrastructure and must verify that the tested commit is an
accepted ancestor of `main`.

# VIII. Validation gates

Every numerical or physical contract must record:

```text
equation/model identifier
input and output units
solver and exact version
precision
mesh/grid/spatial identity
time step or frequency discretisation
absolute and relative tolerances
iteration and convergence history
analytical or independent comparison
complete output hash
source commit
hardware execution state
mandatory non-claims
```

For analytic/regulator research, the analogous gate must also record the frozen
operator definition, domain, invariant set, projection policy, Lyapunov quantity
being tested, and whether a result is a proved theorem, a numerical observation,
or a rejected claim.

Validation tiers:

1. **Analytical/semi-analytical fixtures** — exact or declared residual gates.
2. **Independent solver comparison** — agreement on a declared common sampling
   surface, not byte identity.
3. **Calibrated experiment** — raw measurements, calibration, uncertainty, and
   processing provenance.

A run that executes but fails convergence, reconstruction, residual, hash,
calibration, uncertainty, admission, or Lyapunov gates remains preserved as
rejected evidence.

# IX. Principal risks and mitigations

| Risk | Severity | Required mitigation |
|---|---:|---|
| Analytic reference spine confused with canonical RSH geometry | High | Separate contract and receipt domains; `geometry_contract_modified: false` |
| Unverified regulator theorem promoted from numerical behaviour | Critical | Seal operators/hypotheses first; distinguish theorem, observation, and rejected evidence |
| Pressure threshold presented as proof of cavitation | Critical | Require nuclei/bubble model and calibrated evidence |
| Unknown nuclei distribution | Critical | Ensembles, gas metadata, uncertainty reporting |
| Model-to-experiment mismatch | Critical | Calibration, raw-data retention, uncertainty budgets |
| Sierpiński cells used as a complete reactor index | High | Separate complete surface/volume spatial contract |
| ETQ fibre reused as transducer identity | High | Independent `transducer_lane` field |
| No mesh/time-step convergence | High | Mandatory convergence report and rejected state |
| Single-solver dependence | High | Analytical fixtures plus independent comparison |
| Canonical JSON drift | High | Shared vectors, exact strings, schema registry |
| Large fields placed in JSON | High | Zarr/HDF5 plus compact canonical manifest |
| Browser display mistaken for identity | Medium | Display-only declarations and transform records |
| GPU architecture variation | Medium-high | Residual conformance, metadata, full readback |
| Copyleft dependency contamination | Medium-high | Process adapters and pinned licence review |
| Cross-field scope explosion | High | P0/P1 gates and separately mergeable contracts |

# X. Recommended order

The current priority sequence is:

1. complete and seal the restricted analytic reference-spine/admission slice,
   including the full-domain refusal and restricted-domain certificate;
2. harden and freeze the dynamical-closure specification before implementing
   regulator theorem claims;
3. implement the dependency-light Python regulator plus explicit Lyapunov,
   projection, strict-admission, and rejected-evidence traces;
4. add Rust/WASM/browser regulator conformance only after the Python contract and
   fixtures are sealed;
5. continue fuzzing and malformed-evidence hardening across the new and existing
   evidence surfaces;
6. introduce the contract registry, canonicalisation vectors, unit quantities,
   provenance envelope, and field-data manifest;
7. consolidate exact spatial identity in shared Rust/WASM and define complete
   physical surface/volume indexing;
8. implement reactor, medium, and source-array contracts;
9. implement the single-bubble model ladder with analytical fixtures;
10. integrate time-domain and frequency-domain acoustic solver adapters;
11. implement one-way field-to-bubble execution;
12. implement nonlinear coupled cavitation with explicit convergence evidence;
13. add the browser field/cavitation laboratory and deterministic sonification;
14. begin calibrated experimental validation;
15. proceed to source optimisation, piezoelectric, streaming, thermal, chemical,
    and bubble-cloud/HPC work only after the earlier gates pass.

## Planning ranges

These are engineering estimates, not delivery promises:

| Programme slice | Approximate effort |
|---|---:|
| Reference-spine admission and evidence | 1–2 person-weeks |
| Dynamical-closure hardening + Python regulator | 4–8 person-weeks |
| Regulator Rust/WASM/browser conformance | 4–7 person-weeks |
| Evidence foundation | 5–8 person-weeks |
| Exact spatial consolidation | 5–9 person-weeks |
| Bubble kernel | 6–10 person-weeks |
| Reactor/source contracts | 4–7 person-weeks |
| Linear acoustic adapters | 8–13 person-weeks |
| One-way field-to-bubble execution | 4–7 person-weeks |
| Nonlinear coupled cavitation | 10–17 person-weeks |
| Browser physics laboratory | 7–11 person-weeks |
| Experimental validation | 9–16 person-weeks |
| Broad multiphysics programme | 80–130 person-weeks total, excluding equipment and facility lead times |

The roadmap should be revised whenever evidence invalidates an assumption. A new
backend, equation, field, experiment, regulator, or ontology requires a new name
and contract rather than silent modification of an accepted one.
