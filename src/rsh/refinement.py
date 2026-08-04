"""Deterministic dry-run governance for bounded tissue proposals.

This module never edits source code or mutates a committed runtime. It compares
one proposed parameter set with a baseline and emits a sealed recommendation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .constants import CANONICAL_FLOAT_PRECISION
from .tissue import TissueConfig, TissueReport, simulate_tissue

PROPOSAL_SCHEMA = "RSH-REFINEMENT-PROPOSAL-V1"
DECISION_SCHEMA = "RSH-REFINEMENT-DECISION-V1"
INTENT_DOMAIN = b"RSH-REFINEMENT-INTENT-V1\0"
DECISION_DOMAIN = b"RSH-REFINEMENT-DECISION-V1\0"

ALLOWED_CHANGES = frozenset(
    {
        "cells",
        "ticks",
        "geometry_samples",
        "ds",
        "phase_coupling",
        "binding_diffusion",
        "sidecar_backend",
        "sidecar_residual",
        "residual_gate",
        "qf_floor",
    }
)
ESCALATING_FIELDS = frozenset(
    {
        "geometry_samples",
        "residual_gate",
        "qf_floor",
    }
)


def _canonical(value: Any) -> Any:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite refinement evidence value")
        return format(value, f".{CANONICAL_FLOAT_PRECISION}e")
    if isinstance(value, dict):
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def _digest(domain: bytes, payload: Any) -> str:
    encoded = json.dumps(
        _canonical(payload),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(domain + encoded).hexdigest()


@dataclass(frozen=True)
class RefinementProposal:
    id: str
    changes: dict[str, Any]
    rationale: str = ""
    escalates_contract: bool = False
    human_ack: bool = False
    schema: str = PROPOSAL_SCHEMA

    def validate(self) -> "RefinementProposal":
        if self.schema != PROPOSAL_SCHEMA:
            raise ValueError("proposal schema mismatch")
        if not self.id.strip():
            raise ValueError("proposal id must be non-empty")
        if not isinstance(self.changes, dict) or not self.changes:
            raise ValueError(
                "proposal changes must be a non-empty object"
            )
        unknown = sorted(set(self.changes) - ALLOWED_CHANGES)
        if unknown:
            raise ValueError(
                f"unsupported proposal fields: {', '.join(unknown)}"
            )
        return self


@dataclass(frozen=True)
class ObjectiveVector:
    invariant_integrity: int
    oracle_fidelity: float
    tissue_cohesion_qf: float
    resource_efficiency: float
    role_coverage: float

    def as_tuple(self) -> tuple[float, ...]:
        return (
            float(self.invariant_integrity),
            self.oracle_fidelity,
            self.tissue_cohesion_qf,
            self.resource_efficiency,
            self.role_coverage,
        )


@dataclass(frozen=True)
class RefinementDecision:
    schema: str
    proposal_id: str
    intent_token: str
    disposition: str
    reason: str
    dry_run_only: bool
    human_ack_required: bool
    human_ack_present: bool
    baseline_config: TissueConfig
    candidate_config: TissueConfig | None
    baseline_receipt: str
    candidate_receipt: str | None
    baseline_objectives: ObjectiveVector
    candidate_objectives: ObjectiveVector | None
    receipt: str = ""


def proposal_from_dict(payload: dict[str, Any]) -> RefinementProposal:
    if not isinstance(payload, dict):
        raise ValueError("proposal must be a JSON object")

    proposal_id = payload.get("id")
    changes = payload.get("changes")
    rationale = payload.get("rationale", "")
    escalates_contract = payload.get("escalates_contract", False)
    human_ack = payload.get("human_ack", False)
    schema = payload.get("schema", PROPOSAL_SCHEMA)

    if not isinstance(proposal_id, str):
        raise ValueError("proposal id must be a string")
    if not isinstance(changes, dict):
        raise ValueError("proposal changes must be an object")
    if not isinstance(rationale, str):
        raise ValueError("proposal rationale must be a string")
    if not isinstance(escalates_contract, bool):
        raise ValueError("escalates_contract must be a boolean")
    if not isinstance(human_ack, bool):
        raise ValueError("human_ack must be a boolean")
    if not isinstance(schema, str):
        raise ValueError("proposal schema must be a string")

    return RefinementProposal(
        id=proposal_id,
        changes=dict(changes),
        rationale=rationale,
        escalates_contract=escalates_contract,
        human_ack=human_ack,
        schema=schema,
    ).validate()


def load_proposal(path: str | Path) -> RefinementProposal:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return proposal_from_dict(payload)


def intent_token(proposal: RefinementProposal) -> str:
    return _digest(INTENT_DOMAIN, asdict(proposal))


def _objective_vector(report: TissueReport) -> ObjectiveVector:
    config = report.config
    if config.sidecar_backend == "none" or report.fallback_used:
        fidelity = 1.0
    else:
        fidelity = max(
            0.0,
            1.0
            - min(
                1.0,
                config.sidecar_residual / config.residual_gate,
            ),
        )
    return ObjectiveVector(
        invariant_integrity=int(
            report.pass_constitution
            and report.pass_bounds
            and report.pass_centre
            and report.audit_chain_valid
        ),
        oracle_fidelity=fidelity,
        tissue_cohesion_qf=report.final_q_f,
        resource_efficiency=(
            1.0 / (1.0 + config.cells * config.ticks)
        ),
        role_coverage=report.ticks[-1].metrics.role_coverage,
    )


def _strict_lexicographic_improvement(
    baseline: ObjectiveVector,
    candidate: ObjectiveVector,
    tolerance: float = 1.0e-12,
) -> bool:
    for before, after in zip(
        baseline.as_tuple(),
        candidate.as_tuple(),
    ):
        if after > before + tolerance:
            return True
        if after < before - tolerance:
            return False
    return False


def _decision_receipt(decision: RefinementDecision) -> str:
    payload = asdict(decision)
    payload.pop("receipt", None)
    return _digest(DECISION_DOMAIN, payload)


def _sealed(decision: RefinementDecision) -> RefinementDecision:
    return replace(decision, receipt=_decision_receipt(decision))


def _early_revert(
    *,
    proposal: RefinementProposal,
    token: str,
    reason: str,
    human_ack_required: bool,
    baseline_config: TissueConfig,
    baseline_report: TissueReport,
    baseline_objectives: ObjectiveVector,
) -> RefinementDecision:
    return _sealed(
        RefinementDecision(
            schema=DECISION_SCHEMA,
            proposal_id=proposal.id,
            intent_token=token,
            disposition="REVERT",
            reason=reason,
            dry_run_only=True,
            human_ack_required=human_ack_required,
            human_ack_present=proposal.human_ack,
            baseline_config=baseline_config,
            candidate_config=None,
            baseline_receipt=baseline_report.receipt,
            candidate_receipt=None,
            baseline_objectives=baseline_objectives,
            candidate_objectives=None,
        )
    )


def evaluate_refinement(
    proposal: RefinementProposal,
    baseline_config: TissueConfig = TissueConfig(),
) -> RefinementDecision:
    proposal = proposal.validate()
    baseline_config = baseline_config.validate()
    token = intent_token(proposal)
    baseline_report = simulate_tissue(baseline_config)
    baseline_objectives = _objective_vector(baseline_report)

    changed_escalating_fields = sorted(
        set(proposal.changes) & ESCALATING_FIELDS
    )
    escalation_detected = bool(changed_escalating_fields)
    human_ack_required = (
        escalation_detected or proposal.escalates_contract
    )

    if escalation_detected and not proposal.escalates_contract:
        return _early_revert(
            proposal=proposal,
            token=token,
            reason="contract-escalation-not-declared",
            human_ack_required=True,
            baseline_config=baseline_config,
            baseline_report=baseline_report,
            baseline_objectives=baseline_objectives,
        )
    if human_ack_required and not proposal.human_ack:
        return _early_revert(
            proposal=proposal,
            token=token,
            reason="human-ack-required",
            human_ack_required=True,
            baseline_config=baseline_config,
            baseline_report=baseline_report,
            baseline_objectives=baseline_objectives,
        )

    try:
        candidate_config = replace(
            baseline_config,
            **proposal.changes,
        ).validate()
    except (TypeError, ValueError) as error:
        return _early_revert(
            proposal=proposal,
            token=token,
            reason=f"bound-projection-rejected: {error}",
            human_ack_required=human_ack_required,
            baseline_config=baseline_config,
            baseline_report=baseline_report,
            baseline_objectives=baseline_objectives,
        )

    candidate_report = simulate_tissue(candidate_config)
    candidate_objectives = _objective_vector(candidate_report)
    keep = (
        candidate_report.pass_all
        and _strict_lexicographic_improvement(
            baseline_objectives,
            candidate_objectives,
        )
    )

    return _sealed(
        RefinementDecision(
            schema=DECISION_SCHEMA,
            proposal_id=proposal.id,
            intent_token=token,
            disposition=(
                "KEEP_CANDIDATE" if keep else "REVERT"
            ),
            reason=(
                "ordered-objectives-improved"
                if keep
                else "objectives-not-improved"
            ),
            dry_run_only=True,
            human_ack_required=human_ack_required,
            human_ack_present=proposal.human_ack,
            baseline_config=baseline_config,
            candidate_config=candidate_config,
            baseline_receipt=baseline_report.receipt,
            candidate_receipt=candidate_report.receipt,
            baseline_objectives=baseline_objectives,
            candidate_objectives=candidate_objectives,
        )
    )


def decision_json(decision: RefinementDecision) -> str:
    return json.dumps(asdict(decision), indent=2, sort_keys=True) + "\n"


def write_decision_json(
    decision: RefinementDecision,
    path: str | Path,
) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(decision_json(decision), encoding="utf-8")
