"""Bound-safe Frenet–Serret geometry for RSH.

The path is generated from prescribed curvature and torsion schedules. The
central sample is then translated to the origin as an explicit coordinate
normalisation. The normalisation is part of the construction; it is not an
empirical result.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Callable, Sequence, Tuple

from .constants import (
    KAPPA_MAX,
    PSI,
    TAU_MAX_EXCLUSIVE,
    TAU_MIN_EXCLUSIVE,
)

Vec3 = Tuple[float, float, float]
Schedule = Callable[[float], float]


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(v: Vec3) -> float:
    """Return a stable Euclidean norm without squaring components first."""
    return math.hypot(*v)


def add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(v: Vec3, amount: float) -> Vec3:
    return (v[0] * amount, v[1] * amount, v[2] * amount)


def normalize(v: Vec3) -> Vec3:
    magnitude = norm(v)
    if not math.isfinite(magnitude):
        raise ValueError("cannot normalize a non-finite vector")
    if magnitude <= 1.0e-15:
        raise ValueError("cannot normalize a near-zero vector")
    return scale(v, 1.0 / magnitude)


def orthonormalize(
    tangent: Vec3,
    normal: Vec3,
    binormal: Vec3,
) -> tuple[Vec3, Vec3, Vec3]:
    tangent = normalize(tangent)
    normal = sub(normal, scale(tangent, dot(normal, tangent)))
    normal = normalize(normal)
    binormal = normalize(cross(tangent, normal))
    return tangent, normal, binormal


@dataclass(frozen=True)
class ModelConfig:
    """Validated construction parameters.

    An odd sample count is required so the discrete path contains an exact
    p=0.5 sample before translation.
    """

    samples: int = 513
    s0: float = 0.0
    s1: float = 4.0
    kappa_fraction: float = 0.85
    tau_floor: float = 0.22
    tau_amplitude: float = 0.13

    def validate(self) -> "ModelConfig":
        if self.samples < 3:
            raise ValueError("samples must be at least 3")
        if self.samples % 2 == 0:
            raise ValueError("samples must be odd so p=0.5 is represented exactly")
        if not math.isfinite(self.s0) or not math.isfinite(self.s1) or self.s1 <= self.s0:
            raise ValueError("s1 must be finite and greater than s0")
        if not math.isfinite(self.kappa_fraction) or not (
            0.0 < self.kappa_fraction <= 1.0
        ):
            raise ValueError("kappa_fraction must be finite and in (0, 1]")
        if not math.isfinite(self.tau_floor) or not math.isfinite(self.tau_amplitude):
            raise ValueError("torsion schedule parameters must be finite")
        if self.tau_amplitude < 0.0:
            raise ValueError("tau_amplitude must be non-negative")
        tau_min = self.tau_floor
        tau_max = self.tau_floor + 2.0 * self.tau_amplitude
        if not (
            TAU_MIN_EXCLUSIVE < tau_min < TAU_MAX_EXCLUSIVE
            and TAU_MIN_EXCLUSIVE < tau_max < TAU_MAX_EXCLUSIVE
        ):
            raise ValueError(
                "the torsion schedule must remain strictly inside "
                f"({TAU_MIN_EXCLUSIVE:g}, {TAU_MAX_EXCLUSIVE:g})"
            )
        return self


@dataclass(frozen=True)
class Sample:
    s: float
    p: float
    x: float
    y: float
    z: float
    kappa: float
    tau: float
    tx: float
    ty: float
    tz: float
    nx: float
    ny: float
    nz: float
    bx: float
    by: float
    bz: float

    @property
    def position(self) -> Vec3:
        return (self.x, self.y, self.z)

    @property
    def tangent(self) -> Vec3:
        return (self.tx, self.ty, self.tz)

    @property
    def normal(self) -> Vec3:
        return (self.nx, self.ny, self.nz)

    @property
    def binormal(self) -> Vec3:
        return (self.bx, self.by, self.bz)

    @property
    def radius(self) -> float:
        return norm(self.position)


def kappa_schedule(s: float, config: ModelConfig = ModelConfig()) -> float:
    """Smooth curvature schedule that cannot exceed the Robitaille bound."""
    base = config.kappa_fraction * KAPPA_MAX
    return base * (0.92 + 0.08 * math.cos(0.35 * s * PSI))


def tau_schedule(s: float, config: ModelConfig = ModelConfig()) -> float:
    """Smooth torsion schedule strictly inside the configured open interval."""
    return config.tau_floor + config.tau_amplitude * (
        1.0 + math.sin(0.25 * s * PSI)
    )


def _frame_derivative(
    tangent: Vec3,
    normal: Vec3,
    binormal: Vec3,
    kappa: float,
    tau: float,
) -> tuple[Vec3, Vec3, Vec3]:
    tangent_prime = scale(normal, kappa)
    normal_prime = add(scale(tangent, -kappa), scale(binormal, tau))
    binormal_prime = scale(normal, -tau)
    return tangent_prime, normal_prime, binormal_prime


def integrate_path(
    config: ModelConfig = ModelConfig(),
    kappa_fn: Schedule | None = None,
    tau_fn: Schedule | None = None,
) -> tuple[Sample, ...]:
    """Integrate position and the Frenet–Serret frame with a midpoint step.

    The frame is re-orthonormalised after every step to control numerical drift.
    Custom schedules are accepted for research experiments, but are checked at
    every sample and midpoint before they are applied.
    """
    config = config.validate()
    kappa_fn = kappa_fn or (lambda s: kappa_schedule(s, config))
    tau_fn = tau_fn or (lambda s: tau_schedule(s, config))

    ds = (config.s1 - config.s0) / (config.samples - 1)
    tangent: Vec3 = (1.0, 0.0, 0.0)
    normal: Vec3 = (0.0, 1.0, 0.0)
    binormal: Vec3 = (0.0, 0.0, 1.0)
    position: Vec3 = (0.0, 0.0, 0.0)
    rows: list[Sample] = []

    def checked_values(s: float) -> tuple[float, float]:
        kappa = float(kappa_fn(s))
        tau = float(tau_fn(s))
        if not math.isfinite(kappa) or not (
            0.0 <= kappa <= KAPPA_MAX + 1.0e-12
        ):
            raise ValueError(f"curvature schedule violates its bound at s={s!r}")
        if not math.isfinite(tau) or not (
            TAU_MIN_EXCLUSIVE < tau < TAU_MAX_EXCLUSIVE
        ):
            raise ValueError(
                "torsion schedule leaves "
                f"({TAU_MIN_EXCLUSIVE:g}, {TAU_MAX_EXCLUSIVE:g}) at s={s!r}"
            )
        return kappa, tau

    for index in range(config.samples):
        s = config.s0 + index * ds
        p = index / (config.samples - 1)
        kappa, tau = checked_values(s)
        rows.append(
            Sample(
                s=s,
                p=p,
                x=position[0],
                y=position[1],
                z=position[2],
                kappa=kappa,
                tau=tau,
                tx=tangent[0],
                ty=tangent[1],
                tz=tangent[2],
                nx=normal[0],
                ny=normal[1],
                nz=normal[2],
                bx=binormal[0],
                by=binormal[1],
                bz=binormal[2],
            )
        )
        if index == config.samples - 1:
            break

        tangent_prime, normal_prime, binormal_prime = _frame_derivative(
            tangent, normal, binormal, kappa, tau
        )
        tangent_mid = add(tangent, scale(tangent_prime, 0.5 * ds))
        normal_mid = add(normal, scale(normal_prime, 0.5 * ds))
        binormal_mid = add(binormal, scale(binormal_prime, 0.5 * ds))
        tangent_mid, normal_mid, binormal_mid = orthonormalize(
            tangent_mid, normal_mid, binormal_mid
        )

        kappa_mid, tau_mid = checked_values(s + 0.5 * ds)
        tangent_prime, normal_prime, binormal_prime = _frame_derivative(
            tangent_mid, normal_mid, binormal_mid, kappa_mid, tau_mid
        )

        # Position obeys x' = T, so the same midpoint frame used for the
        # derivative must advance the coordinates.
        position = add(position, scale(tangent_mid, ds))
        tangent = add(tangent, scale(tangent_prime, ds))
        normal = add(normal, scale(normal_prime, ds))
        binormal = add(binormal, scale(binormal_prime, ds))
        tangent, normal, binormal = orthonormalize(tangent, normal, binormal)

    return tuple(rows)


def centre_path(rows: Sequence[Sample]) -> tuple[Sample, ...]:
    """Translate the exact p=0.5 sample to the origin."""
    if len(rows) < 3 or len(rows) % 2 == 0:
        raise ValueError("centre_path requires an odd number of at least 3 samples")
    centre = rows[len(rows) // 2]
    offset = centre.position
    return tuple(
        replace(
            sample,
            x=sample.x - offset[0],
            y=sample.y - offset[1],
            z=sample.z - offset[2],
        )
        for sample in rows
    )


def build_path(config: ModelConfig = ModelConfig()) -> tuple[Sample, ...]:
    return centre_path(integrate_path(config))


def logical_sample_indices(
    logical_count: int,
    rendered_count: int,
) -> tuple[int, ...]:
    """Map a large logical field to bounded representatives with exact integers.

    No allocation proportional to ``logical_count`` is performed.
    """
    if logical_count < 1:
        raise ValueError("logical_count must be positive")
    if rendered_count < 1:
        raise ValueError("rendered_count must be positive")
    if rendered_count > logical_count:
        raise ValueError("rendered_count cannot exceed logical_count")
    return tuple(
        (index * logical_count) // rendered_count
        for index in range(rendered_count)
    )
