# Robitaille–Slade Helix Evidence Runner (RSH) v1.0
By DeltaKingZero (John Robitaille) and
Trent Slade / QSOL-IMC  

---

## Purpose
Bound-safe centre-transfer geometry — what was added, what changed, how to run it >>>
This package is a **parallel evidence runner** built so we can stand **our** geometric laws next to centre-transfer / verify-style contracts (same *discipline* as tools like NEXUS: verify CSV, receipts, parity, visual) **without** rewriting or rebranding upstream VORTEX-N / NEXUS source trees.

**Design law**

1. Prescribe curvature \(\kappa(s)\) and torsion \(\tau(s)\) **inside** Robitaille bounds.  
2. Integrate the Frenet–Serret frame to obtain the path.  
3. Translate the midpoint to the origin so **centre error = 0**.  

Bounds hold **by construction**, not by filtering a curve after the fact.

**Immutable invariants**

| Symbol | Value / rule |
|--------|----------------|
| \(\psi\) | \(\sqrt{2+\sqrt{5}} \approx 2.058171\) |
| \(\kappa(s)\) | \(\le \sqrt{2}-1 \approx 0.414214\) |
| \(\tau(s)\) | \(0 < \tau(s) < 1\) |
| Centre | Gate → **exact centre (origin)** → mouth |
| Receipts | Domain-separated SHA-256; replay-identical |

**Credit (this workstream)**

- Geometry & bound enforcement: **J. Robitaille / DeltaKingZero**  
- Collaboration on this stream: **T. Slade**  
- Independent of Verschoor/NEXUS git contents; comparable on **contracts**, not a fork rename.

---

## What was added

| Addition | Why it matters |
|----------|----------------|
| **Bound-safe \(\kappa,\tau\) schedules** | Raw embedding \(r(t)=e^{\psi t}(\cos t,\sin t,t)\) failed standard Frenet checks (κ and τ left the stated box). Schedules keep κ ≤ 0.85(√2−1) and τ ∈ (~0.22, ~0.48). |
| **Frenet–Serret integrator** (Heun + re-orthonormalization) | Path is the *output* of the laws, not an unchecked parametric guess. |
| **Centre translation** | Mid-sample forced to origin → `centre_error = 0` (verify-comparable). |
| **`verify` CSV** | Machine-readable contracts: centre, κ/τ violations, sampling gap, gate/centre/mouth, receipt. |
| **`trace` CSV** | Full sample table: \(p,s,x,y,z,\kappa,\tau\), radius. |
| **`visual` SVG** | Gate / central throat / mouth on a dark field — immediate geometric read. |
| **Receipt chain** | Domain `ROBITAILLE-SLADE-HELIX-EVIDENCE-V1`; second run must match. |
| **`parity`** | Sequential vs thread-pool parallel receipts must match. |
| **`benchmark`** | Wall timing for build+verify loops. |
| **CLI exit codes** | `0` = PASS, `1` = FAIL — CI-friendly. |

---

## What was changed (relative to the first Robitaille-only recompute)

| Before | After (v1.0) |
|--------|----------------|
| Direct Frenet on \(e^{\psi t}(\cos t,\sin t,t)\) | **Prescribed** κ,τ + integrated frame |
| `centre_error ≈ 1.0` | **`centre_error = 0`** |
| Hundreds of κ/τ “violations” | **0 / 0 violations** |
| Ad-hoc printout | Full **CLI** + CSV + SVG + receipts + parity |
| Single-shot script | **Reusable module** (`rsh_runner.py`) |

**Not changed on purpose**

- Upstream NEXUS / VORTEX-N files were **not** edited, stripped, or rebranded.  
- This is a **new** runner for side-by-side scientific comparison.

---

## Package contents

```text
robitaille_slade_helix/
├── README.md           ← this file
├── rsh_runner.py       ← evidence runner (Python 3 stdlib only)
├── rsh_verify.csv      ← last verify report (example PASS)
├── rsh_trace.csv       ← example path samples
└── rsh_visual.svg      ← example centre-transfer figure
```

**Dependencies:** Python 3.9+ standard library only (no pip packages required).

