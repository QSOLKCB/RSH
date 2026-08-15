"""RSH v4 epistemic and conformance governance contracts.

This module does not alter the geometry, tissue, or Lean theorem surfaces.
It classifies evidence explicitly and binds conformance receipts to declared
runtime identity. Text content is never parsed to infer proof status.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Mapping, Sequence

RSH_EPISTEMIC_V1 = "RSH-EPISTEMIC-V1"
RSH_CONFORMANCE_V1 = "RSH-CONFORMANCE-V1"
CONFORMANCE_RECEIPT_DOMAIN = b"RSH-CONFORMANCE-V1\0"
CONFORMANCE_LEDGER_DOMAIN = b"RSH-CONFORMANCE-LEDGER-V1\0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MAX_U64 = (1 << 64) - 1


class EpistemicState(str, Enum):
    KNOWN = "KNOWN"
    RETRIEVED = "RETRIEVED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"
    FICTION = "FICTION"


class EvidenceClass(str, Enum):
    MODEL_PROPOSAL = "MODEL_PROPOSAL"
    TOOL_RECEIPT = "TOOL_RECEIPT"
    MEASUREMENT = "MEASUREMENT"
    FORMAL_SYNTAX = "FORMAL_SYNTAX"
    PROOF_RECEIPT = "PROOF_RECEIPT"
    REJECTED = "REJECTED"


class ClaimTier(str, Enum):
    PROPOSAL = "PROPOSAL"
    HYPOTHESIS = "HYPOTHESIS"
    EVIDENCE_BACKED = "EVIDENCE_BACKED"
    VERIFIED = "VERIFIED"
    BLOCKED = "BLOCKED"


_TIER_RANK = {
    ClaimTier.PROPOSAL: 0,
    ClaimTier.HYPOTHESIS: 1,
    ClaimTier.EVIDENCE_BACKED: 2,
    ClaimTier.VERIFIED: 3,
    ClaimTier.BLOCKED: -1,
}


@dataclass(frozen=True)
class ClaimDecision:
    allowed: bool
    tier: ClaimTier
    epistemic_state: EpistemicState
    evidence_class: EvidenceClass
    reason: str


def _cap_tier(tier: ClaimTier, cap: ClaimTier) -> ClaimTier:
    if tier is ClaimTier.BLOCKED:
        return tier
    return tier if _TIER_RANK[tier] <= _TIER_RANK[cap] else cap


def adjudicate_claim(
    *,
    epistemic_state: EpistemicState,
    evidence_class: EvidenceClass,
    receipt_present: bool = False,
    proof_checked: bool = False,
    measurement_identified: bool = False,
) -> ClaimDecision:
    """Return the strongest claim tier supported by explicit metadata.

    The function deliberately does not inspect natural-language claim text.
    Formal-looking text is not proof, model text is not execution evidence,
    unknown is not false, and material conflict blocks promotion.
    """
    if evidence_class is EvidenceClass.REJECTED:
        tier = ClaimTier.BLOCKED
        reason = "evidence-rejected"
    elif evidence_class is EvidenceClass.PROOF_RECEIPT:
        if not receipt_present or not proof_checked:
            tier = ClaimTier.BLOCKED
            reason = "proof-receipt-incomplete"
        else:
            tier = ClaimTier.VERIFIED
            reason = "proof-receipt-verified"
    elif evidence_class is EvidenceClass.MEASUREMENT:
        if not receipt_present or not measurement_identified:
            tier = ClaimTier.BLOCKED
            reason = "measurement-evidence-incomplete"
        else:
            tier = ClaimTier.EVIDENCE_BACKED
            reason = "measurement-evidence-backed"
    elif evidence_class is EvidenceClass.TOOL_RECEIPT:
        if not receipt_present:
            tier = ClaimTier.BLOCKED
            reason = "tool-receipt-missing"
        else:
            tier = ClaimTier.EVIDENCE_BACKED
            reason = "tool-execution-evidence"
    elif evidence_class is EvidenceClass.FORMAL_SYNTAX:
        tier = ClaimTier.HYPOTHESIS
        reason = "formal-syntax-is-not-proof"
    else:
        tier = ClaimTier.PROPOSAL
        reason = "model-output-is-proposal"

    if epistemic_state is EpistemicState.CONFLICT:
        tier = ClaimTier.BLOCKED
        reason = "material-conflict-unresolved"
    elif epistemic_state is EpistemicState.FICTION:
        tier = _cap_tier(tier, ClaimTier.PROPOSAL)
        reason = "fiction-is-non-literal"
    elif epistemic_state is EpistemicState.UNKNOWN:
        tier = _cap_tier(tier, ClaimTier.HYPOTHESIS)
        reason = f"{reason};unknown-is-not-false"
    elif epistemic_state is EpistemicState.INFERRED:
        tier = _cap_tier(tier, ClaimTier.EVIDENCE_BACKED)
        reason = f"{reason};inference-not-known-without-support"

    return ClaimDecision(
        allowed=tier is not ClaimTier.BLOCKED,
        tier=tier,
        epistemic_state=epistemic_state,
        evidence_class=evidence_class,
        reason=reason,
    )


def _canonical_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    if any(ord(char) < 0x20 or ord(char) > 0x7E or char in '"\\' for char in value):
        raise ValueError(
            f"{label} must use printable ASCII excluding quote and backslash"
        )
    return value


@dataclass(frozen=True)
class RuntimeIdentity:
    backend: str
    implementation: str
    implementation_version: str
    source_revision: str
    fallback_used: bool = False
    fallback_from: str | None = None

    def validate(self) -> "RuntimeIdentity":
        for label, value in (
            ("backend", self.backend),
            ("implementation", self.implementation),
            ("implementation_version", self.implementation_version),
            ("source_revision", self.source_revision),
        ):
            _canonical_text(value, f"runtime.{label}")
        if not isinstance(self.fallback_used, bool):
            raise ValueError("runtime.fallback_used must be boolean")
        if self.fallback_used:
            if not isinstance(self.fallback_from, str) or not self.fallback_from:
                raise ValueError("fallback_used=true requires runtime.fallback_from")
            _canonical_text(self.fallback_from, "runtime.fallback_from")
            if self.fallback_from == self.backend:
                raise ValueError("fallback_from must name a different requested backend")
        elif self.fallback_from is not None:
            raise ValueError("fallback_from must be null when fallback_used=false")
        return self


@dataclass(frozen=True)
class ExperimentEnvelope:
    contract: str
    experiment: str
    input_sha256: str
    runtime: RuntimeIdentity
    parameters: Mapping[str, str]
    seed: int
    observables: Mapping[str, str]

    def validate(self) -> "ExperimentEnvelope":
        if self.contract != RSH_CONFORMANCE_V1:
            raise ValueError(f"contract must be {RSH_CONFORMANCE_V1}")
        _canonical_text(self.experiment, "experiment")
        if not isinstance(self.input_sha256, str) or not _SHA256_RE.fullmatch(self.input_sha256):
            raise ValueError("input_sha256 must be canonical lower-case SHA-256 hex")
        self.runtime.validate()
        if (
            isinstance(self.seed, bool)
            or not isinstance(self.seed, int)
            or self.seed < 0
            or self.seed > _MAX_U64
        ):
            raise ValueError("seed must be an unsigned 64-bit integer")
        _validate_string_map(self.parameters, "parameters")
        _validate_string_map(self.observables, "observables")
        return self


def _validate_string_map(value: Mapping[str, str], label: str) -> None:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    for key, item in value.items():
        _canonical_text(key, f"{label} key")
        _canonical_text(item, f"{label}.{key}")


def _sorted_string_map(value: Mapping[str, str]) -> dict[str, str]:
    return {key: value[key] for key in sorted(value)}


def canonical_experiment_json(envelope: ExperimentEnvelope) -> str:
    """Serialize an RSH-CONFORMANCE-V1 envelope in the normative field order."""
    envelope.validate()
    runtime = envelope.runtime
    payload = {
        "contract": envelope.contract,
        "experiment": envelope.experiment,
        "input_sha256": envelope.input_sha256,
        "runtime": {
            "backend": runtime.backend,
            "implementation": runtime.implementation,
            "implementation_version": runtime.implementation_version,
            "source_revision": runtime.source_revision,
            "fallback_used": runtime.fallback_used,
            "fallback_from": runtime.fallback_from,
        },
        "parameters": _sorted_string_map(envelope.parameters),
        "seed": envelope.seed,
        "observables": _sorted_string_map(envelope.observables),
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def experiment_receipt(envelope: ExperimentEnvelope) -> str:
    payload = canonical_experiment_json(envelope).encode("utf-8")
    return hashlib.sha256(CONFORMANCE_RECEIPT_DOMAIN + payload).hexdigest()


def require_backend(
    envelope: ExperimentEnvelope,
    expected_backend: str,
    *,
    allow_declared_fallback: bool = False,
) -> None:
    envelope.validate()
    if envelope.runtime.backend != expected_backend:
        raise ValueError(
            f"backend mismatch: expected {expected_backend!r}, "
            f"observed {envelope.runtime.backend!r}"
        )
    if envelope.runtime.fallback_used and not allow_declared_fallback:
        raise ValueError(
            f"declared fallback from {envelope.runtime.fallback_from!r} is not accepted"
        )


def compare_observables(a: ExperimentEnvelope, b: ExperimentEnvelope) -> bool:
    """Compare declared portable observables without pretending receipts must match."""
    a.validate()
    b.validate()
    return (
        a.contract == b.contract
        and a.experiment == b.experiment
        and a.input_sha256 == b.input_sha256
        and _sorted_string_map(a.parameters) == _sorted_string_map(b.parameters)
        and a.seed == b.seed
        and _sorted_string_map(a.observables) == _sorted_string_map(b.observables)
    )


def ledger_digest(receipts: Sequence[str]) -> str:
    if not receipts:
        raise ValueError("ledger must contain at least one receipt")
    canonical = []
    for receipt in receipts:
        if not isinstance(receipt, str) or not _SHA256_RE.fullmatch(receipt):
            raise ValueError("ledger receipts must be canonical lower-case SHA-256 hex")
        canonical.append(receipt)
    payload = json.dumps(
        {"contract": RSH_CONFORMANCE_V1, "receipts": canonical},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(CONFORMANCE_LEDGER_DOMAIN + payload).hexdigest()
