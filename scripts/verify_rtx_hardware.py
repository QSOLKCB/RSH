#!/usr/bin/env python3
"""Validate CUDA and WebGPU evidence from the trusted RTX workflow.

The aggregate report deliberately excludes stable device UUIDs. Raw per-adapter
files remain workflow artifacts and are never committed as canonical evidence.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
from typing import Any

EXIT_ARGUMENT = 2
EXIT_EVIDENCE = 31
SOFTWARE_ADAPTER_MARKERS = ("swiftshader", "llvmpipe", "lavapipe", "software")
PARALLEL_RESIDUAL_GATES = (
    ("max_position_component_vs_parallel_wasm_f64", "position"),
    ("max_frame_component_vs_parallel_wasm_f64", "frame"),
    ("max_schedule_component_vs_parallel_wasm_f64", "schedule"),
    ("max_frame_norm_error", "frameNorm"),
    ("max_frame_orthogonality_error", "frameOrthogonality"),
)


def load_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def finite(value: Any, name: str, errors: list[str]) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{name} is missing or invalid")
        return None
    numeric = float(value)
    if not math.isfinite(numeric):
        errors.append(f"{name} is not finite")
        return None
    return numeric


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def physical_adapter(value: Any, name: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{name} is missing")
        return None
    adapter = value.strip()
    lowered = adapter.lower()
    require("nvidia" in lowered, f"{name} is not an NVIDIA adapter", errors)
    require(
        not any(marker in lowered for marker in SOFTWARE_ADAPTER_MARKERS),
        f"{name} identifies a software adapter",
        errors,
    )
    return adapter


def validate_cuda(summary: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    require(
        summary.get("schema") == "RSH-CUDA-HARDWARE-TEST-RESULT-V1",
        "CUDA summary schema mismatch",
        errors,
    )
    require(summary.get("status") == "PASS", "CUDA summary did not report PASS", errors)
    require(
        summary.get("runs_completed") == 3,
        "CUDA workflow requires exactly three completed runs",
        errors,
    )
    require(summary.get("repeatable") is True, "CUDA repeatability did not pass", errors)

    sidecar = summary.get("sidecar")
    if not isinstance(sidecar, dict):
        errors.append("CUDA summary.sidecar is missing")
        sidecar = {}
    require(
        sidecar.get("actual_cuda_execution") is True,
        "CUDA actual execution was not recorded",
        errors,
    )
    require(
        sidecar.get("geometry_receipt_authority") is False,
        "CUDA claimed geometry authority",
        errors,
    )
    device = physical_adapter(sidecar.get("device"), "CUDA device", errors)
    compute_capability = sidecar.get("compute_capability")
    require(
        isinstance(compute_capability, str)
        and re.fullmatch(r"\d+\.\d+", compute_capability) is not None,
        "CUDA compute capability is invalid",
        errors,
    )
    architecture = sidecar.get("compiled_architectures")
    require(
        isinstance(architecture, str) and architecture.strip() not in ("", "unspecified"),
        "CUDA compiled architecture is missing",
        errors,
    )
    maximum = finite(sidecar.get("maximum_residual"), "CUDA maximum residual", errors)
    threshold = finite(sidecar.get("threshold"), "CUDA residual threshold", errors)
    if maximum is not None and threshold is not None:
        require(maximum <= threshold, "CUDA residual exceeds its gate", errors)

    sanitizers = summary.get("sanitizers")
    if not isinstance(sanitizers, list):
        errors.append("CUDA sanitizer evidence is missing")
        sanitizers = []
    by_tool = {
        result.get("tool"): result
        for result in sanitizers
        if isinstance(result, dict) and isinstance(result.get("tool"), str)
    }
    for tool in ("memcheck", "racecheck"):
        result = by_tool.get(tool)
        require(isinstance(result, dict), f"CUDA {tool} result is missing", errors)
        if isinstance(result, dict):
            require(result.get("available") is True, f"CUDA {tool} was unavailable", errors)
            require(result.get("status") == "PASS", f"CUDA {tool} did not pass", errors)

    redacted = {
        "status": summary.get("status"),
        "device": device,
        "compute_capability": compute_capability,
        "compiled_architectures": architecture,
        "runs_completed": summary.get("runs_completed"),
        "repeatable": summary.get("repeatable"),
        "maximum_residual": maximum,
        "threshold": threshold,
        "sanitizers": [
            {
                "tool": tool,
                "available": by_tool.get(tool, {}).get("available"),
                "status": by_tool.get(tool, {}).get("status"),
            }
            for tool in ("memcheck", "racecheck")
        ],
        "actual_cuda_execution": sidecar.get("actual_cuda_execution") is True,
        "geometry_receipt_authority": False,
    }
    return errors, redacted


def validate_schedule(evidence: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    require(
        evidence.get("schema") == "RSH-TRUSTED-RTX-WEBGPU-SCHEDULE-V1",
        "schedule schema mismatch",
        errors,
    )
    require(evidence.get("status") == "PASS", "schedule WebGPU did not report PASS", errors)
    require(
        evidence.get("actual_gpu_execution") is True,
        "schedule actual GPU execution was not recorded",
        errors,
    )
    require(
        evidence.get("complete_field_readback") is True,
        "schedule complete readback was not recorded",
        errors,
    )
    require(evidence.get("speedup_claim") is False, "schedule emitted a speedup claim", errors)
    require(
        evidence.get("universal_speedup_claim") is False,
        "schedule emitted a universal speedup claim",
        errors,
    )
    require(
        evidence.get("geometry_receipt_authority") is False,
        "schedule claimed geometry authority",
        errors,
    )
    adapter = physical_adapter(evidence.get("adapter"), "schedule adapter", errors)
    maximum = finite(evidence.get("maximum_residual"), "schedule maximum residual", errors)
    threshold = finite(evidence.get("threshold"), "schedule threshold", errors)
    if maximum is not None and threshold is not None:
        require(maximum <= threshold, "schedule residual exceeds its gate", errors)
    return errors, {
        "status": evidence.get("status"),
        "adapter": adapter,
        "maximum_residual": maximum,
        "threshold": threshold,
        "actual_gpu_execution": evidence.get("actual_gpu_execution") is True,
        "complete_field_readback": evidence.get("complete_field_readback") is True,
        "speedup_claim": False,
        "universal_speedup_claim": False,
        "geometry_receipt_authority": False,
    }


def validate_parallel(evidence: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    require(
        evidence.get("schema") == "RSH-WEBGPU-FRENET-PARALLEL-BENCHMARK-V1",
        "parallel schema mismatch",
        errors,
    )
    require(evidence.get("status") == "PASS", "parallel WebGPU did not report PASS", errors)
    for field, expected in (
        ("actual_gpu_execution", True),
        ("parallel_scan_execution", True),
        ("complete_path_readback", True),
        ("actual_multi_device_execution", False),
        ("distributed_execution", False),
        ("universal_speedup_claim", False),
        ("geometry_receipt_authority", False),
    ):
        require(evidence.get(field) is expected, f"parallel {field} must be {expected}", errors)
    configuration = evidence.get("configuration")
    metadata = evidence.get("metadata")
    benchmark = evidence.get("benchmark")
    residuals = evidence.get("residuals")
    gates = evidence.get("gates")
    for name, value in (
        ("configuration", configuration),
        ("metadata", metadata),
        ("benchmark", benchmark),
        ("residuals", residuals),
        ("gates", gates),
    ):
        require(isinstance(value, dict), f"parallel {name} is missing", errors)
    configuration = configuration if isinstance(configuration, dict) else {}
    metadata = metadata if isinstance(metadata, dict) else {}
    benchmark = benchmark if isinstance(benchmark, dict) else {}
    residuals = residuals if isinstance(residuals, dict) else {}
    gates = gates if isinstance(gates, dict) else {}
    require(configuration.get("samples") == 4097, "parallel samples must be 4097", errors)
    require(metadata.get("scan_passes") == 13, "parallel scan passes must be 13", errors)
    require(metadata.get("transform_bytes") == 32, "parallel transform size must be 32 bytes", errors)
    require(benchmark.get("warmup_runs") == 2, "parallel warm-up count must be 2", errors)
    require(benchmark.get("measured_runs") == 7, "parallel measured count must be 7", errors)
    adapter = physical_adapter(metadata.get("adapter"), "parallel adapter", errors)

    redacted_residuals: dict[str, float | None] = {}
    for residual_name, gate_name in PARALLEL_RESIDUAL_GATES:
        residual = finite(residuals.get(residual_name), f"parallel {residual_name}", errors)
        gate = finite(gates.get(gate_name), f"parallel {gate_name}", errors)
        if residual is not None and gate is not None:
            require(
                residual <= gate,
                f"parallel {residual_name} exceeds {gate_name}",
                errors,
            )
        redacted_residuals[residual_name] = residual

    observed_speedup = finite(
        benchmark.get("observed_speedup"),
        "parallel observed speedup",
        errors,
    )
    speedup_claim = evidence.get("speedup_claim") is True
    if speedup_claim and observed_speedup is not None:
        require(observed_speedup > 1.0, "parallel speedup claim lacks an observed speedup", errors)

    return errors, {
        "status": evidence.get("status"),
        "adapter": adapter,
        "samples": configuration.get("samples"),
        "scan_passes": metadata.get("scan_passes"),
        "transform_bytes": metadata.get("transform_bytes"),
        "residuals": redacted_residuals,
        "observed_speedup": observed_speedup,
        "speedup_claim": speedup_claim,
        "speedup_claim_scope": evidence.get("speedup_claim_scope"),
        "actual_gpu_execution": True,
        "complete_path_readback": True,
        "actual_multi_device_execution": False,
        "distributed_execution": False,
        "universal_speedup_claim": False,
        "geometry_receipt_authority": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--cuda-summary", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--parallel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workflow-run", default="unknown")
    parser.add_argument("--actor", default="unknown")
    parser.add_argument("--runner", default="unknown")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if re.fullmatch(r"[0-9a-f]{40}", args.commit) is None:
        print("--commit must be a full lowercase SHA-1", flush=True)
        return EXIT_ARGUMENT
    try:
        cuda = load_object(args.cuda_summary)
        schedule = load_object(args.schedule)
        parallel = load_object(args.parallel)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"invalid evidence input: {error}", flush=True)
        return EXIT_ARGUMENT

    cuda_errors, cuda_redacted = validate_cuda(cuda)
    schedule_errors, schedule_redacted = validate_schedule(schedule)
    parallel_errors, parallel_redacted = validate_parallel(parallel)
    errors = {
        "cuda": cuda_errors,
        "schedule_webgpu": schedule_errors,
        "parallel_webgpu": parallel_errors,
    }
    pass_all = not any(errors.values())
    report = {
        "schema": "RSH-TRUSTED-RTX-HARDWARE-AUDIT-V1",
        "status": "PASS" if pass_all else "FAIL",
        "tested_commit": args.commit,
        "workflow_run": args.workflow_run,
        "dispatch_actor": args.actor,
        "runner_name": args.runner,
        "trust_policy": "manual-main-ancestor-environment-protected-self-hosted-v1",
        "cuda": cuda_redacted,
        "schedule_webgpu": schedule_redacted,
        "parallel_webgpu": parallel_redacted,
        "errors": errors,
        "actual_rtx_hardware_execution": pass_all,
        "actual_multi_device_execution": False,
        "distributed_execution": False,
        "universal_speedup_claim": False,
        "geometry_receipt_authority": False,
        "privacy_note": "Stable device UUIDs and local host paths are excluded from this aggregate report. Raw evidence remains an access-controlled workflow artifact.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if pass_all else EXIT_EVIDENCE


if __name__ == "__main__":
    raise SystemExit(main())
