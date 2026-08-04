"""Machine-checkable governance contract for the experimental tissue layer.

The constitution constrains implementation behaviour and evidence authority. It
is not a statement that the runtime is conscious, alive, or self-aware.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from .constants import (
    CANONICAL_FLOAT_PRECISION,
    KAPPA_MAX,
    MODEL_NAME,
    PSI,
    VERSION,
)

CONSTITUTION_SCHEMA = "RSH-CONSTITUTION-V1"
CONSTITUTION_VERSION = "1.0.0"
CONSTITUTION_DOMAIN = b"RSH-CONSTITUTION-V1\0"

DEFAULT_CONSTITUTION: dict[str, Any] = {
    "schema": CONSTITUTION_SCHEMA,
    "version": CONSTITUTION_VERSION,
    "geometry_model": MODEL_NAME,
    "geometry_model_contract": VERSION,
    "invariants": {
        "psi": PSI,
        "kappa_interval": [0.0, KAPPA_MAX],
        "tau_interval": {
            "lower": 0.0,
            "upper": 1.0,
            "open": True,
        },
        "geometry_centring": "discrete-midpoint-to-origin",
        "tissue_centring": "shared-centroid-to-origin",
        "oracle_authority": ["f64-cpu", "f64-wasm"],
        "accelerator_authority": "residual-sidecar-only",
        "geometry_receipt_domain": "RSH-GEOMETRY-EVIDENCE-V2",
    },
    "ordered_objectives": [
        "invariant_integrity",
        "oracle_fidelity",
        "tissue_cohesion_qf",
        "resource_cost",
        "role_coverage",
    ],
    "governance": {
        "non_escalating_refinement": "dry-run-and-seal",
        "contract_escalation": "explicit-human-ack-required",
        "human_veto": "authoritative",
    },
    "refusals": [
        "silent-bound-violation",
        "accelerator-as-oracle",
        "audit-chain-deletion",
        "subjective-awareness-or-qualia-claim",
    ],
    "terminology": {
        "operational_awareness": (
            "state observation, prediction, audit and reporting only"
        ),
        "bound_safe_asymptotic_refinement": (
            "iterated accepted proposals under a fixed constitution; "
            "not unbounded autonomous takeoff"
        ),
    },
}


def _canonical(value: Any) -> Any:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite constitution value")
        return format(value, f".{CANONICAL_FLOAT_PRECISION}e")
    if isinstance(value, dict):
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def canonical_constitution_bytes(
    payload: dict[str, Any] | None = None,
) -> bytes:
    payload = DEFAULT_CONSTITUTION if payload is None else payload
    return json.dumps(
        _canonical(payload),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def constitution_hash(payload: dict[str, Any] | None = None) -> str:
    return hashlib.sha256(
        CONSTITUTION_DOMAIN + canonical_constitution_bytes(payload)
    ).hexdigest()


def validate_constitution(
    payload: dict[str, Any] | None = None,
) -> tuple[str, ...]:
    payload = DEFAULT_CONSTITUTION if payload is None else payload
    errors: list[str] = []

    if payload.get("schema") != CONSTITUTION_SCHEMA:
        errors.append("schema mismatch")
    if payload.get("geometry_model") != MODEL_NAME:
        errors.append("geometry model mismatch")
    if payload.get("geometry_model_contract") != VERSION:
        errors.append("geometry contract mismatch")

    invariants = payload.get("invariants")
    if not isinstance(invariants, dict):
        return tuple([*errors, "invariants missing"])

    try:
        psi = float(invariants["psi"])
    except (KeyError, TypeError, ValueError):
        errors.append("psi missing or invalid")
    else:
        if not math.isclose(psi, PSI, rel_tol=0.0, abs_tol=1.0e-15):
            errors.append("psi mismatch")

    kappa_interval = invariants.get("kappa_interval")
    if not isinstance(kappa_interval, list) or len(kappa_interval) != 2:
        errors.append("kappa interval missing or invalid")
    else:
        try:
            kappa_lower = float(kappa_interval[0])
            kappa_upper = float(kappa_interval[1])
        except (TypeError, ValueError):
            errors.append("kappa interval missing or invalid")
        else:
            if not math.isclose(
                kappa_lower,
                0.0,
                rel_tol=0.0,
                abs_tol=0.0,
            ) or not math.isclose(
                kappa_upper,
                KAPPA_MAX,
                rel_tol=0.0,
                abs_tol=1.0e-15,
            ):
                errors.append("kappa interval mismatch")

    tau_interval = invariants.get("tau_interval")
    if not isinstance(tau_interval, dict):
        errors.append("tau interval missing or invalid")
    else:
        try:
            tau_lower = float(tau_interval["lower"])
            tau_upper = float(tau_interval["upper"])
        except (KeyError, TypeError, ValueError):
            errors.append("tau interval missing or invalid")
        else:
            if (
                tau_lower != 0.0
                or tau_upper != 1.0
                or tau_interval.get("open") is not True
            ):
                errors.append("tau interval mismatch")

    if invariants.get("accelerator_authority") != "residual-sidecar-only":
        errors.append("accelerator authority mismatch")

    oracle_authority = invariants.get("oracle_authority")
    if oracle_authority != ["f64-cpu", "f64-wasm"]:
        errors.append("oracle authority mismatch")

    refusals = payload.get("refusals")
    if not isinstance(refusals, list):
        errors.append("refusal list missing")
    else:
        required_refusals = {
            "silent-bound-violation",
            "accelerator-as-oracle",
            "audit-chain-deletion",
            "subjective-awareness-or-qualia-claim",
        }
        if not required_refusals.issubset(set(refusals)):
            errors.append("refusal list incomplete")

    return tuple(errors)


def constitution_report() -> dict[str, Any]:
    errors = validate_constitution()
    return {
        "schema": "RSH-CONSTITUTION-REPORT-V1",
        "constitution": DEFAULT_CONSTITUTION,
        "hash": constitution_hash(),
        "pass_all": not errors,
        "errors": list(errors),
    }
