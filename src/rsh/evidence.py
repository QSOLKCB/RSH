"""Verification, canonical receipts, exports, and replay parity for RSH."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
import csv
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Any, Sequence

from .constants import (
    CANONICAL_FLOAT_PRECISION,
    KAPPA_MAX,
    MODEL_NAME,
    PSI,
    RECEIPT_DOMAIN,
    TAU_MAX_EXCLUSIVE,
    TAU_MIN_EXCLUSIVE,
    VERSION,
)
from .geometry import ModelConfig, Sample, build_path, dot, norm, sub


@dataclass(frozen=True)
class VerifyReport:
    model: str
    version: str
    samples: int
    s0: float
    s1: float
    kappa_fraction: float
    tau_floor: float
    tau_amplitude: float
    psi: float
    kappa_bound: float
    centering_mode: str
    centre_parameter: float
    centre_error: float
    min_kappa: float
    max_kappa: float
    min_tau: float
    max_tau: float
    kappa_violations: int
    tau_violations: int
    max_sampling_gap_error: float
    max_frame_norm_error: float
    max_frame_orthogonality_error: float
    min_radius: float
    max_radius: float
    path_length: float
    entry: tuple[float, float, float]
    centre: tuple[float, float, float]
    exit: tuple[float, float, float]
    endpoint_separation: float
    pass_centre: bool
    pass_kappa: bool
    pass_tau: bool
    pass_sampling: bool
    pass_frame: bool
    pass_all: bool
    receipt: str = ""


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


def canonical_report_bytes(report: VerifyReport) -> bytes:
    payload = asdict(report)
    payload.pop("receipt", None)
    return json.dumps(
        _canonical(payload),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def make_receipt(report: VerifyReport) -> str:
    return hashlib.sha256(
        RECEIPT_DOMAIN + canonical_report_bytes(report)
    ).hexdigest()


def verify(
    rows: Sequence[Sample],
    config: ModelConfig,
    centre_tolerance: float = 1.0e-12,
) -> VerifyReport:
    config = config.validate()
    if len(rows) != config.samples:
        raise ValueError(
            "row count does not match the validated model configuration"
        )

    centre = rows[len(rows) // 2]
    kappas = [row.kappa for row in rows]
    taus = [row.tau for row in rows]
    radii = [row.radius for row in rows]
    gaps = [
        rows[index + 1].p - rows[index].p
        for index in range(len(rows) - 1)
    ]
    ideal_gap = 1.0 / (len(rows) - 1)
    gap_error = max(abs(gap - ideal_gap) / ideal_gap for gap in gaps)

    path_length = sum(
        norm(sub(rows[index + 1].position, rows[index].position))
        for index in range(len(rows) - 1)
    )

    frame_norm_error = 0.0
    frame_orthogonality_error = 0.0
    for index, row in enumerate(rows):
        frame = (row.tangent, row.normal, row.binormal)
        if not all(
            math.isfinite(component)
            for vector in frame
            for component in vector
        ):
            raise ValueError(
                f"sample {index} contains a non-finite frame component"
            )
        frame_norm_error = max(
            frame_norm_error,
            *(abs(norm(vector) - 1.0) for vector in frame),
        )
        frame_orthogonality_error = max(
            frame_orthogonality_error,
            abs(dot(frame[0], frame[1])),
            abs(dot(frame[0], frame[2])),
            abs(dot(frame[1], frame[2])),
        )

    centre_error = norm(centre.position)
    kappa_violations = sum(
        not (0.0 <= value <= KAPPA_MAX + 1.0e-12)
        for value in kappas
    )
    tau_violations = sum(
        not (TAU_MIN_EXCLUSIVE < value < TAU_MAX_EXCLUSIVE)
        for value in taus
    )
    pass_centre = centre_error <= centre_tolerance and centre.p == 0.5
    pass_kappa = kappa_violations == 0
    pass_tau = tau_violations == 0
    pass_sampling = gap_error <= 1.0e-12
    pass_frame = (
        frame_norm_error <= 1.0e-12
        and frame_orthogonality_error <= 1.0e-12
    )

    report = VerifyReport(
        model=MODEL_NAME,
        version=VERSION,
        samples=len(rows),
        s0=config.s0,
        s1=config.s1,
        kappa_fraction=config.kappa_fraction,
        tau_floor=config.tau_floor,
        tau_amplitude=config.tau_amplitude,
        psi=PSI,
        kappa_bound=KAPPA_MAX,
        centering_mode="midpoint-coordinate-normalisation",
        centre_parameter=centre.p,
        centre_error=centre_error,
        min_kappa=min(kappas),
        max_kappa=max(kappas),
        min_tau=min(taus),
        max_tau=max(taus),
        kappa_violations=int(kappa_violations),
        tau_violations=int(tau_violations),
        max_sampling_gap_error=gap_error,
        max_frame_norm_error=frame_norm_error,
        max_frame_orthogonality_error=frame_orthogonality_error,
        min_radius=min(radii),
        max_radius=max(radii),
        path_length=path_length,
        entry=rows[0].position,
        centre=centre.position,
        exit=rows[-1].position,
        endpoint_separation=norm(
            sub(rows[-1].position, rows[0].position)
        ),
        pass_centre=pass_centre,
        pass_kappa=pass_kappa,
        pass_tau=pass_tau,
        pass_sampling=pass_sampling,
        pass_frame=pass_frame,
        pass_all=(
            pass_centre
            and pass_kappa
            and pass_tau
            and pass_sampling
            and pass_frame
        ),
    )
    return replace(report, receipt=make_receipt(report))


def build_and_verify(
    config: ModelConfig = ModelConfig(),
) -> tuple[tuple[Sample, ...], VerifyReport]:
    config = config.validate()
    rows = build_path(config)
    return rows, verify(rows, config)


def verify_parallel(
    config: ModelConfig,
    workers: int = 2,
) -> tuple[VerifyReport, tuple[VerifyReport, ...], bool]:
    """Run independent concurrent replays and compare canonical receipts.

    This proves concurrent replay parity. It does not claim that integration is
    partitioned across workers.
    """
    if workers < 1:
        raise ValueError("workers must be positive")
    baseline = build_and_verify(config)[1]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        reports = tuple(
            executor.map(
                lambda _: build_and_verify(config)[1],
                range(workers),
            )
        )
    return (
        baseline,
        reports,
        all(report.receipt == baseline.receipt for report in reports),
    )


def benchmark(
    config: ModelConfig,
    loops: int = 20,
) -> dict[str, float | int | str | bool]:
    if loops < 1:
        raise ValueError("loops must be positive")
    start = time.perf_counter_ns()
    report: VerifyReport | None = None
    for _ in range(loops):
        report = build_and_verify(config)[1]
    elapsed = time.perf_counter_ns() - start
    assert report is not None
    return {
        "loops": loops,
        "samples": config.samples,
        "elapsed_ns": elapsed,
        "ns_per_loop": elapsed / loops,
        "pass_all": report.pass_all,
        "receipt": report.receipt,
    }


def write_trace_csv(rows: Sequence[Sample], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "p",
                "s",
                "x",
                "y",
                "z",
                "kappa",
                "tau",
                "tx",
                "ty",
                "tz",
                "nx",
                "ny",
                "nz",
                "bx",
                "by",
                "bz",
                "radius",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    format(value, ".17e")
                    for value in (
                        row.p,
                        row.s,
                        row.x,
                        row.y,
                        row.z,
                        row.kappa,
                        row.tau,
                        row.tx,
                        row.ty,
                        row.tz,
                        row.nx,
                        row.ny,
                        row.nz,
                        row.bx,
                        row.by,
                        row.bz,
                        row.radius,
                    )
                ]
            )


def write_verify_csv(report: VerifyReport, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["metric", "value"])
        for key, value in asdict(report).items():
            if isinstance(value, float):
                encoded = format(value, ".17e")
            elif isinstance(value, tuple):
                encoded = ";".join(
                    format(item, ".17e") for item in value
                )
            else:
                encoded = (
                    str(value).lower()
                    if isinstance(value, bool)
                    else str(value)
                )
            writer.writerow([key, encoded])


def write_report_json(report: VerifyReport, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
