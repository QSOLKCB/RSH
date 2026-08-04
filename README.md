# RSH — Robitaille–Slade Helix

**Bounded Frenet–Serret geometry and deterministic evidence.**

RSH constructs a three-dimensional path by prescribing curvature and torsion
inside explicit Robitaille bounds, integrating the Frenet–Serret frame, and
translating the exact discrete midpoint to the coordinate origin.

**Authors:** J. Robitaille (DeltaKingZero) and Trent Slade / QSOL-IMC  
**Version:** 2.0.0  
**Current implementation:** Python 3.10+ standard library

## Current phase: Python reference implementation

The Python implementation is the readable scientific oracle for later native
and GPU versions. It defines the equations, validation rules, canonical report
schema, golden behaviour, and command-line evidence workflow before any Rust,
WASM, C++, or WGSL optimisation is introduced.

## Invariants

| Quantity | Contract |
|---|---|
| \(\psi\) | \(\sqrt{2+\sqrt{5}}\) |
| Curvature | \(0 \le \kappa(s) \le \sqrt{2}-1\) |
| Torsion | \(0 < \tau(s) < 1\) |
| Centre | exact discrete \(p=0.5\) sample translated to `(0, 0, 0)` |
| Frame | tangent, normal, and binormal remain orthonormal within tolerance |
| Evidence | canonical domain-separated SHA-256 receipt |

Bounds hold by construction and are verified again after integration.

## Quick start

Run directly from a checkout with no installation or third-party packages:

```bash
python3 rsh_runner.py info
python3 rsh_runner.py verify
python3 rsh_runner.py receipt
python3 rsh_runner.py parity --workers 4
python3 rsh_runner.py trace -o rsh_trace.csv
python3 rsh_runner.py visual -o rsh_visual.svg
```

A passing run reports the central parameter, centre error, curvature/torsion
ranges, frame drift, and canonical receipt. Commands return `0` on success,
`1` for a failed contract, and `2` for invalid input or an I/O error.

The package can also be installed locally:

```bash
python3 -m pip install -e .
rsh verify
```

## Exact bounded logical sampling

Large logical fields can be represented without allocating the full field:

```bash
python3 rsh_runner.py sample 16777216 12
```

The mapping uses exact integer arithmetic:

```text
logical_index(i) = floor(i * logical_count / rendered_count)
```

## Repository map

```text
rsh_runner.py                 Direct source-checkout runner
src/rsh/                      Geometry, verification, exports, and CLI package
tests/                        Geometry, evidence, export, and CLI tests
docs/MODEL.md                 Equations and numerical construction
docs/PROVENANCE.md            Attribution and implementation boundary
docs/SCIENTIFIC_BOUNDARY.md   Claims the evidence does and does not support
docs/ROADMAP.md               Python → Rust → WASM/WGSL implementation plan
```

## Scientific precision

The central sample reaches the origin because the integrated path is translated
there as an explicit coordinate convention. That check confirms implementation
correctness; it is not an empirical discovery.

Receipts prove byte-level identity of the canonical report. They do not, by
themselves, prove a physical interpretation. Concurrent parity means independent
runs agree; it is not a claim that the integrator is partitioned across threads.

See [the scientific boundary](docs/SCIENTIFIC_BOUNDARY.md) for the full statement.

## Test

```bash
python3 -m pip install -e .
python3 -m unittest discover -s tests -v
python3 rsh_runner.py verify -n 129 -o /tmp/rsh_verify.csv
python3 rsh_runner.py receipt -n 129
python3 rsh_runner.py parity -n 129 --workers 3
```

## Planned implementation sequence

1. **Python reference** — equations, evidence schema, tests, golden receipts.
2. **Rust core and CLI** — native deterministic implementation validated against Python.
3. **WASM bridge** — browser access to the Rust core without a server.
4. **WGSL compute and visual kernels** — GPU acceleration checked against shared vectors.
5. **Optional C++/CUDA adapter** — only where interoperability or NVIDIA-specific work requires it.

No later implementation becomes authoritative merely because it is faster. It
must reproduce the reference contracts and declared numerical tolerances.

## Licence and citation

MPL-2.0. See `NOTICE.md` for attribution and `CITATION.cff` for citation metadata.
