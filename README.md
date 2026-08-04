# RSH — Robitaille–Slade Helix

**Bounded Frenet–Serret geometry, deterministic evidence, and an offline visual laboratory.**

RSH constructs a three-dimensional path by prescribing curvature and torsion
inside explicit Robitaille bounds, integrating the Frenet–Serret frame, and
translating the exact discrete midpoint to the coordinate origin.

**Authors:** J. Robitaille (DeltaKingZero) and Trent Slade / QSOL-IMC  
**Version:** 2.0.0  
**Runtime:** Python 3.9+ standard library; optional offline browser lab

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

```bash
python3 rsh_runner.py info
python3 rsh_runner.py verify
python3 rsh_runner.py receipt
python3 rsh_runner.py parity --workers 4
python3 rsh_runner.py trace -o rsh_trace.csv
python3 rsh_runner.py visual -o rsh_visual.svg
```

A passing run reports the central parameter, centre error, curvature/torsion
ranges, frame drift, and receipt. Commands return `0` on success and non-zero on
invalid input or a failed contract.

## Offline browser laboratory

Open `web/index.html` directly, or publish the `web/` directory with GitHub
Pages. The lab provides:

- draggable three-dimensional projection;
- curvature and torsion controls constrained to valid ranges;
- entry, centre, and exit landmarks;
- live verification metrics;
- animation along the generated path;
- CSV, JSON, and SVG exports;
- no server, Node.js, CDN, telemetry, or network access.

## Exact bounded logical sampling

Large logical fields can be represented without allocating the field:

```bash
python3 rsh_runner.py sample 16777216 12
```

The mapping uses exact integer arithmetic:

```text
logical_index(i) = floor(i * logical_count / rendered_count)
```

## Repository map

```text
rsh_runner.py            Standard-library geometry, evidence, CLI, and SVG output
tests/                   Unit and CLI tests
web/                     Offline interactive laboratory
docs/MODEL.md            Equations and numerical construction
docs/PROVENANCE.md       Attribution and independent implementation boundary
docs/SCIENTIFIC_BOUNDARY.md  Claims the evidence does and does not support
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
python3 -m unittest discover -s tests -v
python3 rsh_runner.py verify -n 129 -o /tmp/rsh_verify.csv
python3 rsh_runner.py receipt -n 129
python3 rsh_runner.py parity -n 129 --workers 3
```

## Licence and citation

MPL-2.0. See `NOTICE.md` for attribution and `CITATION.cff` for citation metadata.
