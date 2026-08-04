# RSH v2.1.0 — native Rust core and restored Pages

RSH v2.1.0 adds the first native implementation of the bounded geometry model
and restores the public GitHub Pages surface.

## Native Rust implementation

- adds a Cargo workspace with `rsh-core` and `rsh-cli`;
- reproduces the prescribed curvature/torsion schedules and midpoint
  Frenet–Serret integration;
- preserves exact discrete midpoint coordinate normalisation;
- verifies centre, bounds, sampling, frame orthonormality, path metrics, and
  endpoint evidence;
- emits native JSON reports, CSV traces, logical sample mappings, and SHA-256
  receipts;
- provides `info`, `verify`, `trace`, `conformance`, and `sample` commands;
- locks Rust dependencies with `Cargo.lock`.

## Cross-runtime conformance

- adds `conformance/python_v2_129.json` as a checked-in reference record;
- tests Rust entry and exit coordinates against the Python golden path with a
  `1e-12` maximum-absolute-error tolerance;
- observed native errors are below `5e-16` for the declared 129-sample record;
- reports Python and Rust receipts side by side instead of claiming byte-level
  identity where runtime-sensitive transcendental values differ.

## GitHub Pages

- adds a Pages deployment workflow for `web/`;
- fixes the project-site 404 after merge and deployment;
- adds a responsive, dependency-free project surface;
- labels its animated geometry as schematic so it cannot be mistaken for
  verification evidence;
- prepares the site for the next WASM-backed laboratory phase.

## CI and quality

- adds Rust formatting enforcement;
- adds Clippy with warnings denied;
- runs locked workspace tests and native evidence smoke commands;
- validates the static Pages source;
- retains the Python 3.10, 3.12, and 3.14 reference matrix;
- retains the provenance-boundary terminology gate.

## Compatibility

The scientific model contract remains `2.0.0`. Version `2.1.0` identifies the
multi-runtime software release. The Python CLI and evidence schema remain
available and authoritative as the readable reference implementation.

## Next phase

Compile `rsh-core` to WebAssembly and connect the verified core to the offline
Pages interface. JavaScript will remain interface and export glue rather than a
second independent scientific implementation.
