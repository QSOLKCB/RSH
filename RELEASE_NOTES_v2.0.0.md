# RSH v2.0.0 — independent bounded-geometry core

## Major changes

- Rebuilt the model as a standard-library Python evidence runner with a stable CLI.
- Replaced ambiguous visual terminology with **entry → centre → exit**.
- Requires an odd sample count so the discrete path contains exact `p = 0.5`.
- Makes midpoint translation explicit as coordinate normalisation.
- Expands verification to frame norms, frame orthogonality, sampling, curvature,
  torsion, and replay identity.
- Adds canonical, domain-separated SHA-256 receipts.
- Adds independent concurrent replay parity with an explicit scope statement.
- Adds exact integer bounded logical sampling without logical-field allocation.
- Adds CSV, JSON, and SVG exports.
- Adds a completely offline browser laboratory.
- Adds unit tests, command-line smoke tests, CI, and GitHub Pages deployment.
- Adds citation metadata, attribution, provenance, and scientific-boundary docs.

## Compatibility

The original single-file v1 runner remains conceptually compatible at the level
of its constants and default schedules. v2 intentionally changes the default
sample count from 512 to 513 and renames endpoint fields. Receipt values are new
because the canonical schema and domain separator changed.
