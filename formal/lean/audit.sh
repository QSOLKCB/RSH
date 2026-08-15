#!/usr/bin/env bash
set -euo pipefail

REPORT="${1:-formal-verification-report.txt}"

if grep -R -nE '(^|[^[:alnum:]_])(sorry|admit)([^[:alnum:]_]|$)' RSH --include='*.lean'; then
  echo 'RSH formalization contains a forbidden proof hole.' >&2
  exit 1
fi

if grep -R -nE '^[[:space:]]*((private|protected|noncomputable|unsafe|partial|local)[[:space:]]+)*(axiom|constant)[[:space:]]' RSH --include='*.lean'; then
  echo 'RSH formalization contains a project-defined axiom or constant declaration.' >&2
  exit 1
fi

lake build

{
  echo 'RSH v3.0.0 Lean formal verification'
  echo 'contract: RSH-FORMAL-V1'
  echo "toolchain: $(cat lean-toolchain)"
  echo 'mathlib: 520045ab14e26149ee970e2e617ca04b09bde5d6 (v4.32.1)'
  echo
  lake env lean RSH/AxiomAudit.lean
} | tee "$REPORT"
