"""Analytic Robitaille reference spine and restricted-domain admission evidence.

This module is a separately named research/evidence surface.  It does not
replace the canonical RSH geometry oracle, its prescribed curvature/torsion
schedules, or the RSH geometry receipt domain.

For the analytic spine

    r_*(t) = exp(psi t) (cos t, sin t, t),

closed-form curvature and torsion are evaluated directly.  On t >= 0 both are
strictly decreasing: the derivative of kappa^2 and the derivative of tau have a
negative prefactor and positive polynomial numerators.  Consequently the
curvature ceiling has at most one crossing on the frozen seed interval
[0, 2*pi], and interval admission can be decided from its endpoints once the
crossing is located.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .constants import CANONICAL_FLOAT_PRECISION, KAPPA_MAX, PSI


REFERENCE_SPINE_SCHEMA = "RSH-REFERENCE-SPINE-V1"
REFERENCE_SPINE_CONTRACT_VERSION = "1.0.0"
ADMISSION_SCHEMA = "RSH-GAMMASEED-ADMISSION-V1"
AUDIT_SCHEMA = "RSH-REFERENCE-SPINE-AUDIT-V1"
REFERENCE_SPINE_RECEIPT_DOMAIN = b"RSH-REFERENCE-SPINE-EVIDENCE-V1\0"
ADMISSION_RECEIPT_DOMAIN = b"RSH-GAMMASEED-ADMISSION-V1\0"
AUDIT_RECEIPT_DOMAIN = b"RSH-REFERENCE-SPINE-AUDIT-V1\0"

# Frozen seed identifier supplied by the GammaSeed-restricted-v1 source record.
GAMMASEED_RESTRICTED_V1_HASH = (
    "baec1aa01299bb465be50e9685988f1d27c41fb97c40a4e2058660dc63ce2681"
)
SEED_T0 = 0.0
SEED_T1 = 2.0 * math.pi
BOUND_TOLERANCE = 1.0e-12


@dataclass(frozen=True)
class ReferenceSpinePoint:
    schema: str
    contract_version: str
    t: float
    x: float
    y: float
    z: float
    kappa: float
    tau: float
    receipt: str = ""


@dataclass(frozen=True)
class AdmissionCertificate:
    schema: str
    contract_version: str
    source_seed_hash: str
    requested_t0: float
    requested_t1: float
    t_star: float
    psi: float
    kappa_bound: float
    tau_lower_exclusive: float
    tau_upper_exclusive: float
    max_kappa: float
    min_kappa: float
    max_tau: float
    min_tau: float
    pass_kappa: bool
    pass_tau: bool
    admitted: bool
    disposition: str
    monotonicity_basis: str
    geometry_contract_modified: bool
    geometry_receipt_authority: bool
    receipt: str = ""


@dataclass(frozen=True)
class ReferenceSpineAudit:
    schema: str
    contract_version: str
    source_seed_hash: str
    reference_spine_schema: str
    psi: float
    kappa_bound: float
    seed_t0: float
    seed_t1: float
    t_star: float
    kappa_at_zero: float
    tau_at_zero: float
    full_domain: AdmissionCertificate
    restricted_domain: AdmissionCertificate
    pass_full_domain_refusal: bool
    pass_restricted_domain_admission: bool
    pass_unique_curvature_crossing: bool
    geometry_contract_modified: bool
    geometry_receipt_authority: bool
    pass_all: bool
    receipt: str = ""


def _validate_t(t: float) -> float:
    t = float(t)
    if not math.isfinite(t):
        raise ValueError("reference-spine parameter must be finite")
    return t


def reference_position(t: float) -> tuple[float, float, float]:
    """Return r_*(t) for the analytic Robitaille reference spine."""
    t = _validate_t(t)
    scale = math.exp(PSI * t)
    return (scale * math.cos(t), scale * math.sin(t), scale * t)


def reference_curvature(t: float) -> float:
    """Return the exact closed-form curvature evaluated in binary64.

    With a = psi,

      kappa(t)^2 =
        (a^2+1)(a^2 t^2 + 2a^2 + 2at + 2)e^(-2at)
        -------------------------------------------------
        (a^2 t^2 + a^2 + 2at + 2)^3.

    For a > 0 and t >= 0, d(kappa^2)/dt is strictly negative because it is
    -2a times a positive denominator/exponential and a polynomial whose
    coefficients are all positive.
    """
    t = _validate_t(t)
    a = PSI
    a2 = a * a
    numerator = (a2 + 1.0) * (
        a2 * t * t + 2.0 * a2 + 2.0 * a * t + 2.0
    )
    denominator = (
        a2 * t * t + a2 + 2.0 * a * t + 2.0
    ) ** 3
    return math.exp(-a * t) * math.sqrt(numerator / denominator)


def reference_torsion(t: float) -> float:
    """Return the exact closed-form torsion evaluated in binary64.

    With a = psi,

      tau(t) = (at + 1)e^(-at) / (a^2 t^2 + 2a^2 + 2at + 2).

    For a > 0 and t >= 0 this is positive and strictly decreasing.  The
    derivative has prefactor -a e^(-at) and polynomial numerator
    a^3 t^3 + 2a^3 t + 4a^2 t^2 + 6at + 2, which is positive there.
    """
    t = _validate_t(t)
    a = PSI
    denominator = a * a * t * t + 2.0 * a * a + 2.0 * a * t + 2.0
    return (a * t + 1.0) * math.exp(-a * t) / denominator


def restricted_seed_start(iterations: int = 96) -> float:
    """Return the unique t_star where kappa(t_star) == KAPPA_MAX.

    A deterministic bisection is used on the frozen seed interval.  The return
    value is the admissible side of the bracket so rounding cannot silently
    place the reported restricted start above the curvature ceiling.
    """
    if isinstance(iterations, bool) or not isinstance(iterations, int):
        raise ValueError("iterations must be an integer")
    if iterations < 32 or iterations > 256:
        raise ValueError("iterations must be in [32, 256]")

    low = SEED_T0
    high = SEED_T1
    if not reference_curvature(low) > KAPPA_MAX:
        raise ValueError("frozen seed no longer starts above the curvature bound")
    if not reference_curvature(high) < KAPPA_MAX:
        raise ValueError("frozen seed does not cross the curvature bound")

    for _ in range(iterations):
        midpoint = 0.5 * (low + high)
        if reference_curvature(midpoint) > KAPPA_MAX:
            low = midpoint
        else:
            high = midpoint
    return high


def _canonical(value: Any) -> Any:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite values cannot be receipted")
        return format(value, f".{CANONICAL_FLOAT_PRECISION}e")
    if isinstance(value, dict):
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    return value


def _canonical_dataclass_bytes(value: Any, receipt_domain: bytes) -> bytes:
    payload = asdict(value)
    payload.pop("receipt", None)
    encoded = json.dumps(
        _canonical(payload),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return receipt_domain + encoded


def _receipt(value: Any, receipt_domain: bytes) -> str:
    return hashlib.sha256(_canonical_dataclass_bytes(value, receipt_domain)).hexdigest()


def sample_reference_spine(t: float) -> ReferenceSpinePoint:
    """Evaluate one point and seal it in the reference-spine receipt domain."""
    x, y, z = reference_position(t)
    point = ReferenceSpinePoint(
        schema=REFERENCE_SPINE_SCHEMA,
        contract_version=REFERENCE_SPINE_CONTRACT_VERSION,
        t=float(t),
        x=x,
        y=y,
        z=z,
        kappa=reference_curvature(t),
        tau=reference_torsion(t),
    )
    return replace(point, receipt=_receipt(point, REFERENCE_SPINE_RECEIPT_DOMAIN))


def admission_certificate(t0: float, t1: float) -> AdmissionCertificate:
    """Seal admission evidence for a sub-interval of the frozen seed domain."""
    t0 = _validate_t(t0)
    t1 = _validate_t(t1)
    if t0 < SEED_T0 or t1 > SEED_T1 or t1 <= t0:
        raise ValueError(
            "admission interval must satisfy 0 <= t0 < t1 <= 2*pi "
            "under GammaSeed-restricted-v1"
        )

    t_star = restricted_seed_start()
    # Analytic monotonicity on t >= 0 means endpoint values are interval extrema.
    max_kappa = reference_curvature(t0)
    min_kappa = reference_curvature(t1)
    max_tau = reference_torsion(t0)
    min_tau = reference_torsion(t1)
    pass_kappa = max_kappa <= KAPPA_MAX + BOUND_TOLERANCE
    pass_tau = 0.0 < min_tau and max_tau < 1.0
    admitted = pass_kappa and pass_tau

    certificate = AdmissionCertificate(
        schema=ADMISSION_SCHEMA,
        contract_version=REFERENCE_SPINE_CONTRACT_VERSION,
        source_seed_hash=GAMMASEED_RESTRICTED_V1_HASH,
        requested_t0=t0,
        requested_t1=t1,
        t_star=t_star,
        psi=PSI,
        kappa_bound=KAPPA_MAX,
        tau_lower_exclusive=0.0,
        tau_upper_exclusive=1.0,
        max_kappa=max_kappa,
        min_kappa=min_kappa,
        max_tau=max_tau,
        min_tau=min_tau,
        pass_kappa=pass_kappa,
        pass_tau=pass_tau,
        admitted=admitted,
        disposition="ADMIT" if admitted else "REFUSE",
        monotonicity_basis="analytic-derivative-sign-on-t>=0",
        geometry_contract_modified=False,
        geometry_receipt_authority=False,
    )
    return replace(certificate, receipt=_receipt(certificate, ADMISSION_RECEIPT_DOMAIN))


def build_reference_spine_audit() -> ReferenceSpineAudit:
    """Audit full-seed refusal and restricted-seed admission together."""
    t_star = restricted_seed_start()
    full = admission_certificate(SEED_T0, SEED_T1)
    restricted = admission_certificate(t_star, SEED_T1)

    pass_full_refusal = full.disposition == "REFUSE" and not full.admitted
    pass_restricted_admission = (
        restricted.disposition == "ADMIT" and restricted.admitted
    )
    pass_unique_crossing = (
        reference_curvature(SEED_T0) > KAPPA_MAX
        and reference_curvature(SEED_T1) < KAPPA_MAX
        and abs(reference_curvature(t_star) - KAPPA_MAX) <= BOUND_TOLERANCE
    )
    pass_all = (
        pass_full_refusal
        and pass_restricted_admission
        and pass_unique_crossing
        and not full.geometry_contract_modified
        and not restricted.geometry_contract_modified
        and not full.geometry_receipt_authority
        and not restricted.geometry_receipt_authority
    )

    audit = ReferenceSpineAudit(
        schema=AUDIT_SCHEMA,
        contract_version=REFERENCE_SPINE_CONTRACT_VERSION,
        source_seed_hash=GAMMASEED_RESTRICTED_V1_HASH,
        reference_spine_schema=REFERENCE_SPINE_SCHEMA,
        psi=PSI,
        kappa_bound=KAPPA_MAX,
        seed_t0=SEED_T0,
        seed_t1=SEED_T1,
        t_star=t_star,
        kappa_at_zero=reference_curvature(0.0),
        tau_at_zero=reference_torsion(0.0),
        full_domain=full,
        restricted_domain=restricted,
        pass_full_domain_refusal=pass_full_refusal,
        pass_restricted_domain_admission=pass_restricted_admission,
        pass_unique_curvature_crossing=pass_unique_crossing,
        geometry_contract_modified=False,
        geometry_receipt_authority=False,
        pass_all=pass_all,
    )
    return replace(audit, receipt=_receipt(audit, AUDIT_RECEIPT_DOMAIN))


def write_reference_spine_audit_json(
    audit: ReferenceSpineAudit,
    path: str | Path,
) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(asdict(audit), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
