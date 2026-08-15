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
  echo 'RSH Lean formal verification'
  echo 'existing contract: RSH-FORMAL-V1'
  echo 'additive contract: RSH-GLUBALL-FORMAL-V1'
  echo 'RSH base: v4.0.0 @ 79b8481639fb4187c41035de4e707545db93f59a'
  echo 'GLUBALL source: v1.0.0 @ 80941183d14531093117e122da0fc32c13d2464b'
  echo "toolchain: $(cat lean-toolchain)"
  echo 'mathlib: 520045ab14e26149ee970e2e617ca04b09bde5d6 (v4.32.1)'
  echo
  lake env lean RSH/AxiomAudit.lean
} | tee "$REPORT"
