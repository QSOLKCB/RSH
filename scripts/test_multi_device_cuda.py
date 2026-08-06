#!/usr/bin/env python3
"""Run and validate the trusted RSH multi-device CUDA path experiment."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

CONTRACT = "RSH-FRENET-MULTI-DEVICE-CUDA-V1"
SCHEMA = "RSH-FRENET-MULTI-DEVICE-CUDA-SIDECAR-V1"
AUDIT_SCHEMA = "RSH-FRENET-MULTI-DEVICE-CUDA-AUDIT-V1"
PROFILE_SCHEMA = "RSH-FRENET-MULTI-DEVICE-CUDA-CONFORMANCE-V1"
CSV_FIELDS = (
    "index", "p", "s", "x", "y", "z", "kappa", "tau",
    "tx", "ty", "tz", "nx", "ny", "nz", "bx", "by", "bz",
)
POSITION_FIELDS = ("x", "y", "z")
FRAME_FIELDS = ("tx", "ty", "tz", "nx", "ny", "nz", "bx", "by", "bz")
SCHEDULE_FIELDS = ("p", "s", "kappa", "tau")
PORTABLE_CLAIMS = {
    "actual_cuda_execution": False,
    "actual_multi_device_execution": False,
    "distributed_execution": False,
    "universal_speedup_claim": False,
    "geometry_receipt_authority": False,
}
GATE_REL_TOLERANCE = 1.0e-6
GATE_ABS_TOLERANCE = 1.0e-12
STABLE_FIELDS = (
    "schema", "contract", "source_parallel_contract",
    "source_shard_prefix_contract", "status", "actual_cuda_execution",
    "actual_multi_device_execution", "single_host_execution",
    "distributed_execution", "universal_speedup_claim",
    "geometry_receipt_authority", "raw_device_uuid_published",
    "assignment_policy", "local_prefix_policy", "shard_prefix_policy",
    "assembly_policy", "detected_device_count", "used_device_count",
    "samples", "intervals", "interval_width", "shard_count",
    "shard_prefix_passes", "final_shard_interval_count", "block_size",
    "stream_count_per_device", "reduction_transfer_bytes",
    "base_transfer_bytes", "inter_device_peer_bytes", "final_readback_bytes",
    "readback_point_count", "readback_float_components_per_point",
    "complete_path_readback", "compiled_architectures",
    "cuda_driver_api_version", "cuda_runtime_version", "cuda_compile_version",
    "max_frame_norm_error", "max_frame_orthogonality_error",
    "max_tail_vs_reduction_component_error", "centre_error", "frame_gate",
    "tail_gate", "centre_gate", "pass_finite", "pass_coverage",
    "pass_schedule_bounds", "pass_frame", "pass_centre",
    "pass_tail_integrity", "devices", "shards",
)


class ValidationError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError(f"{path} must contain a JSON object")
    return value


def exact_int(value: Any, label: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{label} must be an integer")
    return value


def finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValidationError(f"{label} must be finite")
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_profile(profile: dict[str, Any]) -> None:
    if profile.get("schema") != PROFILE_SCHEMA or profile.get("contract") != CONTRACT:
        raise ValidationError("profile schema or contract mismatch")

    configuration = profile.get("configuration")
    sharding = profile.get("sharding")
    topology = profile.get("topology")
    gates = profile.get("gates")
    claims = profile.get("portable_claims")
    if not all(
        isinstance(value, dict)
        for value in (configuration, sharding, topology, gates, claims)
    ):
        raise ValidationError("profile sections must be objects")

    samples = exact_int(configuration.get("samples"), "configuration.samples")
    width = exact_int(sharding.get("interval_width"), "sharding.interval_width")
    if samples < 3 or samples % 2 == 0 or width < 1:
        raise ValidationError("profile sample or shard bounds invalid")

    minimum = exact_int(
        topology.get("minimum_physical_device_count"),
        "topology.minimum_physical_device_count",
    )
    maximum = exact_int(
        topology.get("maximum_physical_device_count"),
        "topology.maximum_physical_device_count",
    )
    if minimum < 2 or maximum < minimum or maximum > 8:
        raise ValidationError("physical device bounds invalid")

    required_gates = (
        "max_position_vs_f64_shard_reference",
        "max_frame_vs_f64_shard_reference",
        "max_schedule_vs_f64",
        "max_frame_norm_error",
        "max_frame_orthogonality_error",
        "max_tail_vs_reduction_component_error",
        "centre_error",
    )
    for key in required_gates:
        if finite_number(gates.get(key), f"gates.{key}") <= 0.0:
            raise ValidationError(f"gate {key} must be positive")

    if set(claims) != set(PORTABLE_CLAIMS):
        raise ValidationError("portable_claims must contain the exact mandatory key set")
    for key, expected in PORTABLE_CLAIMS.items():
        value = claims.get(key)
        if type(value) is not bool or value is not expected:
            raise ValidationError(f"portable claim {key} must be literal false")


def parse_csv(path: Path, expected_samples: int) -> list[dict[str, float | int]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != CSV_FIELDS:
            raise ValidationError(f"{path} header mismatch")
        rows: list[dict[str, float | int]] = []
        for row_index, row in enumerate(reader):
            if row["index"] != str(row_index):
                raise ValidationError(f"{path} row {row_index} index is noncanonical")
            parsed: dict[str, float | int] = {"index": row_index}
            for field in CSV_FIELDS[1:]:
                token = row[field]
                if token is None or token == "" or token != token.strip():
                    raise ValidationError(
                        f"{path} row {row_index} {field} malformed"
                    )
                try:
                    numeric = float(token)
                except (TypeError, ValueError) as error:
                    raise ValidationError(
                        f"{path} row {row_index} {field} is not numeric"
                    ) from error
                parsed[field] = finite_number(
                    numeric, f"{path} row {row_index} {field}"
                )
            rows.append(parsed)
    if len(rows) != expected_samples:
        raise ValidationError(
            f"{path} has {len(rows)} rows, expected {expected_samples}"
        )
    return rows


def compare_rows(
    actual: list[dict[str, float | int]],
    expected: list[dict[str, float | int]],
    gates: dict[str, float],
) -> dict[str, float]:
    if len(actual) != len(expected):
        raise ValidationError("reference row counts differ")
    maxima = {"position": 0.0, "frame": 0.0, "schedule": 0.0}
    for index, (left, right) in enumerate(zip(actual, expected, strict=True)):
        if left["index"] != index or right["index"] != index:
            raise ValidationError("path ordering mismatch")
        for field in POSITION_FIELDS:
            maxima["position"] = max(
                maxima["position"], abs(float(left[field]) - float(right[field]))
            )
        for field in FRAME_FIELDS:
            maxima["frame"] = max(
                maxima["frame"], abs(float(left[field]) - float(right[field]))
            )
        for field in SCHEDULE_FIELDS:
            maxima["schedule"] = max(
                maxima["schedule"], abs(float(left[field]) - float(right[field]))
            )
    for key, gate_key in (
        ("position", "position_component_gate"),
        ("frame", "frame_component_gate"),
        ("schedule", "schedule_component_gate"),
    ):
        if maxima[key] > gates[gate_key]:
            raise ValidationError(
                f"{key} residual {maxima[key]} exceeds {gates[gate_key]}"
            )
    return maxima


def _require_exact(sidecar: dict[str, Any], key: str, expected: Any) -> None:
    actual = sidecar.get(key)
    if type(expected) is bool:
        if type(actual) is not bool or actual is not expected:
            raise ValidationError(f"{key}: {actual!r} != {expected!r}")
        return
    if type(expected) is int:
        if exact_int(actual, key) != expected:
            raise ValidationError(f"{key}: {actual!r} != {expected!r}")
        return
    if actual != expected:
        raise ValidationError(f"{key}: {actual!r} != {expected!r}")


def _require_gate(sidecar: dict[str, Any], field: str, expected: float) -> None:
    actual = finite_number(sidecar.get(field), field)
    if not math.isclose(
        actual,
        expected,
        rel_tol=GATE_REL_TOLERANCE,
        abs_tol=GATE_ABS_TOLERANCE,
    ):
        raise ValidationError(f"{field}: {actual!r} != profile gate {expected!r}")


def validate_sidecar(
    sidecar: dict[str, Any],
    profile: dict[str, Any],
    expected_run: int,
    selected_devices: list[int],
) -> None:
    if not isinstance(sidecar, dict):
        raise ValidationError("CUDA sidecar must be an object")
    configuration = profile["configuration"]
    sharding = profile["sharding"]
    topology = profile["topology"]
    gates = profile["gates"]
    required = {
        "schema": SCHEMA,
        "contract": CONTRACT,
        "source_parallel_contract": profile["source_parallel_contract"],
        "source_shard_prefix_contract": profile["source_shard_prefix_contract"],
        "status": "PASS",
        "actual_cuda_execution": True,
        "actual_multi_device_execution": True,
        "single_host_execution": True,
        "distributed_execution": False,
        "universal_speedup_claim": False,
        "geometry_receipt_authority": False,
        "raw_device_uuid_published": False,
        "assignment_policy": profile["assignment_policy"],
        "local_prefix_policy": profile["local_prefix_policy"],
        "shard_prefix_policy": profile["shard_prefix_policy"],
        "assembly_policy": profile["assembly_policy"],
        "samples": configuration["samples"],
        "intervals": sharding["expected_intervals"],
        "interval_width": sharding["interval_width"],
        "shard_count": sharding["expected_shard_count"],
        "shard_prefix_passes": sharding["expected_shard_prefix_passes"],
        "final_shard_interval_count": sharding["expected_final_shard_interval_count"],
        "stream_count_per_device": 1,
        "inter_device_peer_bytes": 0,
        "readback_point_count": configuration["samples"],
        "readback_float_components_per_point": 16,
        "complete_path_readback": True,
        "pass_finite": True,
        "pass_coverage": True,
        "pass_schedule_bounds": True,
        "pass_frame": True,
        "pass_centre": True,
        "pass_tail_integrity": True,
    }
    for key, expected in required.items():
        _require_exact(sidecar, key, expected)
    if exact_int(sidecar.get("repeat_run"), "repeat_run") != expected_run:
        raise ValidationError("repeat_run mismatch")

    used = exact_int(sidecar.get("used_device_count"), "used_device_count")
    if (
        used != len(selected_devices)
        or used < topology["minimum_physical_device_count"]
        or used > topology["maximum_physical_device_count"]
    ):
        raise ValidationError("used device count mismatch")
    if exact_int(sidecar.get("detected_device_count"), "detected_device_count") < used:
        raise ValidationError("detected device count is too small")
    if "device_uuid" in sidecar:
        raise ValidationError("raw device UUID field is forbidden")

    devices = sidecar.get("devices")
    if not isinstance(devices, list) or len(devices) != used:
        raise ValidationError("device metadata count mismatch")
    redacted: set[str] = set()
    for slot, device in enumerate(devices):
        if not isinstance(device, dict):
            raise ValidationError("device metadata must be an object")
        if (
            exact_int(device.get("logical_slot"), f"devices[{slot}].logical_slot") != slot
            or exact_int(device.get("cuda_index"), f"devices[{slot}].cuda_index")
            != selected_devices[slot]
            or exact_int(device.get("stream_ordinal"), f"devices[{slot}].stream_ordinal")
            != 0
        ):
            raise ValidationError("device slot/index/stream mismatch")
        token = device.get("redacted_device_id")
        if (
            not isinstance(token, str)
            or re.fullmatch(r"[0-9a-f]{16}", token) is None
            or token in redacted
        ):
            raise ValidationError("redacted device identifier invalid or duplicated")
        redacted.add(token)
        if "uuid" in device or "device_uuid" in device:
            raise ValidationError("raw device UUID leaked in device metadata")

    shards = sidecar.get("shards")
    if not isinstance(shards, list) or len(shards) != sharding["expected_shard_count"]:
        raise ValidationError("shard assignment count mismatch")
    expected_start = 0
    for index, shard in enumerate(shards):
        if not isinstance(shard, dict):
            raise ValidationError("shard assignment must be an object")
        count = exact_int(
            shard.get("interval_count"), f"shards[{index}].interval_count"
        )
        start = exact_int(
            shard.get("start_interval"), f"shards[{index}].start_interval"
        )
        end = exact_int(
            shard.get("end_interval_exclusive"),
            f"shards[{index}].end_interval_exclusive",
        )
        if (
            exact_int(shard.get("shard_index"), f"shards[{index}].shard_index")
            != index
            or start != expected_start
            or end != expected_start + count
        ):
            raise ValidationError("shard assignment is missing, overlapping, or unordered")
        expected_slot = index % used
        if (
            exact_int(shard.get("device_slot"), f"shards[{index}].device_slot")
            != expected_slot
            or exact_int(
                shard.get("cuda_device_index"),
                f"shards[{index}].cuda_device_index",
            )
            != selected_devices[expected_slot]
            or exact_int(
                shard.get("stream_ordinal"), f"shards[{index}].stream_ordinal"
            )
            != 0
        ):
            raise ValidationError("shard device/stream binding mismatch")
        expected_start += count
    if expected_start != sharding["expected_intervals"]:
        raise ValidationError("shards do not cover all intervals")

    if exact_int(
        sidecar.get("reduction_transfer_bytes"), "reduction_transfer_bytes"
    ) != len(shards) * 32:
        raise ValidationError("reduction transfer byte count mismatch")
    if exact_int(sidecar.get("base_transfer_bytes"), "base_transfer_bytes") != len(
        shards
    ) * 32:
        raise ValidationError("base transfer byte count mismatch")
    if exact_int(
        sidecar.get("final_readback_bytes"), "final_readback_bytes"
    ) != configuration["samples"] * 64:
        raise ValidationError("final readback byte count mismatch")

    _require_gate(sidecar, "frame_gate", finite_number(
        gates["max_frame_norm_error"], "gates.max_frame_norm_error"
    ))
    _require_gate(sidecar, "centre_gate", finite_number(
        gates["centre_error"], "gates.centre_error"
    ))
    _require_gate(sidecar, "tail_gate", finite_number(
        gates["max_tail_vs_reduction_component_error"],
        "gates.max_tail_vs_reduction_component_error",
    ))

    for field, gate_key in (
        ("max_frame_norm_error", "max_frame_norm_error"),
        ("max_frame_orthogonality_error", "max_frame_orthogonality_error"),
    ):
        if finite_number(sidecar.get(field), field) > gates[gate_key]:
            raise ValidationError(f"{field} exceeds its gate")
    if finite_number(sidecar.get("centre_error"), "centre_error") > gates[
        "centre_error"
    ]:
        raise ValidationError("centre_error exceeds its gate")
    if finite_number(
        sidecar.get("max_tail_vs_reduction_component_error"), "tail_error"
    ) > gates["max_tail_vs_reduction_component_error"]:
        raise ValidationError("tail integrity exceeds its gate")
    if sidecar.get("compiled_architectures") in (None, "", "unspecified"):
        raise ValidationError("compiled architecture missing")


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def write_text(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def run_reference(
    parallel_cli: Path, profile: dict[str, Any], output: Path
) -> tuple[Path, Path]:
    configuration = profile["configuration"]
    sharding = profile["sharding"]
    parallel_json = output / "parallel-report.json"
    parallel_csv = output / "parallel-path.csv"
    shard_json = output / "shard-report.json"
    shard_csv = output / "shard-path.csv"
    bundle = output / "shard-bundle.json"
    commands = [
        [
            str(parallel_cli), "run", "--samples", str(configuration["samples"]),
            "--json", str(parallel_json), "--csv", str(parallel_csv),
        ],
        [
            str(parallel_cli), "reconstruct", "--samples",
            str(configuration["samples"]), "--interval-width",
            str(sharding["interval_width"]), "--json", str(shard_json),
            "--csv", str(shard_csv), "--shards-json", str(bundle),
        ],
    ]
    for index, command in enumerate(commands):
        result = run(command)
        write_text(output / f"reference-{index}.stderr.txt", result.stderr)
        if result.returncode != 0:
            raise ValidationError(f"reference command failed: {command}")
    if (
        load_json(parallel_json).get("pass_all") is not True
        or load_json(shard_json).get("pass_all") is not True
    ):
        raise ValidationError("accepted references did not pass")
    return parallel_csv, shard_csv


def cuda_command(
    executable: Path,
    profile: dict[str, Any],
    devices: list[int],
    run_number: int,
    csv_path: Path,
) -> list[str]:
    configuration = profile["configuration"]
    sharding = profile["sharding"]
    gates = profile["gates"]
    return [
        str(executable),
        "--samples", str(configuration["samples"]),
        "--interval-width", str(sharding["interval_width"]),
        "--block-size", "128",
        "--devices", ",".join(map(str, devices)),
        "--repeat-run", str(run_number),
        "--frame-gate", str(gates["max_frame_norm_error"]),
        "--centre-gate", str(gates["centre_error"]),
        "--tail-gate", str(gates["max_tail_vs_reduction_component_error"]),
        "--output-csv", str(csv_path),
    ]


def run_sanitizer(
    tool: str,
    executable: Path,
    profile: dict[str, Any],
    devices: list[int],
    output: Path,
) -> dict[str, Any]:
    command_name = shutil.which("compute-sanitizer")
    if command_name is None:
        return {"tool": tool, "available": False, "status": "MISSING"}
    csv_path = output / f"sanitizer-{tool}-path.csv"
    command = [
        command_name,
        "--tool", tool,
        "--error-exitcode", "86",
        *cuda_command(executable, profile, devices, 0, csv_path),
    ]
    result = run(command)
    write_text(output / f"sanitizer-{tool}.stdout.txt", result.stdout)
    write_text(output / f"sanitizer-{tool}.stderr.txt", result.stderr)
    return {
        "tool": tool,
        "available": True,
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "exit_code": result.returncode,
    }


def write_manifest(output: Path) -> None:
    lines: list[str] = []
    files = sorted(
        (
            path
            for path in output.rglob("*")
            if path.is_file() and path.name != "SHA256SUMS.txt"
        ),
        key=lambda path: path.relative_to(output).as_posix(),
    )
    for path in files:
        lines.append(
            f"{sha256_file(path)}  {path.relative_to(output).as_posix()}\n"
        )
    write_text(output / "SHA256SUMS.txt", "".join(lines))


def build_rejection_audit(reason: str, source_commit: str | None) -> dict[str, Any]:
    return {
        "schema": AUDIT_SCHEMA,
        "contract": CONTRACT,
        "status": "REJECTED",
        "source_commit": source_commit,
        "actual_cuda_execution": False,
        "actual_multi_device_execution": False,
        "single_host_execution": False,
        "distributed_execution": False,
        "universal_speedup_claim": False,
        "geometry_receipt_authority": False,
        "raw_device_uuid_published": False,
        "complete_path_readback": False,
        "reason": reason,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cuda-executable", type=Path, required=True)
    parser.add_argument("--parallel-cli", type=Path, required=True)
    parser.add_argument(
        "--profile",
        type=Path,
        default=Path("conformance/frenet_multi_device_cuda_v1_4097.json"),
    )
    parser.add_argument("--devices", default="0,1")
    parser.add_argument("--source-commit")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--require-sanitizers", action="store_true")
    args = parser.parse_args()

    profile = load_json(args.profile)
    validate_profile(profile)
    if args.source_commit is not None and re.fullmatch(
        r"[0-9a-f]{40}", args.source_commit
    ) is None:
        raise SystemExit("--source-commit must be a full lowercase commit SHA")
    try:
        devices = [int(token) for token in args.devices.split(",") if token != ""]
    except ValueError as error:
        raise SystemExit("--devices must contain comma-separated integers") from error
    if (
        len(devices) != len(set(devices))
        or len(devices) < 2
        or len(devices) > 8
        or any(device < 0 for device in devices)
    ):
        raise SystemExit("--devices must contain between two and eight unique indices")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("output directory must be empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    try:
        parallel_csv, shard_csv = run_reference(
            args.parallel_cli, profile, args.output_dir
        )
        expected_samples = profile["configuration"]["samples"]
        parallel_rows = parse_csv(parallel_csv, expected_samples)
        shard_rows = parse_csv(shard_csv, expected_samples)
        repeat_runs = exact_int(
            profile["trusted_execution"]["repeat_runs"], "repeat_runs"
        )
        path_hashes: list[str] = []
        stable: dict[str, Any] | None = None
        runs: list[dict[str, Any]] = []
        maxima = {
            "parallel": {"position": 0.0, "frame": 0.0, "schedule": 0.0},
            "shard": {"position": 0.0, "frame": 0.0, "schedule": 0.0},
        }
        comparison_gates = {
            "position_component_gate": profile["gates"][
                "max_position_vs_f64_shard_reference"
            ],
            "frame_component_gate": profile["gates"][
                "max_frame_vs_f64_shard_reference"
            ],
            "schedule_component_gate": profile["gates"]["max_schedule_vs_f64"],
        }
        for run_number in range(repeat_runs):
            csv_path = args.output_dir / f"cuda-run-{run_number}.csv"
            result = run(
                cuda_command(
                    args.cuda_executable, profile, devices, run_number, csv_path
                )
            )
            write_text(
                args.output_dir / f"cuda-run-{run_number}.stdout.json",
                result.stdout,
            )
            write_text(
                args.output_dir / f"cuda-run-{run_number}.stderr.txt",
                result.stderr,
            )
            if not result.stdout.strip():
                raise ValidationError(f"CUDA run {run_number} produced no sidecar")
            try:
                sidecar = json.loads(result.stdout)
            except json.JSONDecodeError as error:
                raise ValidationError(
                    f"CUDA run {run_number} produced invalid JSON"
                ) from error
            validate_sidecar(sidecar, profile, run_number, devices)
            rows = parse_csv(csv_path, expected_samples)
            parallel_residuals = compare_rows(
                rows, parallel_rows, comparison_gates
            )
            shard_residuals = compare_rows(rows, shard_rows, comparison_gates)
            for key in maxima["parallel"]:
                maxima["parallel"][key] = max(
                    maxima["parallel"][key], parallel_residuals[key]
                )
                maxima["shard"][key] = max(
                    maxima["shard"][key], shard_residuals[key]
                )
            digest = sha256_file(csv_path)
            path_hashes.append(digest)
            record = {key: sidecar.get(key) for key in STABLE_FIELDS}
            if stable is None:
                stable = record
            elif record != stable:
                raise ValidationError(
                    "repeat sidecars differ outside timing/run fields"
                )
            if result.returncode != 0:
                raise ValidationError(
                    f"CUDA run {run_number} returned {result.returncode}"
                )
            runs.append(
                {
                    "repeat_run": run_number,
                    "path_sha256": digest,
                    "sidecar_status": sidecar["status"],
                    "end_to_end_milliseconds": finite_number(
                        sidecar.get("end_to_end_milliseconds"),
                        "end_to_end_milliseconds",
                    ),
                }
            )
        if len(set(path_hashes)) != 1:
            raise ValidationError("complete path readback is not repeatable")

        sanitizers = [
            run_sanitizer(
                tool, args.cuda_executable, profile, devices, args.output_dir
            )
            for tool in ("memcheck", "racecheck")
        ]
        if args.require_sanitizers and any(
            item["status"] != "PASS" for item in sanitizers
        ):
            raise ValidationError(
                "required Compute Sanitizer evidence did not pass"
            )
        audit = {
            "schema": AUDIT_SCHEMA,
            "contract": CONTRACT,
            "status": "PASS",
            "source_commit": args.source_commit,
            "actual_cuda_execution": True,
            "actual_multi_device_execution": True,
            "single_host_execution": True,
            "distributed_execution": False,
            "universal_speedup_claim": False,
            "geometry_receipt_authority": False,
            "raw_device_uuid_published": False,
            "used_device_indices": devices,
            "devices": stable["devices"] if stable else [],
            "repeat_runs": runs,
            "repeatable_path_sha256": path_hashes[0],
            "max_residuals": maxima,
            "sanitizers": sanitizers,
            "complete_path_readback": True,
        }
        write_text(
            args.output_dir / "audit.json",
            json.dumps(audit, indent=2, sort_keys=True) + "\n",
        )
        write_manifest(args.output_dir)
        print(json.dumps(audit, indent=2, sort_keys=True))
        return 0
    except Exception as error:
        rejection = build_rejection_audit(str(error), args.source_commit)
        write_text(
            args.output_dir / "rejection.json",
            json.dumps(rejection, indent=2, sort_keys=True) + "\n",
        )
        write_manifest(args.output_dir)
        print(json.dumps(rejection, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
