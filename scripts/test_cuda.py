#!/usr/bin/env python3
"""Execute, validate, repeat, and optionally sanitize the RSH CUDA adapter."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

EXIT_ARGUMENT = 2
EXIT_UNAVAILABLE = 20
EXIT_MALFORMED = 30
EXIT_RESIDUAL = 31
EXIT_REPEATABILITY = 32
EXIT_SANITIZER = 40

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
    "cuda_runtime_version",
    "cuda_compile_version",
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def command_for(executable: Path, profile: dict[str, Any], run_number: int) -> list[str]:
    configuration = profile["configuration"]
    return [
        str(executable),
        "--samples",
        str(configuration["samples"]),
        "--block-size",
        str(profile["block_size"]),
        "--threshold",
        str(profile["residual_threshold"]),
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


def validate_sidecar(sidecar: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_samples = int(profile["configuration"]["samples"])
    expected_block = int(profile["block_size"])
    expected_threshold = float(profile["residual_threshold"])

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    require(sidecar.get("schema") == "RSH-CUDA-RESIDUAL-SIDECAR-V1", "schema mismatch")
    require(sidecar.get("status") == "PASS", "CUDA sidecar did not report PASS")
    require(sidecar.get("actual_cuda_execution") is True, "actual CUDA execution was not recorded")
    require(sidecar.get("geometry_receipt_authority") is False, "CUDA claimed geometry receipt authority")
    require(int(sidecar.get("samples", -1)) == expected_samples, "sample count mismatch")
    require(int(sidecar.get("block_size", -1)) == expected_block, "block size mismatch")
    require(
        math.isclose(
            float(sidecar.get("threshold", math.nan)),
            expected_threshold,
            rel_tol=0.0,
            abs_tol=0.0,
        ),
        "threshold mismatch",
    )
    require(bool(str(sidecar.get("device", "")).strip()), "device name missing")
    require(bool(str(sidecar.get("compute_capability", "")).strip()), "compute capability missing")

    for field in (
        "max_abs_kappa_vs_rust_f64",
        "max_abs_tau_vs_rust_f64",
        "maximum_residual",
    ):
        try:
            require(math.isfinite(float(sidecar[field])), f"{field} is not finite")
        except (KeyError, TypeError, ValueError):
            errors.append(f"{field} is missing or invalid")

    try:
        require(
            float(sidecar["maximum_residual"]) <= expected_threshold,
            "maximum residual exceeds the published gate",
        )
    except (KeyError, TypeError, ValueError):
        pass
    return errors


def repeatability_record(sidecar: dict[str, Any]) -> dict[str, Any]:
    return {field: sidecar.get(field) for field in REPEATABILITY_FIELDS}


def run_cpu_reference(executable: Path, profile: dict[str, Any], output: Path) -> dict[str, Any]:
    command = [
        str(executable),
        "cuda-reference",
        "--samples",
        str(profile["configuration"]["samples"]),
        "--threshold",
        str(profile["residual_threshold"]),
    ]
    result = run_command(command)
    output.write_text(result.stdout, encoding="utf-8", newline="\n")
    (output.parent / "cpu-reference.stderr.txt").write_text(
        result.stderr, encoding="utf-8", newline="\n"
    )
    if result.returncode != 0:
        raise RuntimeError(f"CPU f32 reference failed with exit {result.returncode}")
    payload = json.loads(result.stdout)
    if payload.get("actual_cuda_execution") is not False or payload.get("status") != "PASS":
        raise RuntimeError("CPU f32 reference returned an invalid authority/status boundary")
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
    if args.runs < 1:
        print("--runs must be at least 1", file=sys.stderr)
        return EXIT_ARGUMENT
    executable = args.executable.resolve()
    if not executable.is_file():
        print(f"CUDA executable not found: {executable}", file=sys.stderr)
        return EXIT_UNAVAILABLE

    try:
        profile = load_json(args.profile)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"invalid profile: {error}", file=sys.stderr)
        return EXIT_ARGUMENT

    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
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
        except (OSError, RuntimeError, json.JSONDecodeError) as error:
            summary.update(status="FAIL", failure="cpu-reference", detail=str(error))
            write_summary(output_dir, summary)
            return EXIT_MALFORMED

    sidecars: list[dict[str, Any]] = []
    for run_number in range(1, args.runs + 1):
        result = run_command(command_for(executable, profile, run_number))
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
            sidecar = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            summary.update(
                status="FAIL",
                failure="malformed-sidecar",
                run=run_number,
                detail=str(error),
            )
            write_summary(output_dir, summary)
            return EXIT_MALFORMED
        errors = validate_sidecar(sidecar, profile)
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
