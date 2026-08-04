#!/usr/bin/env python3
"""Execute, validate, repeat, and optionally sanitize the RSH CUDA adapter."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any
from uuid import UUID

EXIT_ARGUMENT = 2
EXIT_UNAVAILABLE = 20
EXIT_MALFORMED = 30
EXIT_RESIDUAL = 31
EXIT_REPEATABILITY = 32
EXIT_SANITIZER = 40

MAX_RUNS = 20
FLOAT_REL_TOLERANCE = 1.0e-12
FLOAT_ABS_TOLERANCE = 1.0e-15
SEALED_CONFIGURATION = {
    "s0": 0.0,
    "s1": 4.0,
    "kappa_fraction": 0.85,
    "tau_floor": 0.22,
    "tau_amplitude": 0.13,
}

REPEATABILITY_FIELDS = (
    "schema",
    "status",
    "diagnostic_status",
    "actual_cuda_execution",
    "device_index",
    "device",
    "device_uuid",
    "compute_capability",
    "compiled_architectures",
    "cuda_driver_api_version",
    "cuda_driver_api",
    "cuda_runtime_version",
    "cuda_runtime",
    "cuda_compile_version",
    "cuda_compile",
    "host_pointer_width",
    "samples",
    "block_size",
    "grid_blocks",
    "max_abs_kappa_vs_rust_f64",
    "max_abs_tau_vs_rust_f64",
    "maximum_residual",
    "diagnostic_observation_band",
    "threshold",
    "geometry_receipt_authority",
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def floats_close(left: float, right: float) -> bool:
    return math.isclose(
        left,
        right,
        rel_tol=FLOAT_REL_TOLERANCE,
        abs_tol=FLOAT_ABS_TOLERANCE,
    )


def profile_parameters(profile: dict[str, Any]) -> tuple[int, int, float]:
    if profile.get("schema") != "RSH-CUDA-SCHEDULE-CONFORMANCE-V1":
        raise ValueError("unexpected CUDA profile schema")
    if profile.get("precision") != "f32":
        raise ValueError("CUDA profile precision must be f32")

    configuration = profile.get("configuration")
    if not isinstance(configuration, dict):
        raise ValueError("profile.configuration must be an object")

    samples_value = configuration.get("samples")
    block_value = profile.get("block_size")
    threshold_value = profile.get("residual_threshold")
    if type(samples_value) is not int:
        raise ValueError("profile samples must be an integer")
    if type(block_value) is not int:
        raise ValueError("profile block size must be an integer")
    if isinstance(threshold_value, bool) or not isinstance(threshold_value, (int, float)):
        raise ValueError("profile residual threshold must be numeric")

    samples = samples_value
    block_size = block_value
    threshold = float(threshold_value)
    if samples < 2:
        raise ValueError("profile samples must be at least 2")
    if block_size < 1 or block_size > 1024:
        raise ValueError("profile block size must be in [1, 1024]")
    if not math.isfinite(threshold) or threshold <= 0.0:
        raise ValueError("profile residual threshold must be finite and positive")

    for field, expected in SEALED_CONFIGURATION.items():
        value = configuration.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"profile configuration field {field} must be numeric")
        numeric = float(value)
        if not math.isfinite(numeric) or not floats_close(numeric, expected):
            raise ValueError(
                f"profile configuration field {field} must retain the sealed value {expected}"
            )

    return samples, block_size, threshold


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def command_for(executable: Path, profile: dict[str, Any], run_number: int) -> list[str]:
    samples, block_size, threshold = profile_parameters(profile)
    return [
        str(executable),
        "--samples",
        str(samples),
        "--block-size",
        str(block_size),
        "--threshold",
        str(threshold),
        "--repeat-run",
        str(run_number),
    ]


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def unavailable_message(stderr: str) -> bool:
    lowered = stderr.lower()
    markers = (
        "no cuda-capable device",
        "cuda driver version is insufficient",
        "cuda initialization error",
        "cudaerrornodevice",
        "driver/library version mismatch",
        "cannot open shared object file",
    )
    return any(marker in lowered for marker in markers)


def parse_int_field(sidecar: dict[str, Any], field: str, errors: list[str]) -> int | None:
    value = sidecar.get(field)
    if type(value) is not int:
        errors.append(f"{field} is missing or invalid")
        return None
    return value


def parse_float_field(sidecar: dict[str, Any], field: str, errors: list[str]) -> float | None:
    value = sidecar.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{field} is missing or invalid")
        return None
    numeric = float(value)
    if not math.isfinite(numeric):
        errors.append(f"{field} is not finite")
        return None
    return numeric


def parse_string_field(
    sidecar: dict[str, Any], field: str, errors: list[str]
) -> str | None:
    value = sidecar.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} is missing or invalid")
        return None
    return value


def validate_sidecar(
    sidecar: dict[str, Any],
    profile: dict[str, Any],
    expected_run: int | None = None,
) -> list[str]:
    errors: list[str] = []
    try:
        expected_samples, expected_block, expected_threshold = profile_parameters(profile)
    except ValueError as error:
        return [f"invalid profile: {error}"]

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    require(
        sidecar.get("schema") == "RSH-CUDA-RESIDUAL-SIDECAR-V1",
        "schema mismatch",
    )
    require(sidecar.get("status") == "PASS", "CUDA sidecar did not report PASS")
    require(
        sidecar.get("actual_cuda_execution") is True,
        "actual CUDA execution was not recorded",
    )
    require(
        sidecar.get("geometry_receipt_authority") is False,
        "CUDA claimed geometry receipt authority",
    )

    diagnostic_status = parse_string_field(sidecar, "diagnostic_status", errors)
    device_index = parse_int_field(sidecar, "device_index", errors)
    parse_string_field(sidecar, "device", errors)
    device_uuid = parse_string_field(sidecar, "device_uuid", errors)
    compute_capability = parse_string_field(sidecar, "compute_capability", errors)
    compiled_architectures = parse_string_field(
        sidecar, "compiled_architectures", errors
    )
    driver_version = parse_int_field(sidecar, "cuda_driver_api_version", errors)
    runtime_version = parse_int_field(sidecar, "cuda_runtime_version", errors)
    compile_version = parse_int_field(sidecar, "cuda_compile_version", errors)
    parse_string_field(sidecar, "cuda_driver_api", errors)
    parse_string_field(sidecar, "cuda_runtime", errors)
    parse_string_field(sidecar, "cuda_compile", errors)
    pointer_width = parse_int_field(sidecar, "host_pointer_width", errors)
    repeat_run = parse_int_field(sidecar, "repeat_run", errors)
    samples = parse_int_field(sidecar, "samples", errors)
    block_size = parse_int_field(sidecar, "block_size", errors)
    grid_blocks = parse_int_field(sidecar, "grid_blocks", errors)

    kappa = parse_float_field(sidecar, "max_abs_kappa_vs_rust_f64", errors)
    tau = parse_float_field(sidecar, "max_abs_tau_vs_rust_f64", errors)
    maximum = parse_float_field(sidecar, "maximum_residual", errors)
    diagnostic_band = parse_float_field(
        sidecar, "diagnostic_observation_band", errors
    )
    threshold = parse_float_field(sidecar, "threshold", errors)

    if device_index is not None:
        require(device_index >= 0, "device_index must be non-negative")
    if device_uuid is not None:
        try:
            UUID(device_uuid)
        except ValueError:
            errors.append("device_uuid is not a canonical UUID")
    if compute_capability is not None:
        require(
            re.fullmatch(r"\d+\.\d+", compute_capability) is not None,
            "compute_capability must use major.minor form",
        )
    if compiled_architectures is not None:
        require(
            compiled_architectures != "unspecified",
            "compiled_architectures must identify the configured target",
        )
    for field, value in (
        ("cuda_driver_api_version", driver_version),
        ("cuda_runtime_version", runtime_version),
        ("cuda_compile_version", compile_version),
    ):
        if value is not None:
            require(value > 0, f"{field} must be positive")
    if pointer_width is not None:
        require(pointer_width in (32, 64), "host_pointer_width must be 32 or 64")
    if repeat_run is not None:
        require(repeat_run >= 0, "repeat_run must be non-negative")
        if expected_run is not None:
            require(repeat_run == expected_run, "repeat_run does not match the requested run")
    if samples is not None:
        require(samples == expected_samples, "sample count mismatch")
    if block_size is not None:
        require(block_size == expected_block, "block size mismatch")
    if samples is not None and block_size is not None and grid_blocks is not None:
        expected_grid = (samples + block_size - 1) // block_size
        require(grid_blocks == expected_grid, "grid block count mismatch")
    if grid_blocks is not None:
        require(grid_blocks > 0, "grid_blocks must be positive")

    if threshold is not None:
        require(
            floats_close(threshold, expected_threshold),
            "threshold mismatch",
        )
    if diagnostic_band is not None:
        require(
            diagnostic_band > 0.0,
            "diagnostic observation band must be positive",
        )

    for field, residual in (
        ("max_abs_kappa_vs_rust_f64", kappa),
        ("max_abs_tau_vs_rust_f64", tau),
        ("maximum_residual", maximum),
    ):
        if residual is not None:
            require(
                residual <= expected_threshold,
                f"{field} exceeds the published gate",
            )

    if kappa is not None and tau is not None and maximum is not None:
        require(
            floats_close(maximum, max(kappa, tau)),
            "maximum_residual does not equal the maximum component residual",
        )
    if maximum is not None and diagnostic_band is not None and diagnostic_status is not None:
        expected_diagnostic = (
            "NOMINAL" if maximum <= diagnostic_band else "PASS_WITH_WARNING"
        )
        require(
            diagnostic_status == expected_diagnostic,
            "diagnostic_status is inconsistent with the residual band",
        )

    return errors


def repeatability_record(sidecar: dict[str, Any]) -> dict[str, Any]:
    return {field: sidecar.get(field) for field in REPEATABILITY_FIELDS}


def run_cpu_reference(executable: Path, profile: dict[str, Any], output: Path) -> dict[str, Any]:
    samples, _, threshold = profile_parameters(profile)
    command = [
        str(executable),
        "cuda-reference",
        "--samples",
        str(samples),
        "--threshold",
        str(threshold),
    ]
    result = run_command(command)
    output.write_text(result.stdout, encoding="utf-8", newline="\n")
    (output.parent / "cpu-reference.stderr.txt").write_text(
        result.stderr, encoding="utf-8", newline="\n"
    )
    if result.returncode != 0:
        raise RuntimeError(f"CPU f32 reference failed with exit {result.returncode}")
    payload = json.loads(result.stdout)
    if not isinstance(payload, dict):
        raise RuntimeError("CPU f32 reference did not return a JSON object")
    if payload.get("actual_cuda_execution") is not False or payload.get("status") != "PASS":
        raise RuntimeError("CPU f32 reference returned an invalid authority/status boundary")
    residual = parse_float_field(payload, "maximum_residual", [])
    if residual is None or residual > threshold:
        raise RuntimeError("CPU f32 reference exceeded the published residual gate")
    return payload


def run_sanitizer(
    tool: str,
    executable: Path,
    profile: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    sanitizer = shutil.which("compute-sanitizer")
    if sanitizer is None:
        return {"tool": tool, "available": False, "status": "SKIPPED"}
    error_code = "86" if tool == "memcheck" else "87"
    command = [
        sanitizer,
        "--tool",
        tool,
        "--error-exitcode",
        error_code,
        *command_for(executable, profile, 0),
    ]
    result = run_command(command)
    (output_dir / f"compute-sanitizer-{tool}.stdout.txt").write_text(
        result.stdout, encoding="utf-8", newline="\n"
    )
    (output_dir / f"compute-sanitizer-{tool}.stderr.txt").write_text(
        result.stderr, encoding="utf-8", newline="\n"
    )
    return {
        "tool": tool,
        "available": True,
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "exit_code": result.returncode,
    }


def write_manifest(output_dir: Path) -> None:
    files = sorted(
        (
            path
            for path in output_dir.rglob("*")
            if path.is_file() and path.name != "SHA256SUMS.txt"
        ),
        key=lambda path: path.relative_to(output_dir).as_posix(),
    )
    lines = [
        f"{sha256_file(path)}  {path.relative_to(output_dir).as_posix()}\n"
        for path in files
    ]
    (output_dir / "SHA256SUMS.txt").write_text(
        "".join(lines), encoding="utf-8", newline="\n"
    )


def prepare_output_directory(output_dir: Path) -> None:
    if output_dir.exists():
        if not output_dir.is_dir():
            raise ValueError(f"output path is not a directory: {output_dir}")
        if any(output_dir.iterdir()):
            raise ValueError(
                f"output directory must be empty to avoid mixing evidence: {output_dir}"
            )
        return
    output_dir.mkdir(parents=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--cpu-reference", type=Path)
    parser.add_argument(
        "--sanitizers", choices=("auto", "off", "required"), default="auto"
    )
    return parser.parse_args()


def write_summary(output_dir: Path, summary: dict[str, Any]) -> None:
    (output_dir / "audit-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_manifest(output_dir)


def main() -> int:
    args = parse_args()
    if args.runs < 1 or args.runs > MAX_RUNS:
        print(f"--runs must be in [1, {MAX_RUNS}]", file=sys.stderr)
        return EXIT_ARGUMENT
    executable = args.executable.resolve()
    if not executable.is_file():
        print(f"CUDA executable not found: {executable}", file=sys.stderr)
        return EXIT_UNAVAILABLE

    try:
        profile = load_json(args.profile)
        profile_parameters(profile)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"invalid profile: {error}", file=sys.stderr)
        return EXIT_ARGUMENT

    output_dir = args.output.resolve()
    try:
        prepare_output_directory(output_dir)
    except (OSError, ValueError) as error:
        print(f"invalid output directory: {error}", file=sys.stderr)
        return EXIT_ARGUMENT

    summary: dict[str, Any] = {
        "schema": "RSH-CUDA-HARDWARE-TEST-RESULT-V1",
        "status": "RUNNING",
        "profile": str(args.profile),
        "runs_requested": args.runs,
    }

    cpu_reference: dict[str, Any] | None = None
    if args.cpu_reference is not None:
        try:
            cpu_reference = run_cpu_reference(
                args.cpu_reference.resolve(), profile, output_dir / "cpu-reference.json"
            )
        except (OSError, RuntimeError, json.JSONDecodeError, ValueError) as error:
            summary.update(status="FAIL", failure="cpu-reference", detail=str(error))
            write_summary(output_dir, summary)
            return EXIT_MALFORMED

    sidecars: list[dict[str, Any]] = []
    for run_number in range(1, args.runs + 1):
        try:
            result = run_command(command_for(executable, profile, run_number))
        except OSError as error:
            summary.update(
                status="BLOCKED BY ENVIRONMENT",
                failure="cuda-execution",
                run=run_number,
                detail=str(error),
            )
            write_summary(output_dir, summary)
            return EXIT_UNAVAILABLE
        (output_dir / f"run-{run_number}.stdout.json").write_text(
            result.stdout, encoding="utf-8", newline="\n"
        )
        (output_dir / f"run-{run_number}.stderr.txt").write_text(
            result.stderr, encoding="utf-8", newline="\n"
        )
        if result.returncode != 0:
            blocked = unavailable_message(result.stderr)
            summary.update(
                status="BLOCKED BY ENVIRONMENT" if blocked else "FAIL",
                failure="cuda-execution",
                run=run_number,
                exit_code=result.returncode,
            )
            write_summary(output_dir, summary)
            return EXIT_UNAVAILABLE if blocked else EXIT_RESIDUAL
        try:
            decoded = json.loads(result.stdout)
            if not isinstance(decoded, dict):
                raise ValueError("sidecar is not a JSON object")
            sidecar = decoded
        except (json.JSONDecodeError, ValueError) as error:
            summary.update(
                status="FAIL",
                failure="malformed-sidecar",
                run=run_number,
                detail=str(error),
            )
            write_summary(output_dir, summary)
            return EXIT_MALFORMED
        errors = validate_sidecar(sidecar, profile, expected_run=run_number)
        if errors:
            summary.update(
                status="FAIL",
                failure="sidecar-validation",
                run=run_number,
                errors=errors,
            )
            write_summary(output_dir, summary)
            return EXIT_RESIDUAL
        sidecars.append(sidecar)

    records = [repeatability_record(sidecar) for sidecar in sidecars]
    repeatable = all(record == records[0] for record in records[1:])
    if not repeatable:
        summary.update(status="FAIL", failure="repeatability", records=records)
        write_summary(output_dir, summary)
        return EXIT_REPEATABILITY

    sanitizer_results: list[dict[str, Any]] = []
    if args.sanitizers != "off":
        sanitizer_results = [
            run_sanitizer("memcheck", executable, profile, output_dir),
            run_sanitizer("racecheck", executable, profile, output_dir),
        ]
        sanitizer_available = any(result["available"] for result in sanitizer_results)
        if args.sanitizers == "required" and not sanitizer_available:
            summary.update(status="FAIL", failure="sanitizer-unavailable")
            write_summary(output_dir, summary)
            return EXIT_SANITIZER
        if any(result.get("status") == "FAIL" for result in sanitizer_results):
            summary.update(
                status="FAIL", failure="sanitizer", sanitizers=sanitizer_results
            )
            write_summary(output_dir, summary)
            return EXIT_SANITIZER

    summary.update(
        status="PASS",
        runs_completed=len(sidecars),
        repeatable=True,
        sidecar=sidecars[0],
        maximum_residuals=[sidecar["maximum_residual"] for sidecar in sidecars],
        cpu_reference=cpu_reference,
        sanitizers=sanitizer_results,
    )
    write_summary(output_dir, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
