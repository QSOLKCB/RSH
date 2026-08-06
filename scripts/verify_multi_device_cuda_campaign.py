#!/usr/bin/env python3
"""Validate the checked-in physical multi-device CUDA campaign record."""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from pathlib import Path
from typing import Any

SCHEMA = "RSH-FRENET-MULTI-DEVICE-CUDA-CAMPAIGN-V1"
CONTRACT = "RSH-FRENET-MULTI-DEVICE-CUDA-V1"
TESTED_COMMIT = "f590b4b251ad039e0b4c650fb29b7db3330708ef"
PATH_SHA256 = "2e69076c868cfdf7e77d904f60f3b3a5cf95fc411c48b75328aec2bd7ca49379"
EXPECTED_RUN_IDS = {
    31096520169,
    31102590955,
    31110426341,
    31113168005,
    31113751699,
}
HEX_64 = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_RESIDUALS = {
    "parallel": {
        "frame": 1.9477898010877848e-06,
        "position": 1.9637626254009888e-06,
        "schedule": 4.196258607258585e-08,
    },
    "shard": {
        "frame": 1.9477898026698526e-06,
        "position": 1.9637626329505053e-06,
        "schedule": 4.196258607258585e-08,
    },
}


class CampaignError(RuntimeError):
    """Raised when checked-in observed evidence is inconsistent."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CampaignError(f"{path} must contain an object")
    return value


def load_campaign(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    files = payload.get("observation_files")
    if not isinstance(files, list) or len(files) != 5:
        raise CampaignError("campaign must list five observation files")
    observations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in files:
        if (
            not isinstance(item, str)
            or re.fullmatch(r"run-[0-9]+\.json", item) is None
            or item in seen
        ):
            raise CampaignError("observation file list is invalid")
        seen.add(item)
        observations.append(load_json(path.parent / item))
    payload["observations"] = observations
    return payload


def require_bool(value: Any, expected: bool, label: str) -> None:
    if type(value) is not bool or value is not expected:
        raise CampaignError(f"{label} must be literal {expected!r}")


def require_int(value: Any, label: str) -> int:
    if type(value) is not int:
        raise CampaignError(f"{label} must be an integer")
    return value


def require_non_negative_int(value: Any, label: str) -> int:
    result = require_int(value, label)
    if result < 0:
        raise CampaignError(f"{label} must be non-negative")
    return result


def require_finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CampaignError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise CampaignError(f"{label} must be finite")
    return result


def require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX_64.fullmatch(value) is None:
        raise CampaignError(f"{label} must be lowercase SHA-256")
    return value


def validate_sanitizers(audit: dict[str, Any], label: str) -> None:
    sanitizers = audit.get("sanitizers")
    if not isinstance(sanitizers, list) or len(sanitizers) != 2:
        raise CampaignError(f"{label}.sanitizers must contain two entries")
    tools: set[str] = set()
    for item in sanitizers:
        if not isinstance(item, dict):
            raise CampaignError(f"{label}.sanitizers entries must be objects")
        tool = item.get("tool")
        if tool not in {"memcheck", "racecheck"} or tool in tools:
            raise CampaignError(f"{label}.sanitizers tool set is invalid")
        tools.add(tool)
        require_bool(item.get("available"), True, f"{label}.{tool}.available")
        if require_int(item.get("exit_code"), f"{label}.{tool}.exit_code") != 0:
            raise CampaignError(f"{label}.{tool} exit code must be zero")
        if item.get("status") != "PASS":
            raise CampaignError(f"{label}.{tool} status must be PASS")
    if tools != {"memcheck", "racecheck"}:
        raise CampaignError(f"{label}.sanitizers missing required tool")


def validate_observation(
    observation: dict[str, Any],
) -> tuple[int, list[float], list[str]]:
    run_id = require_int(observation.get("workflow_run_id"), "workflow_run_id")
    label = f"observation[{run_id}]"

    artifact = observation.get("artifact")
    workflow = observation.get("workflow")
    audit = observation.get("result")
    if not all(isinstance(item, dict) for item in (artifact, workflow, audit)):
        raise CampaignError(f"{label} artifact/workflow/result sections must be objects")

    selected = workflow.get("selected_device_indices")
    if not isinstance(selected, list) or len(selected) not in {2, 4}:
        raise CampaignError(f"{label} selected device list is invalid")
    for offset, device_index in enumerate(selected):
        require_non_negative_int(
            device_index,
            f"{label}.selected_device_indices[{offset}]",
        )
    if len(selected) != len(set(selected)):
        raise CampaignError(f"{label} selected devices contain duplicates")

    if audit.get("status") != "PASS":
        raise CampaignError(f"{label} status must be PASS")
    for key in (
        "actual_cuda_execution",
        "actual_multi_device_execution",
        "single_host_execution",
        "complete_path_readback",
    ):
        require_bool(audit.get(key), True, f"{label}.{key}")
    for key in (
        "distributed_execution",
        "universal_speedup_claim",
        "geometry_receipt_authority",
        "raw_device_uuid_published",
    ):
        require_bool(audit.get(key), False, f"{label}.{key}")

    if audit.get("used_device_indices") != selected:
        raise CampaignError(f"{label} selected/used device indices differ")
    devices = audit.get("devices")
    if not isinstance(devices, list) or len(devices) != len(selected):
        raise CampaignError(f"{label} device metadata count mismatch")

    redacted_ids: list[str] = []
    for slot, device in enumerate(devices):
        if not isinstance(device, dict):
            raise CampaignError(f"{label} device entry must be an object")
        logical_slot = require_non_negative_int(
            device.get("logical_slot"),
            f"{label}.devices[{slot}].logical_slot",
        )
        if logical_slot != slot:
            raise CampaignError(f"{label} logical slot mismatch")
        cuda_index = require_non_negative_int(
            device.get("cuda_index"),
            f"{label}.devices[{slot}].cuda_index",
        )
        if cuda_index != selected[slot]:
            raise CampaignError(f"{label} CUDA index mismatch")
        token = device.get("redacted_device_id")
        if not isinstance(token, str) or re.fullmatch(r"[0-9a-f]{16}", token) is None:
            raise CampaignError(f"{label} invalid redacted device id")
        if token in redacted_ids:
            raise CampaignError(f"{label} duplicate redacted device id")
        redacted_ids.append(token)
        if "uuid" in device or "device_uuid" in device:
            raise CampaignError(f"{label} raw UUID field is forbidden")

    repeats = audit.get("repeat_runs")
    if not isinstance(repeats, list) or len(repeats) != 3:
        raise CampaignError(f"{label} must contain exactly three repeat runs")
    times: list[float] = []
    for expected_index, repeat in enumerate(repeats):
        if not isinstance(repeat, dict):
            raise CampaignError(f"{label} repeat entry must be an object")
        repeat_index = require_non_negative_int(
            repeat.get("repeat_run"),
            f"{label}.repeat[{expected_index}].repeat_run",
        )
        if repeat_index != expected_index:
            raise CampaignError(f"{label} repeat order mismatch")
        if repeat.get("sidecar_status") != "PASS":
            raise CampaignError(f"{label} repeat sidecar did not pass")
        if require_sha256(
            repeat.get("path_sha256"),
            f"{label}.repeat[{expected_index}].path_sha256",
        ) != PATH_SHA256:
            raise CampaignError(f"{label} path hash mismatch")
        times.append(
            require_finite(
                repeat.get("end_to_end_milliseconds"),
                f"{label}.repeat[{expected_index}].time",
            )
        )
    if audit.get("repeatable_path_sha256") != PATH_SHA256:
        raise CampaignError(f"{label} repeatable path hash mismatch")

    validate_sanitizers(audit, label)

    require_sha256(artifact.get("archive_sha256"), f"{label}.artifact.archive_sha256")
    require_bool(
        artifact.get("downloaded_archive_sha256_verified"),
        True,
        f"{label}.artifact.downloaded_archive_sha256_verified",
    )
    require_sha256(artifact.get("audit_json_sha256"), f"{label}.artifact.audit_json_sha256")
    if require_sha256(
        artifact.get("path_csv_sha256"),
        f"{label}.artifact.path_csv_sha256",
    ) != PATH_SHA256:
        raise CampaignError(f"{label} path CSV checksum mismatch")
    return run_id, times, redacted_ids


def validate_campaign(payload: dict[str, Any]) -> None:
    if payload.get("schema") != SCHEMA:
        raise CampaignError("campaign schema mismatch")
    if payload.get("authority") != "observed-noncanonical":
        raise CampaignError("campaign authority must remain observed-noncanonical")
    if payload.get("contract") != CONTRACT:
        raise CampaignError("campaign contract mismatch")
    if payload.get("tested_commit") != TESTED_COMMIT:
        raise CampaignError("campaign tested commit mismatch")

    configuration = payload.get("configuration")
    invariants = payload.get("campaign_invariants")
    comparison = payload.get("controlled_same_host_comparison")
    observations = payload.get("observations")
    if not all(isinstance(item, dict) for item in (configuration, invariants, comparison)):
        raise CampaignError("campaign sections must be objects")
    if not isinstance(observations, list) or len(observations) != 5:
        raise CampaignError("campaign must contain five accepted observations")

    expected_configuration = {
        "samples": 4097,
        "intervals": 4096,
        "interval_width": 257,
        "shard_count": 16,
        "block_size": 128,
        "stream_count_per_device": 1,
        "complete_path_readback_required": True,
        "repeat_runs_per_observation": 3,
        "compute_sanitizer_memcheck_required": True,
        "compute_sanitizer_racecheck_required": True,
        "inter_device_peer_bytes": 0,
    }
    if configuration != expected_configuration:
        raise CampaignError("sealed campaign configuration mismatch")

    if invariants.get("max_residuals") != EXPECTED_RESIDUALS:
        raise CampaignError("campaign maximum residuals mismatch")
    if invariants.get("accepted_observations") != 5:
        raise CampaignError("accepted observation count mismatch")
    if invariants.get("physical_cuda_executions") != 15:
        raise CampaignError("physical CUDA execution count mismatch")
    if invariants.get("physical_device_count_range") != [2, 4]:
        raise CampaignError("physical device count range mismatch")
    require_sha256(
        invariants.get("repeatable_path_sha256"),
        "campaign_invariants.repeatable_path_sha256",
    )
    if invariants.get("repeatable_path_sha256") != PATH_SHA256:
        raise CampaignError("campaign path hash mismatch")
    for key in (
        "all_status_pass",
        "all_complete_path_readback",
        "all_required_sanitizers_pass",
    ):
        require_bool(invariants.get(key), True, f"campaign_invariants.{key}")
    for key in (
        "raw_device_uuid_published",
        "distributed_execution",
        "universal_speedup_claim",
        "geometry_receipt_authority",
    ):
        require_bool(invariants.get(key), False, f"campaign_invariants.{key}")

    run_times: dict[int, list[float]] = {}
    run_tokens: dict[int, list[str]] = {}
    seen: set[int] = set()
    for observation in observations:
        if not isinstance(observation, dict):
            raise CampaignError("observation entries must be objects")
        run_id, times, tokens = validate_observation(observation)
        if run_id in seen:
            raise CampaignError("duplicate workflow run id")
        seen.add(run_id)
        run_times[run_id] = times
        run_tokens[run_id] = tokens
    if seen != EXPECTED_RUN_IDS:
        raise CampaignError(f"workflow run set mismatch: {sorted(seen)}")

    two_id = require_int(
        comparison.get("two_device_workflow_run_id"),
        "comparison.two_device_workflow_run_id",
    )
    four_id = require_int(
        comparison.get("four_device_workflow_run_id"),
        "comparison.four_device_workflow_run_id",
    )
    if {two_id, four_id} != {31113168005, 31113751699}:
        raise CampaignError("controlled comparison run ids mismatch")
    if run_tokens[two_id] != run_tokens[four_id][:2]:
        raise CampaignError("same-host redacted device correlation failed")
    if comparison.get("shared_redacted_device_ids_for_cuda_indices_0_1") != run_tokens[two_id]:
        raise CampaignError("recorded shared device tokens mismatch")

    mean_two = statistics.mean(run_times[two_id])
    mean_four = statistics.mean(run_times[four_id])
    expected = {
        "two_device_mean_ms": mean_two,
        "four_device_mean_ms": mean_four,
        "four_minus_two_ms": mean_four - mean_two,
        "four_vs_two_percent_change": (mean_four / mean_two - 1.0) * 100.0,
        "two_over_four_mean_time_ratio": mean_two / mean_four,
    }
    for key, value in expected.items():
        actual = require_finite(comparison.get(key), f"comparison.{key}")
        if not math.isclose(actual, value, rel_tol=1.0e-12, abs_tol=1.0e-12):
            raise CampaignError(f"comparison.{key} is inconsistent")
    require_bool(comparison.get("speedup_claim"), False, "comparison.speedup_claim")
    if not mean_four > mean_two:
        raise CampaignError("controlled comparison must record four devices as slower")

    boundary = payload.get("implementation_boundary")
    if not isinstance(boundary, dict):
        raise CampaignError("implementation_boundary must be an object")
    require_bool(boundary.get("inter_device_peer_traffic"), False, "inter_device_peer_traffic")
    require_bool(boundary.get("nvlink_or_peer_to_peer_used"), False, "nvlink_or_peer_to_peer_used")
    require_bool(boundary.get("eight_device_execution_performed"), False, "eight_device_execution_performed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "campaign",
        nargs="?",
        type=Path,
        default=Path("conformance/observed/multi-device-cuda/2026-08-06/campaign.json"),
    )
    args = parser.parse_args()
    validate_campaign(load_campaign(args.campaign))
    print(f"Accepted multi-device CUDA campaign: {args.campaign}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
