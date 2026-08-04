#!/usr/bin/env python3
"""Execute the C++ adapter against the sealed native and CUDA-reference profiles."""

from __future__ import annotations

import json
import math
import pathlib
import subprocess
import sys
import tempfile
from typing import Any


def load_json(path: pathlib.Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def max_abs_error(actual: list[float], expected: list[float]) -> float:
    if len(actual) != len(expected):
        raise AssertionError("coordinate vector length mismatch")
    return max(abs(float(left) - float(right)) for left, right in zip(actual, expected))


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, text=True, capture_output=True)


def main() -> int:
    executable = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "build/rsh-cpp")
    ffi_profile_path = pathlib.Path(
        sys.argv[2] if len(sys.argv) > 2 else "conformance/ffi_v1_129.json"
    )
    cuda_profile_path = pathlib.Path(
        sys.argv[3] if len(sys.argv) > 3 else "conformance/cuda_schedule_v1_4096.json"
    )
    ffi_profile = load_json(ffi_profile_path)
    cuda_profile = load_json(cuda_profile_path)

    with tempfile.TemporaryDirectory(prefix="rsh-ffi-") as directory:
        root = pathlib.Path(directory)
        report_path = root / "report.json"
        trace_path = root / "schedule.csv"

        verify = run(
            str(executable),
            "verify",
            "--samples",
            str(ffi_profile["configuration"]["samples"]),
            "--json",
            str(report_path),
        )
        if "RSH C++ FFI verify [PASS]" not in verify.stdout:
            raise AssertionError("C++ adapter did not report a passing verification")
        report = load_json(report_path)

        assert report["pass_all"] is ffi_profile["requirements"]["pass_all"]
        assert int(report["samples"]) == int(ffi_profile["configuration"]["samples"])
        assert report["receipt"] == ffi_profile["canonical_rust_receipt"]
        assert float(report["centre_error"]) <= float(ffi_profile["centre_tolerance"])
        entry_error = max_abs_error(report["entry"], ffi_profile["entry"])
        exit_error = max_abs_error(report["exit"], ffi_profile["exit"])
        assert entry_error <= float(ffi_profile["coordinate_tolerance"])
        assert exit_error <= float(ffi_profile["coordinate_tolerance"])

        schedule = run(
            str(executable),
            "schedule",
            "--samples",
            str(cuda_profile["configuration"]["samples"]),
            "--csv",
            str(trace_path),
        )
        if "RSH C++ FFI schedule [PASS]" not in schedule.stdout:
            raise AssertionError("C++ adapter did not report a passing schedule")
        lines = trace_path.read_text(encoding="utf-8").splitlines()
        expected_lines = int(cuda_profile["configuration"]["samples"]) + 1
        assert len(lines) == expected_lines, (len(lines), expected_lines)

        reference = run(
            str(executable),
            "cuda-reference",
            "--samples",
            str(cuda_profile["configuration"]["samples"]),
            "--threshold",
            str(cuda_profile["residual_threshold"]),
        )
        residual = json.loads(reference.stdout)
        assert residual["schema"] == "RSH-CUDA-F32-REFERENCE-V1"
        assert residual["status"] == "PASS"
        assert residual["actual_cuda_execution"] is False
        assert int(residual["samples"]) == int(cuda_profile["configuration"]["samples"])
        assert math.isfinite(float(residual["maximum_residual"]))
        assert float(residual["maximum_residual"]) <= float(
            cuda_profile["residual_threshold"]
        )

    print(
        json.dumps(
            {
                "schema": "RSH-CPP-FFI-CONFORMANCE-RESULT-V1",
                "status": "PASS",
                "executable": str(executable),
                "abi_version": ffi_profile["abi_version"],
                "samples": ffi_profile["configuration"]["samples"],
                "entry_max_abs_error": entry_error,
                "exit_max_abs_error": exit_error,
                "rust_receipt": report["receipt"],
                "cuda_reference_samples": residual["samples"],
                "cuda_reference_maximum_residual": residual["maximum_residual"],
                "actual_cuda_execution": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
