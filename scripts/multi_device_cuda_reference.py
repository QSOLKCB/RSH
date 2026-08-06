#!/usr/bin/env python3
"""Portable f32 mirror for RSH-FRENET-MULTI-DEVICE-CUDA-V1."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path

CONTRACT = "RSH-FRENET-MULTI-DEVICE-CUDA-V1"
SCHEMA = "RSH-FRENET-MULTI-DEVICE-CUDA-PORTABLE-REFERENCE-V1"
PROFILE_SCHEMA = "RSH-FRENET-MULTI-DEVICE-CUDA-CONFORMANCE-V1"
PARALLEL_CONTRACT = "RSH-FRENET-PARALLEL-V1"
SHARD_CONTRACT = "RSH-FRENET-SHARD-PREFIX-V1"
ASSIGNMENT_POLICY = "round-robin-contiguous-shards-v1"
LOCAL_POLICY = "sequential-local-inclusive-quaternion-se3-f32-v1"
BASE_POLICY = "hillis-steele-exclusive-shard-se3-f32-v1"
ASSEMBLY_POLICY = "ordered-base-compose-local-prefix-v1"
MAX_SAMPLES = 1_048_577
MAX_SHARDS = 65_536
MAX_LOGICAL_DEVICES = 64
PSI = math.sqrt(2.0 + math.sqrt(5.0))
KAPPA_BOUND = math.sqrt(2.0) - 1.0
CSV_FIELDS = (
    "index",
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
)
CLAIMS = {
    "actual_cuda_execution": False,
    "actual_multi_device_execution": False,
    "distributed_execution": False,
    "universal_speedup_claim": False,
    "geometry_receipt_authority": False,
}


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def add(left: tuple[float, float, float], right: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(f32(left[index] + right[index]) for index in range(3))


def scale(vector: tuple[float, float, float], factor: float) -> tuple[float, float, float]:
    return tuple(f32(component * factor) for component in vector)


def dot(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return f32(sum(f32(left[index] * right[index]) for index in range(3)))


def cross(left: tuple[float, float, float], right: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        f32(left[1] * right[2] - left[2] * right[1]),
        f32(left[2] * right[0] - left[0] * right[2]),
        f32(left[0] * right[1] - left[1] * right[0]),
    )


def quaternion_norm(rotation: tuple[float, float, float, float]) -> float:
    return f32(math.sqrt(sum(f32(value * value) for value in rotation)))


def normalize_quaternion(rotation: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    magnitude = quaternion_norm(rotation)
    if magnitude <= f32(1.0e-12):
        return (0.0, 0.0, 0.0, 1.0)
    return tuple(f32(value / magnitude) for value in rotation)


def quaternion_multiply(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    left_vector = left[:3]
    right_vector = right[:3]
    product_cross = cross(left_vector, right_vector)
    vector = tuple(
        f32(
            left_vector[index] * right[3]
            + right_vector[index] * left[3]
            + product_cross[index]
        )
        for index in range(3)
    )
    scalar = f32(left[3] * right[3] - dot(left_vector, right_vector))
    return (*vector, scalar)


def rotate_quaternion(
    rotation: tuple[float, float, float, float],
    vector: tuple[float, float, float],
) -> tuple[float, float, float]:
    doubled_cross = scale(cross(rotation[:3], vector), f32(2.0))
    return add(
        add(vector, scale(doubled_cross, rotation[3])),
        cross(rotation[:3], doubled_cross),
    )


def quaternion_from_omega(
    omega: tuple[float, float, float], step: float
) -> tuple[float, float, float, float]:
    half_step = f32(0.5 * step)
    half_step_squared = f32(half_step * half_step)
    half_angle_squared = f32(dot(omega, omega) * half_step_squared)
    half_angle_fourth = f32(half_angle_squared * half_angle_squared)
    sinc = f32(1.0 - half_angle_squared / 6.0 + half_angle_fourth / 120.0)
    cosine = f32(1.0 - half_angle_squared / 2.0 + half_angle_fourth / 24.0)
    return normalize_quaternion((*scale(omega, f32(half_step * sinc)), cosine))


@dataclass(frozen=True)
class TransformF32:
    rotation: tuple[float, float, float, float]
    translation: tuple[float, float, float]


def identity_f32() -> TransformF32:
    return TransformF32((0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0))


def compose_f32(left: TransformF32, right: TransformF32) -> TransformF32:
    return TransformF32(
        normalize_quaternion(quaternion_multiply(left.rotation, right.rotation)),
        add(left.translation, rotate_quaternion(left.rotation, right.translation)),
    )


def schedules_f32(
    s: float,
    kappa_fraction: float,
    tau_floor: float,
    tau_amplitude: float,
) -> tuple[float, float]:
    kappa = f32(
        f32(kappa_fraction * KAPPA_BOUND)
        * f32(0.92 + 0.08 * math.cos(f32(0.35 * s * PSI)))
    )
    tau = f32(tau_floor + tau_amplitude * f32(1.0 + math.sin(f32(0.25 * s * PSI))))
    return kappa, tau


def interval_f32(
    interval_index: int,
    samples: int,
    s0: float,
    s1: float,
    kappa_fraction: float,
    tau_floor: float,
    tau_amplitude: float,
) -> TransformF32:
    ds = f32((s1 - s0) / (samples - 1))
    midpoint = f32(s0 + f32(interval_index + 0.5) * ds)
    kappa, tau = schedules_f32(midpoint, kappa_fraction, tau_floor, tau_amplitude)
    omega = (tau, 0.0, kappa)
    rotation = quaternion_from_omega(omega, ds)
    half_rotation = quaternion_from_omega(omega, f32(0.5 * ds))
    translation = scale(rotate_quaternion(half_rotation, (1.0, 0.0, 0.0)), ds)
    return TransformF32(rotation, translation)


def partition_intervals(interval_count: int, interval_width: int) -> list[tuple[int, int]]:
    if type(interval_width) is not int or interval_width <= 0:
        raise ValueError("interval_width must be a positive integer")
    return [
        (start, min(start + interval_width, interval_count))
        for start in range(0, interval_count, interval_width)
    ]


def inclusive_doubling_scan(values: list[TransformF32]) -> tuple[list[TransformF32], int]:
    current = list(values)
    offset = 1
    passes = 0
    while offset < len(current):
        previous = list(current)
        for index in range(offset, len(current)):
            current[index] = compose_f32(previous[index - offset], previous[index])
        offset *= 2
        passes += 1
    return current, passes


def add_f64(left: tuple[float, float, float], right: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(left[index] + right[index] for index in range(3))


def scale_f64(vector: tuple[float, float, float], factor: float) -> tuple[float, float, float]:
    return tuple(component * factor for component in vector)


def dot_f64(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return sum(left[index] * right[index] for index in range(3))


def cross_f64(left: tuple[float, float, float], right: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def rotate_rodrigues_f64(
    vector: tuple[float, float, float],
    omega: tuple[float, float, float],
    step: float,
) -> tuple[float, float, float]:
    magnitude = math.sqrt(dot_f64(omega, omega))
    if magnitude <= 1.0e-15:
        return vector
    axis = scale_f64(omega, 1.0 / magnitude)
    angle = magnitude * step
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return add_f64(
        add_f64(scale_f64(vector, cosine), scale_f64(cross_f64(axis, vector), sine)),
        scale_f64(axis, dot_f64(axis, vector) * (1.0 - cosine)),
    )


@dataclass(frozen=True)
class TransformF64:
    tangent: tuple[float, float, float]
    normal: tuple[float, float, float]
    binormal: tuple[float, float, float]
    translation: tuple[float, float, float]


def identity_f64() -> TransformF64:
    return TransformF64(
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
        (0.0, 0.0, 0.0),
    )


def rotate_transform_f64(
    transform: TransformF64, vector: tuple[float, float, float]
) -> tuple[float, float, float]:
    return add_f64(
        add_f64(
            scale_f64(transform.tangent, vector[0]),
            scale_f64(transform.normal, vector[1]),
        ),
        scale_f64(transform.binormal, vector[2]),
    )


def compose_f64(left: TransformF64, right: TransformF64) -> TransformF64:
    return TransformF64(
        rotate_transform_f64(left, right.tangent),
        rotate_transform_f64(left, right.normal),
        rotate_transform_f64(left, right.binormal),
        add_f64(left.translation, rotate_transform_f64(left, right.translation)),
    )


def interval_f64(
    interval_index: int,
    samples: int,
    s0: float,
    s1: float,
    kappa_fraction: float,
    tau_floor: float,
    tau_amplitude: float,
) -> TransformF64:
    ds = (s1 - s0) / (samples - 1)
    midpoint = s0 + (interval_index + 0.5) * ds
    kappa = kappa_fraction * KAPPA_BOUND * (
        0.92 + 0.08 * math.cos(0.35 * midpoint * PSI)
    )
    tau = tau_floor + tau_amplitude * (1.0 + math.sin(0.25 * midpoint * PSI))
    omega = (tau, 0.0, kappa)
    return TransformF64(
        rotate_rodrigues_f64((1.0, 0.0, 0.0), omega, ds),
        rotate_rodrigues_f64((0.0, 1.0, 0.0), omega, ds),
        rotate_rodrigues_f64((0.0, 0.0, 1.0), omega, ds),
        scale_f64(rotate_rodrigues_f64((1.0, 0.0, 0.0), omega, 0.5 * ds), ds),
    )


def quaternion_frame(
    rotation: tuple[float, float, float, float]
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    return (
        rotate_quaternion(rotation, (1.0, 0.0, 0.0)),
        rotate_quaternion(rotation, (0.0, 1.0, 0.0)),
        rotate_quaternion(rotation, (0.0, 0.0, 1.0)),
    )


def validate_inputs(samples: int, interval_width: int, logical_devices: int) -> None:
    if type(samples) is not int or samples < 3 or samples > MAX_SAMPLES or samples % 2 == 0:
        raise ValueError("samples must be an odd integer in [3, MAX_SAMPLES]")
    if type(interval_width) is not int or interval_width <= 0:
        raise ValueError("interval_width must be a positive integer")
    if (
        type(logical_devices) is not int
        or logical_devices < 2
        or logical_devices > MAX_LOGICAL_DEVICES
    ):
        raise ValueError("logical_devices must be an integer in [2, 64]")


def build_reference(
    samples: int = 4097,
    interval_width: int = 257,
    logical_devices: int = 2,
    s0: float = 0.0,
    s1: float = 4.0,
    kappa_fraction: float = 0.85,
    tau_floor: float = 0.22,
    tau_amplitude: float = 0.13,
) -> tuple[dict[str, object], str]:
    validate_inputs(samples, interval_width, logical_devices)
    shards = partition_intervals(samples - 1, interval_width)
    if not shards or len(shards) > MAX_SHARDS:
        raise ValueError(f"shard count must be in [1, {MAX_SHARDS}]")

    local_prefixes: list[list[TransformF32]] = []
    reductions: list[TransformF32] = []
    for start, end in shards:
        current = identity_f32()
        prefixes: list[TransformF32] = []
        for interval_index in range(start, end):
            current = compose_f32(
                current,
                interval_f32(
                    interval_index,
                    samples,
                    s0,
                    s1,
                    kappa_fraction,
                    tau_floor,
                    tau_amplitude,
                ),
            )
            prefixes.append(current)
        local_prefixes.append(prefixes)
        reductions.append(current)

    inclusive, shard_prefix_passes = inclusive_doubling_scan(reductions)
    bases = [identity_f32(), *inclusive[:-1]]
    prefixes = [identity_f32()]
    assignments: list[dict[str, int]] = []
    for shard_index, ((start, end), local, base) in enumerate(
        zip(shards, local_prefixes, bases, strict=True)
    ):
        assignments.append(
            {
                "shard_index": shard_index,
                "start_interval": start,
                "end_interval_exclusive": end,
                "interval_count": end - start,
                "logical_device_slot": shard_index % logical_devices,
                "stream_ordinal": 0,
            }
        )
        prefixes.extend(compose_f32(base, transform) for transform in local)
    if len(prefixes) != samples:
        raise AssertionError("reconstructed prefix count does not match samples")

    sequential = [identity_f32()]
    current_f32 = identity_f32()
    for interval_index in range(samples - 1):
        current_f32 = compose_f32(
            current_f32,
            interval_f32(
                interval_index,
                samples,
                s0,
                s1,
                kappa_fraction,
                tau_floor,
                tau_amplitude,
            ),
        )
        sequential.append(current_f32)

    reference_f64 = [identity_f64()]
    current_f64 = identity_f64()
    for interval_index in range(samples - 1):
        current_f64 = compose_f64(
            current_f64,
            interval_f64(
                interval_index,
                samples,
                s0,
                s1,
                kappa_fraction,
                tau_floor,
                tau_amplitude,
            ),
        )
        reference_f64.append(current_f64)

    centre = prefixes[samples // 2].translation
    sequential_centre = sequential[samples // 2].translation
    reference_centre = reference_f64[samples // 2].translation
    rows: list[list[object]] = []
    max_position_vs_sequential_f32 = 0.0
    max_frame_vs_sequential_f32 = 0.0
    max_position_vs_f64 = 0.0
    max_frame_vs_f64 = 0.0
    max_schedule_vs_f64 = 0.0
    max_frame_norm_error = 0.0
    max_frame_orthogonality_error = 0.0

    for index, (transform, sequential_transform, f64_transform) in enumerate(
        zip(prefixes, sequential, reference_f64, strict=True)
    ):
        p = index / (samples - 1)
        s = s0 + p * (s1 - s0)
        kappa, tau = schedules_f32(
            f32(s), kappa_fraction, tau_floor, tau_amplitude
        )
        frame = quaternion_frame(transform.rotation)
        sequential_frame = quaternion_frame(sequential_transform.rotation)
        position = tuple(
            f32(transform.translation[axis] - centre[axis]) for axis in range(3)
        )
        sequential_position = tuple(
            f32(
                sequential_transform.translation[axis]
                - sequential_centre[axis]
            )
            for axis in range(3)
        )
        reference_position = tuple(
            f64_transform.translation[axis] - reference_centre[axis]
            for axis in range(3)
        )
        max_position_vs_sequential_f32 = max(
            max_position_vs_sequential_f32,
            *(abs(position[axis] - sequential_position[axis]) for axis in range(3)),
        )
        max_position_vs_f64 = max(
            max_position_vs_f64,
            *(abs(position[axis] - reference_position[axis]) for axis in range(3)),
        )
        for actual, sequential_vector, reference_vector in zip(
            frame,
            sequential_frame,
            (f64_transform.tangent, f64_transform.normal, f64_transform.binormal),
            strict=True,
        ):
            max_frame_vs_sequential_f32 = max(
                max_frame_vs_sequential_f32,
                *(abs(actual[axis] - sequential_vector[axis]) for axis in range(3)),
            )
            max_frame_vs_f64 = max(
                max_frame_vs_f64,
                *(abs(actual[axis] - reference_vector[axis]) for axis in range(3)),
            )
            max_frame_norm_error = max(
                max_frame_norm_error,
                abs(math.sqrt(sum(component * component for component in actual)) - 1.0),
            )
        max_frame_orthogonality_error = max(
            max_frame_orthogonality_error,
            abs(sum(frame[0][axis] * frame[1][axis] for axis in range(3))),
            abs(sum(frame[0][axis] * frame[2][axis] for axis in range(3))),
            abs(sum(frame[1][axis] * frame[2][axis] for axis in range(3))),
        )
        reference_kappa = kappa_fraction * KAPPA_BOUND * (
            0.92 + 0.08 * math.cos(0.35 * s * PSI)
        )
        reference_tau = tau_floor + tau_amplitude * (
            1.0 + math.sin(0.25 * s * PSI)
        )
        max_schedule_vs_f64 = max(
            max_schedule_vs_f64,
            abs(kappa - reference_kappa),
            abs(tau - reference_tau),
        )
        rows.append(
            [
                index,
                p,
                s,
                *position,
                kappa,
                tau,
                *frame[0],
                *frame[1],
                *frame[2],
            ]
        )

    csv_stream = io.StringIO(newline="")
    writer = csv.writer(csv_stream, lineterminator="\n")
    writer.writerow(CSV_FIELDS)
    writer.writerows(rows)
    csv_text = csv_stream.getvalue()
    path_csv_sha256 = hashlib.sha256(csv_text.encode("utf-8")).hexdigest()

    report: dict[str, object] = {
        "schema": SCHEMA,
        "contract": CONTRACT,
        "source_parallel_contract": PARALLEL_CONTRACT,
        "source_shard_prefix_contract": SHARD_CONTRACT,
        "assignment_policy": ASSIGNMENT_POLICY,
        "local_prefix_policy": LOCAL_POLICY,
        "shard_prefix_policy": BASE_POLICY,
        "assembly_policy": ASSEMBLY_POLICY,
        "configuration": {
            "samples": samples,
            "s0": s0,
            "s1": s1,
            "kappa_fraction": kappa_fraction,
            "tau_floor": tau_floor,
            "tau_amplitude": tau_amplitude,
        },
        "topology": {
            "host_count": 1,
            "logical_device_count": logical_devices,
            "stream_count_per_device": 1,
            "physical_device_execution": False,
        },
        "sharding": {
            "interval_width": interval_width,
            "intervals": samples - 1,
            "shard_count": len(shards),
            "shard_prefix_passes": shard_prefix_passes,
            "final_shard_interval_count": shards[-1][1] - shards[-1][0],
        },
        "assignments": assignments,
        "transfer_policy": {
            "composition_reduction_records": len(shards),
            "composition_base_records": len(shards),
            "inter_device_peer_bytes": 0,
            "complete_final_readback_required": True,
        },
        "residuals": {
            "max_position_vs_sequential_f32": max_position_vs_sequential_f32,
            "max_frame_vs_sequential_f32": max_frame_vs_sequential_f32,
            "max_position_vs_f64_shard_reference": max_position_vs_f64,
            "max_frame_vs_f64_shard_reference": max_frame_vs_f64,
            "max_schedule_vs_f64": max_schedule_vs_f64,
            "max_frame_norm_error": max_frame_norm_error,
            "max_frame_orthogonality_error": max_frame_orthogonality_error,
        },
        "path_csv_sha256": path_csv_sha256,
        "path_point_count": len(rows),
        "path_float_components_per_point": 16,
        "complete_path_readback": True,
        "claims": dict(CLAIMS),
    }
    canonical = json.dumps(
        report, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    report["canonical_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return report, csv_text


def verify_profile(profile_path: Path) -> tuple[dict[str, object], str]:
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    if profile.get("schema") != PROFILE_SCHEMA or profile.get("contract") != CONTRACT:
        raise ValueError("profile schema or contract mismatch")
    configuration = profile["configuration"]
    sharding = profile["sharding"]
    topology = profile["topology"]
    report, csv_text = build_reference(
        configuration["samples"],
        sharding["interval_width"],
        topology["portable_logical_device_count"],
        configuration["s0"],
        configuration["s1"],
        configuration["kappa_fraction"],
        configuration["tau_floor"],
        configuration["tau_amplitude"],
    )
    for key, expected in profile["expected"].items():
        if key in ("canonical_sha256", "path_csv_sha256"):
            actual = report[key]
        elif key in report["sharding"]:
            actual = report["sharding"][key]
        else:
            raise ValueError(f"unknown expected field: {key}")
        if actual != expected:
            raise AssertionError(f"{key}: {actual} != {expected}")
    for key, limit in profile["gates"].items():
        value = report["residuals"][key]
        if value > limit:
            raise AssertionError(f"{key}: {value} > {limit}")
    if report["claims"] != CLAIMS:
        raise AssertionError("portable claim boundary mismatch")
    return report, csv_text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-profile", type=Path)
    parser.add_argument("--samples", type=int, default=4097)
    parser.add_argument("--interval-width", type=int, default=257)
    parser.add_argument("--logical-devices", type=int, default=2)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args()
    if args.verify_profile:
        report, csv_text = verify_profile(args.verify_profile)
    else:
        report, csv_text = build_reference(
            args.samples, args.interval_width, args.logical_devices
        )
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_bytes(
            (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
        )
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        args.csv.write_bytes(csv_text.encode("utf-8"))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
