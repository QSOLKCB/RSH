#!/usr/bin/env bash
set -euo pipefail

REPORT="${1:-${TMPDIR:-/tmp}/rsh-formal-verification-report.txt}"
mkdir -p "$(dirname "$REPORT")"

mapfile -d '' LEAN_SOURCES < <(find RSH -type f -name '*.lean' -print0)
LEAN_SOURCES+=(RSH.lean)

if grep -nE '(^|[^[:alnum:]_])(sorry|admit)([^[:alnum:]_]|$)' "${LEAN_SOURCES[@]}"; then
  echo 'RSH formalization contains a forbidden proof hole.' >&2
  exit 1
fi

if grep -nE '^[[:space:]]*((private|protected|noncomputable|unsafe|partial|local)[[:space:]]+)*(axiom|constant)[[:space:]]' "${LEAN_SOURCES[@]}"; then
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
