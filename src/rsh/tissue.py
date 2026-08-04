"""Deterministic multi-cell tissue simulation seeded by verified RSH geometry.

The tissue layer is an experimental systems model over bounded geometric states.
``Q_f`` is a functional cohesion metric. It is not a measure or claim of
biological life, consciousness, subjective awareness, or qualia.
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .constants import (
    CANONICAL_FLOAT_PRECISION,
    KAPPA_MAX,
    MODEL_NAME,
    PSI,
    VERSION,
)
from .constitution import (
    CONSTITUTION_VERSION,
    constitution_hash,
    validate_constitution,
)
from .evidence import build_and_verify
from .geometry import ModelConfig

TISSUE_CONTRACT_VERSION = "1.0.0"
TISSUE_SCHEMA = "RSH-TISSUE-REPORT-V1"
TICK_SCHEMA = "RSH-TISSUE-TICK-V1"
TISSUE_RECEIPT_DOMAIN = b"RSH-TISSUE-EVIDENCE-V1\0"
TICK_RECEIPT_DOMAIN = b"RSH-TISSUE-TICK-V1\0"
ROLES = ("R", "W", "P")
SIDECAR_BACKENDS = ("none", "webgpu", "cuda", "npu")
MAX_TISSUE_WORK = 5_000_000


def _canonical(value: Any) -> Any:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite tissue evidence value")
        return format(value, f".{CANONICAL_FLOAT_PRECISION}e")
    if isinstance(value, dict):
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        _canonical(payload),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def _digest(domain: bytes, payload: Any) -> str:
    return hashlib.sha256(domain + _canonical_bytes(payload)).hexdigest()


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _angle_delta(target: float, current: float) -> float:
    return (target - current + math.pi) % (2.0 * math.pi) - math.pi


@dataclass(frozen=True)
class TissueConfig:
    cells: int = 8
    ticks: int = 20
    geometry_samples: int = 129
    ds: float = 0.05
    phase_coupling: float = 0.25
    binding_diffusion: float = 0.15
    sidecar_backend: str = "none"
    sidecar_residual: float = 0.0
    residual_gate: float = 1.0e-4
    qf_floor: float = 0.0

    def validate(self) -> "TissueConfig":
        for name in ("cells", "ticks", "geometry_samples"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be a non-boolean integer")

        if self.cells < 3 or self.cells > 4096:
            raise ValueError("cells must be in [3, 4096]")
        if self.ticks < 1 or self.ticks > 100_000:
            raise ValueError("ticks must be in [1, 100000]")
        if self.cells * self.ticks > MAX_TISSUE_WORK:
            raise ValueError(
                "cells × ticks exceeds the bounded tissue work limit"
            )
        if (
            self.geometry_samples < self.cells
            or self.geometry_samples < 3
            or self.geometry_samples > 262_145
            or self.geometry_samples % 2 == 0
        ):
            raise ValueError(
                "geometry_samples must be odd, at least cells, and no more "
                "than 262145"
            )

        numeric = (
            ("ds", self.ds),
            ("phase_coupling", self.phase_coupling),
            ("binding_diffusion", self.binding_diffusion),
            ("sidecar_residual", self.sidecar_residual),
            ("residual_gate", self.residual_gate),
            ("qf_floor", self.qf_floor),
        )
        for name, value in numeric:
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")

        if not (0.0 < self.ds <= 1.0):
            raise ValueError("ds must be in (0, 1]")
        if not (0.0 <= self.phase_coupling <= 1.0):
            raise ValueError("phase_coupling must be in [0, 1]")
        if not (0.0 <= self.binding_diffusion <= 1.0):
            raise ValueError("binding_diffusion must be in [0, 1]")
        if self.sidecar_backend not in SIDECAR_BACKENDS:
            raise ValueError(
                f"sidecar_backend must be one of {SIDECAR_BACKENDS}"
            )
        if self.sidecar_residual < 0.0:
            raise ValueError("sidecar_residual must be non-negative")
        if self.residual_gate <= 0.0:
            raise ValueError("residual_gate must be positive")
        if not (0.0 <= self.qf_floor <= 1.0):
            raise ValueError("qf_floor must be in [0, 1]")
        if self.sidecar_backend == "none" and self.sidecar_residual != 0.0:
            raise ValueError(
                "sidecar_residual must be zero when no sidecar is requested"
            )
        return self


@dataclass
class CellState:
    id: str
    x: float
    y: float
    z: float
    kappa: float
    tau: float
    phase: float
    role: str
    binding: float
    prediction_error: float = 0.0

    def project_bounds(self) -> bool:
        before = (self.kappa, self.tau)
        self.kappa = _clamp(self.kappa, 0.0, KAPPA_MAX)
        self.tau = _clamp(self.tau, 1.0e-12, 1.0 - 1.0e-12)
        return before != (self.kappa, self.tau)


@dataclass(frozen=True)
class CellSnapshot:
    id: str
    x: float
    y: float
    z: float
    kappa: float
    tau: float
    phase: float
    role: str
    binding: float
    prediction_error: float


@dataclass(frozen=True)
class TissueMetrics:
    phase_coherence: float
    binding_cohesion: float
    predictive_stability: float
    edge_continuity: float
    role_coverage: float
    dissociation: float
    q_f: float


@dataclass(frozen=True)
class TissueTick:
    schema: str
    index: int
    previous_receipt: str
    centre_shift: tuple[float, float, float]
    centre_error: float
    bound_fixes: int
    sidecar_accepted: bool
    fallback_used: bool
    metrics: TissueMetrics
    receipt: str = ""


@dataclass(frozen=True)
class TissueReport:
    schema: str
    tissue_contract: str
    geometry_model: str
    geometry_model_contract: str
    constitution_version: str
    constitution_hash: str
    config: TissueConfig
    seed_geometry_receipt: str
    edges: tuple[tuple[int, int], ...]
    roles: tuple[str, ...]
    ticks: tuple[TissueTick, ...]
    final_cells: tuple[CellSnapshot, ...]
    final_q_f: float
    min_q_f: float
    max_q_f: float
    sidecar_accepted: bool
    fallback_used: bool
    pass_constitution: bool
    pass_bounds: bool
    pass_centre: bool
    pass_qf_floor: bool
    audit_chain_valid: bool
    pass_all: bool
    receipt: str = ""


def _sample_indices(samples: int, cells: int) -> tuple[int, ...]:
    return tuple(
        (index * (samples - 1)) // (cells - 1)
        for index in range(cells)
    )


def _snapshot(cell: CellState) -> CellSnapshot:
    return CellSnapshot(
        id=cell.id,
        x=cell.x,
        y=cell.y,
        z=cell.z,
        kappa=cell.kappa,
        tau=cell.tau,
        phase=cell.phase,
        role=cell.role,
        binding=cell.binding,
        prediction_error=cell.prediction_error,
    )


def _initial_state(
    config: TissueConfig,
) -> tuple[list[CellState], tuple[tuple[int, int], ...], str]:
    model = ModelConfig(samples=config.geometry_samples).validate()
    rows, geometry_report = build_and_verify(model)
    indices = _sample_indices(len(rows), config.cells)

    cells: list[CellState] = []
    for index, sample_index in enumerate(indices):
        sample = rows[sample_index]
        cells.append(
            CellState(
                id=f"C{index}",
                x=sample.x,
                y=sample.y,
                z=sample.z,
                kappa=sample.kappa,
                tau=sample.tau,
                phase=math.atan2(sample.ty, sample.tx)
                % (2.0 * math.pi),
                role=ROLES[index % len(ROLES)],
                binding=(index + 1) / (config.cells + 1),
            )
        )

    edge_set = {
        (index, (index + 1) % config.cells)
        for index in range(config.cells)
    }
    if config.cells >= 4:
        half = config.cells // 2
        for index in range(0, config.cells, 2):
            left, right = sorted(
                (index, (index + half) % config.cells)
            )
            if left != right:
                edge_set.add((left, right))

    return (
        cells,
        tuple(sorted(edge_set)),
        geometry_report.receipt,
    )


def _neighbours(
    count: int,
    edges: tuple[tuple[int, int], ...],
) -> dict[int, list[int]]:
    result = {index: [] for index in range(count)}
    for left, right in edges:
        result[left].append(right)
        result[right].append(left)
    return result


def _shared_centre(
    cells: list[CellState],
) -> tuple[float, float, float]:
    count = len(cells)
    centre = (
        sum(cell.x for cell in cells) / count,
        sum(cell.y for cell in cells) / count,
        sum(cell.z for cell in cells) / count,
    )
    for cell in cells:
        cell.x -= centre[0]
        cell.y -= centre[1]
        cell.z -= centre[2]
    return centre


def _centre_error(cells: list[CellState]) -> float:
    count = len(cells)
    return math.hypot(
        sum(cell.x for cell in cells) / count,
        sum(cell.y for cell in cells) / count,
        sum(cell.z for cell in cells) / count,
    )


def _phase_lock(cells: list[CellState], amount: float) -> None:
    sine = sum(math.sin(cell.phase) for cell in cells)
    cosine = sum(math.cos(cell.phase) for cell in cells)
    target = math.atan2(sine, cosine)
    for cell in cells:
        cell.phase = (
            cell.phase + amount * _angle_delta(target, cell.phase)
        ) % (2.0 * math.pi)


def _binding_diffuse(
    cells: list[CellState],
    neighbours: dict[int, list[int]],
    amount: float,
) -> None:
    values: list[float] = []
    for index, cell in enumerate(cells):
        adjacent = neighbours[index]
        if not adjacent:
            values.append(cell.binding)
            continue
        mean = sum(cells[item].binding for item in adjacent) / len(adjacent)
        curvature_pressure = 0.002 * (cell.kappa / KAPPA_MAX)
        values.append(
            max(
                1.0e-12,
                cell.binding
                + amount * (mean - cell.binding)
                - curvature_pressure,
            )
        )
    for cell, value in zip(cells, values):
        cell.binding = value


def _prediction_errors(
    cells: list[CellState],
    neighbours: dict[int, list[int]],
) -> None:
    for index, cell in enumerate(cells):
        adjacent = neighbours[index]
        if not adjacent:
            cell.prediction_error = 0.0
            continue
        sine = sum(math.sin(cells[item].phase) for item in adjacent)
        cosine = sum(math.cos(cells[item].phase) for item in adjacent)
        target = math.atan2(sine, cosine)
        phase_error = abs(_angle_delta(target, cell.phase)) / math.pi
        tau_error = sum(
            abs(cell.tau - cells[item].tau)
            for item in adjacent
        ) / len(adjacent)
        cell.prediction_error = 0.75 * phase_error + 0.25 * tau_error


def _edge_lengths(
    cells: list[CellState],
    edges: tuple[tuple[int, int], ...],
) -> list[float]:
    return [
        math.dist(
            (cells[left].x, cells[left].y, cells[left].z),
            (cells[right].x, cells[right].y, cells[right].z),
        )
        for left, right in edges
    ]


def _metrics(
    cells: list[CellState],
    edges: tuple[tuple[int, int], ...],
    bound_fixes: int,
    sidecar_pressure: float,
) -> TissueMetrics:
    count = len(cells)
    phase_coherence = _clamp(
        math.hypot(
            sum(math.cos(cell.phase) for cell in cells),
            sum(math.sin(cell.phase) for cell in cells),
        )
        / count,
        0.0,
        1.0,
    )

    bindings = [cell.binding for cell in cells]
    binding_mean = sum(bindings) / count
    if binding_mean <= 1.0e-15:
        binding_cohesion = 0.0
    else:
        binding_variance = sum(
            (value - binding_mean) ** 2 for value in bindings
        ) / count
        binding_cohesion = 1.0 / (
            1.0 + math.sqrt(binding_variance) / binding_mean
        )

    predictive_stability = math.exp(
        -sum(cell.prediction_error for cell in cells) / count
    )

    edge_lengths = _edge_lengths(cells, edges)
    if not edge_lengths:
        edge_continuity = 1.0
    else:
        edge_mean = sum(edge_lengths) / len(edge_lengths)
        edge_variance = sum(
            (value - edge_mean) ** 2 for value in edge_lengths
        ) / len(edge_lengths)
        edge_continuity = math.exp(
            -math.sqrt(edge_variance) / (edge_mean + 1.0e-15)
        )

    role_coverage = len({cell.role for cell in cells}) / len(ROLES)
    fix_pressure = min(
        1.0,
        bound_fixes / max(1, 2 * len(edges)),
    )
    dissociation = _clamp(
        0.55 * (1.0 - phase_coherence)
        + 0.25 * fix_pressure
        + 0.20 * sidecar_pressure,
        0.0,
        1.0,
    )
    q_f = _clamp(
        phase_coherence
        * binding_cohesion
        * predictive_stability
        * edge_continuity
        * role_coverage
        * (1.0 - dissociation),
        0.0,
        1.0,
    )
    return TissueMetrics(
        phase_coherence=phase_coherence,
        binding_cohesion=binding_cohesion,
        predictive_stability=predictive_stability,
        edge_continuity=edge_continuity,
        role_coverage=role_coverage,
        dissociation=dissociation,
        q_f=q_f,
    )


def _tick_receipt(tick: TissueTick) -> str:
    payload = asdict(tick)
    payload.pop("receipt", None)
    return _digest(TICK_RECEIPT_DOMAIN, payload)


def _report_receipt(report: TissueReport) -> str:
    payload = asdict(report)
    payload.pop("receipt", None)
    return _digest(TISSUE_RECEIPT_DOMAIN, payload)


def validate_audit_chain(
    ticks: tuple[TissueTick, ...],
    seed_receipt: str,
    *,
    expected_ticks: int,
    terminal_receipt: str | None = None,
) -> bool:
    """Validate a complete receipt chain with an explicit expected length.

    Requiring the expected length prevents an empty or truncated prefix from
    being accepted merely because every remaining link is internally valid.
    ``terminal_receipt`` may additionally pin the final tick identity when a
    report or external manifest publishes it separately.
    """
    if isinstance(expected_ticks, bool) or not isinstance(expected_ticks, int):
        return False
    if expected_ticks < 1 or len(ticks) != expected_ticks:
        return False
    if not isinstance(seed_receipt, str) or not seed_receipt:
        return False

    previous = seed_receipt
    for expected_index, tick in enumerate(ticks, start=1):
        if tick.schema != TICK_SCHEMA or tick.index != expected_index:
            return False
        if tick.previous_receipt != previous:
            return False
        if tick.receipt != _tick_receipt(tick):
            return False
        previous = tick.receipt

    if terminal_receipt is not None and previous != terminal_receipt:
        return False
    return True


def simulate_tissue(
    config: TissueConfig = TissueConfig(),
) -> TissueReport:
    config = config.validate()
    cells, edges, seed_receipt = _initial_state(config)
    neighbours = _neighbours(len(cells), edges)
    tick_history: list[TissueTick] = []
    previous_receipt = seed_receipt

    sidecar_requested = config.sidecar_backend != "none"
    sidecar_accepted = (
        sidecar_requested
        and config.sidecar_residual <= config.residual_gate
    )
    fallback_used = sidecar_requested and not sidecar_accepted
    sidecar_pressure = (
        min(1.0, config.sidecar_residual / config.residual_gate)
        if sidecar_requested
        else 0.0
    )

    for tick_index in range(1, config.ticks + 1):
        bound_fixes = 0
        for cell in cells:
            bound_fixes += int(cell.project_bounds())
            cell.phase = (
                cell.phase + cell.tau * config.ds * PSI
            ) % (2.0 * math.pi)
            speed = max(
                0.05,
                1.0 - 0.35 * (cell.kappa / KAPPA_MAX),
            )
            cell.x += config.ds * math.cos(cell.phase) * speed
            cell.y += config.ds * math.sin(cell.phase) * speed
            cell.z += config.ds * cell.tau * 0.1
            bound_fixes += int(cell.project_bounds())

        _phase_lock(cells, config.phase_coupling)
        _binding_diffuse(cells, neighbours, config.binding_diffusion)
        _prediction_errors(cells, neighbours)
        centre_shift = _shared_centre(cells)
        centre_error = _centre_error(cells)
        metrics = _metrics(
            cells,
            edges,
            bound_fixes,
            sidecar_pressure,
        )

        unsealed = TissueTick(
            schema=TICK_SCHEMA,
            index=tick_index,
            previous_receipt=previous_receipt,
            centre_shift=centre_shift,
            centre_error=centre_error,
            bound_fixes=bound_fixes,
            sidecar_accepted=sidecar_accepted,
            fallback_used=fallback_used,
            metrics=metrics,
        )
        sealed = replace(unsealed, receipt=_tick_receipt(unsealed))
        tick_history.append(sealed)
        previous_receipt = sealed.receipt

    final_cells = tuple(_snapshot(cell) for cell in cells)
    ticks = tuple(tick_history)
    q_values = [tick.metrics.q_f for tick in ticks]

    pass_constitution = not validate_constitution()
    pass_bounds = all(
        0.0 <= cell.kappa <= KAPPA_MAX
        and 0.0 < cell.tau < 1.0
        for cell in final_cells
    )
    pass_centre = max(tick.centre_error for tick in ticks) <= 1.0e-12
    pass_qf_floor = q_values[-1] >= config.qf_floor
    audit_chain_valid = validate_audit_chain(
        ticks,
        seed_receipt,
        expected_ticks=config.ticks,
    )
    pass_all = (
        pass_constitution
        and pass_bounds
        and pass_centre
        and pass_qf_floor
        and audit_chain_valid
    )

    report = TissueReport(
        schema=TISSUE_SCHEMA,
        tissue_contract=TISSUE_CONTRACT_VERSION,
        geometry_model=MODEL_NAME,
        geometry_model_contract=VERSION,
        constitution_version=CONSTITUTION_VERSION,
        constitution_hash=constitution_hash(),
        config=config,
        seed_geometry_receipt=seed_receipt,
        edges=edges,
        roles=tuple(cell.role for cell in final_cells),
        ticks=ticks,
        final_cells=final_cells,
        final_q_f=q_values[-1],
        min_q_f=min(q_values),
        max_q_f=max(q_values),
        sidecar_accepted=sidecar_accepted,
        fallback_used=fallback_used,
        pass_constitution=pass_constitution,
        pass_bounds=pass_bounds,
        pass_centre=pass_centre,
        pass_qf_floor=pass_qf_floor,
        audit_chain_valid=audit_chain_valid,
        pass_all=pass_all,
    )
    return replace(report, receipt=_report_receipt(report))


def tissue_report_json(report: TissueReport) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True) + "\n"


def write_tissue_report_json(
    report: TissueReport,
    path: str | Path,
) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(tissue_report_json(report), encoding="utf-8")


def write_tissue_trace_csv(
    report: TissueReport,
    path: str | Path,
) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "tick",
                "centre_error",
                "bound_fixes",
                "phase_coherence",
                "binding_cohesion",
                "predictive_stability",
                "edge_continuity",
                "role_coverage",
                "dissociation",
                "q_f",
                "sidecar_accepted",
                "fallback_used",
                "receipt",
            ]
        )
        for tick in report.ticks:
            writer.writerow(
                [
                    tick.index,
                    format(tick.centre_error, ".17e"),
                    tick.bound_fixes,
                    format(tick.metrics.phase_coherence, ".17e"),
                    format(tick.metrics.binding_cohesion, ".17e"),
                    format(tick.metrics.predictive_stability, ".17e"),
                    format(tick.metrics.edge_continuity, ".17e"),
                    format(tick.metrics.role_coverage, ".17e"),
                    format(tick.metrics.dissociation, ".17e"),
                    format(tick.metrics.q_f, ".17e"),
                    str(tick.sidecar_accepted).lower(),
                    str(tick.fallback_used).lower(),
                    tick.receipt,
                ]
            )