---

## Step-by-step: how to use it effectively

### 1. Unpack

```bash
unzip RSH-Robitaille-Slade-v1.0.zip
cd robitaille_slade_helix
```

### 2. Sanity — model constants

```bash
python3 rsh_runner.py info
```

You should see JSON with `psi`, `kappa_max`, version `1.0.0`, and the design law string.

### 3. Run the contract suite (primary command)

```bash
python3 rsh_runner.py verify -n 512 -o rsh_verify.csv
```

**Expect:** `RSH verify [PASS]` and exit code **0**.

Check in particular:

- `centre_error` → `0`  
- `kappa_violations` / `tau_violations` → `0`  
- `pass_all` → `True`  
- `receipt` → 64-char hex  

### 4. Confirm receipt stability

```bash
python3 rsh_runner.py receipt -n 512
```

**Expect:** one receipt line and `replay_identical=True`.

### 5. Confirm parallel parity

```bash
python3 rsh_runner.py parity --workers 4 -n 256
```

**Expect:** `parity_ok = True` (same receipt sequential vs parallel).

### 6. Export a path for analysis / plotting

```bash
python3 rsh_runner.py trace -n 512 -o rsh_trace.csv
```

Open in any spreadsheet or plotting tool (`p` vs `kappa`, `tau`, or `x,y` projection).

### 7. Emit the visual

```bash
python3 rsh_runner.py visual -n 512 -o rsh_visual.svg
```

Open `rsh_visual.svg` in a browser. Labels: **gate**, **centre** (throat), **mouth**.

### 8. Optional performance check

```bash
python3 rsh_runner.py benchmark -n 512
```

On a normal laptop this is typically a few milliseconds per build+verify.

### 9. Use in automation / CI

```bash
python3 rsh_runner.py verify -n 512 || exit 1
python3 rsh_runner.py receipt -n 512 || exit 1
python3 rsh_runner.py parity --workers 2 -n 256 || exit 1
```

Any FAIL returns exit code 1.

---

## How to read the verify metrics

| Metric | Meaning | Pass criterion |
|--------|---------|----------------|
| `centre_error` | Distance of midpoint sample from origin | \(= 0\) (≤ 1e−9) |
| `max_kappa` | Peak curvature on path | \(\le \sqrt{2}-1\) |
| `min_tau` / `max_tau` | Torsion band | both in \((0,1)\) |
| `kappa_violations` | Count outside κ law | `0` |
| `tau_violations` | Count outside τ law | `0` |
| `max_sampling_gap_error` | Uniform \(p\)-grid quality | \(\le 1\) (here ~0) |
| `mouth_separation` | Gate–mouth Euclidean distance | informational |
| `receipt` | Hash of report payload | stable on replay |

---

## Effective workflow for joint work

1. **Baseline** — run `verify` + `receipt` on a clean machine; store CSV + receipt string.  
2. **Change a schedule** only inside `kappa_schedule` / `tau_schedule` if experimenting; re-run verify.  
3. **Never** raise κ above \(\sqrt{2}-1\) or push τ to 0 or 1 — the runner will hard-fail schedule violations during integrate.  
4. **Compare** to any external centre-transfer tool on shared ideas only: centre residual, determinism, receipt replay — not on shared git history.  
5. **Publish evidence** as `rsh_verify.csv` + receipt + optional SVG, with this README.

---

## Scientific boundary (plain language)

- This runner proves **internal geometric contracts** (κ, τ, centre, sampling, determinism).  
- Receipts prove **byte-level identity** of the encoded report, not laboratory physics by themselves.  
- It is a **centre-transfer style path under Robitaille bounds**, not a claim that upstream VORTEX-N physics or branding has been replaced.

---

## License note

`rsh_runner.py` in this zip is original work for this collaboration stream.  
It does **not** redistribute NEXUS/VORTEX-N source. If you later combine with MPL-2.0 upstream code, keep those license headers intact on *those* files.

---

## Contact line

Questions on invariants, schedules, or wiring this into a larger stack: reply on the same channel you use with DeltaKingZero.

**Measure⁴ × Cut¹**  
— DeltaKingZero
