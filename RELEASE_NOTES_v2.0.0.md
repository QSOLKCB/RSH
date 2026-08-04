# RSH v2.0.0 — Python reference geometry core

## Major changes

- Rebuilt RSH as a standard-library Python reference implementation with a stable CLI.
- Defines prescribed curvature and torsion schedules under explicit bounds.
- Requires an odd sample count so the discrete path contains exact `p = 0.5`.
- Makes midpoint translation explicit as coordinate normalisation.
- Verifies frame norms, frame orthogonality, sampling, curvature, torsion, and centre placement.
- Adds canonical, domain-separated SHA-256 evidence receipts.
- Adds independent concurrent replay parity with an explicit scope statement.
- Adds exact integer bounded logical sampling without logical-field allocation.
- Adds CSV, JSON, and dependency-free SVG exports.
- Adds a direct `rsh_runner.py` entry point and an installable `rsh` command.
- Adds geometry, evidence, export, invalid-input, and command-line tests.
- Adds CI across Python 3.10, 3.12, and 3.14.
- Adds citation metadata, attribution, provenance, scientific-boundary, and staged roadmap documents.

## Deliberately deferred

The browser laboratory, Rust core, WASM bridge, WGSL kernels, and any optional
C++/CUDA adapter are later phases. They will be introduced only after the Python
reference schema and golden conformance vectors are stable.

## Compatibility

The original single-file v1 runner remains conceptually compatible at the level
of its constants and default schedules. v2 intentionally changes the default
sample count from 512 to 513 and renames endpoint fields. Receipt values are new
because the canonical schema and domain separator changed.
