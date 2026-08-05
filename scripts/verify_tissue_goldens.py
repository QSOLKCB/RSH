#!/usr/bin/env python3
"""Verify a live Python tissue report against the sealed 8x20 goldens."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare a live RSH tissue report with a sealed conformance profile."
    )
    parser.add_argument(
        "--profile",
        type=Path,
        default=Path("conformance/tissue_v1_8x20.json"),
        help="sealed tissue conformance profile",
    )
    parser.add_argument(
        "--report",
        type=Path,
        required=True,
        help="fresh Python tissue JSON report",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"{path}: {error}") from error
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: expected a JSON object")
    return payload


def require_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise SystemExit(f"missing or invalid object: {key}")
    return value


def require_ticks(report: dict[str, Any]) -> list[dict[str, Any]]:
    ticks = report.get("ticks")
    if not isinstance(ticks, list) or not ticks:
        raise SystemExit("live report must contain at least one tissue tick")
    if not all(isinstance(tick, dict) for tick in ticks):
        raise SystemExit("live report contains a malformed tissue tick")
    return ticks


def near(left: Any, right: Any, tolerance: float) -> bool:
    try:
        left_value = float(left)
        right_value = float(right)
    except (TypeError, ValueError):
        return False
    return (
        math.isfinite(left_value)
        and math.isfinite(right_value)
        and abs(left_value - right_value) <= tolerance
    )


def main() -> int:
    args = parse_args()
    profile = load_json(args.profile)
    report = load_json(args.report)

    if profile.get("schema") != "RSH-TISSUE-CONFORMANCE-V1":
        raise SystemExit("unexpected tissue conformance profile schema")
    if report.get("schema") != "RSH-TISSUE-REPORT-V1":
        raise SystemExit("unexpected live tissue report schema")

    expected = require_mapping(profile, "expected")
    tolerance = float(expected["observable_absolute_tolerance"])
    if not math.isfinite(tolerance) or tolerance <= 0.0:
        raise SystemExit("observable_absolute_tolerance must be positive and finite")

    ticks = require_ticks(report)
    first_tick = ticks[0]
    last_tick = ticks[-1]
    first_metrics = require_mapping(first_tick, "metrics")
    last_metrics = require_mapping(last_tick, "metrics")

    centre_errors = [tick.get("centre_error") for tick in ticks]
    try:
        maximum_centre_error = max(float(value) for value in centre_errors)
    except (TypeError, ValueError) as error:
        raise SystemExit("live report contains an invalid centre_error") from error

    checks: list[tuple[str, bool, Any, Any]] = []

    def exact(name: str, live: Any, sealed: Any) -> None:
        checks.append((name, live == sealed, live, sealed))

    def approximate(name: str, live: Any, sealed: Any) -> None:
        checks.append((name, near(live, sealed, tolerance), live, sealed))

    exact("constitution_hash", report.get("constitution_hash"), expected.get("constitution_hash"))
    exact(
        "seed_geometry_receipt",
        report.get("seed_geometry_receipt"),
        expected.get("seed_geometry_receipt"),
    )
    approximate("first_q_f", first_metrics.get("q_f"), expected.get("first_q_f"))
    approximate("final_q_f", report.get("final_q_f"), expected.get("final_q_f"))
    approximate("minimum_q_f", report.get("min_q_f"), expected.get("minimum_q_f"))
    approximate("maximum_q_f", report.get("max_q_f"), expected.get("maximum_q_f"))
    approximate(
        "final_dissociation",
        last_metrics.get("dissociation"),
        expected.get("final_dissociation"),
    )

    centre_gate = float(expected["maximum_centre_error"])
    checks.append(
        (
            "maximum_centre_error_gate",
            math.isfinite(maximum_centre_error)
            and maximum_centre_error <= centre_gate + tolerance,
            maximum_centre_error,
            centre_gate,
        )
    )

    exact("audit_chain_valid", report.get("audit_chain_valid"), True)
    exact("reference_report_receipt", report.get("receipt"), expected.get("reference_report_receipt"))
    exact(
        "reference_first_tick_receipt",
        first_tick.get("receipt"),
        expected.get("reference_first_tick_receipt"),
    )
    exact(
        "reference_last_tick_receipt",
        last_tick.get("receipt"),
        expected.get("reference_last_tick_receipt"),
    )

    failures = 0
    print(f"profile={args.profile}")
    print(f"report={args.report}")
    print(f"tolerance={tolerance:.17e}")
    for name, passed, live, sealed in checks:
        status = "PASS" if passed else "FAIL"
        failures += int(not passed)
        print(f"{status} {name}: live={live!r} sealed={sealed!r}")

    result = "PASS" if failures == 0 else "FAIL"
    print(f"RESULT={result} failed={failures}/{len(checks)}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
