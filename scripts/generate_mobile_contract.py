#!/usr/bin/env python3
"""Generate mobile PWA contract metadata from RSH-owned sources."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CONSTANTS = ROOT / "src" / "rsh" / "constants.py"
FIXTURE = ROOT / "conformance" / "ffi_v1_129.json"
OUTPUT = ROOT / "web" / "mobile" / "contract.json"


def load_constants():
    spec = importlib.util.spec_from_file_location("rsh_mobile_constants", CONSTANTS)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load RSH constants")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_payload() -> dict:
    constants = load_constants()
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return {
        "schema": "RSH-MOBILE-CONTRACT-METADATA-V1",
        "model": constants.MODEL_NAME,
        "model_version": constants.VERSION,
        "psi": constants.PSI,
        "kappa_max": constants.KAPPA_MAX,
        "tau_min_exclusive": constants.TAU_MIN_EXCLUSIVE,
        "tau_max_exclusive": constants.TAU_MAX_EXCLUSIVE,
        "canonical_float_precision": constants.CANONICAL_FLOAT_PRECISION,
        "configuration": fixture["configuration"],
        "sealed_ffi_fixture": {
            "schema": fixture["schema"],
            "abi_version": fixture["abi_version"],
            "layout": fixture["layout"],
            "coordinate_tolerance": fixture["coordinate_tolerance"],
            "centre_tolerance": fixture["centre_tolerance"],
            "entry": fixture["entry"],
            "exit": fixture["exit"],
            "canonical_rust_receipt": fixture["canonical_rust_receipt"],
        },
        "authority": {
            "generated_from": ["src/rsh/constants.py", "conformance/ffi_v1_129.json"],
            "geometry_receipt_authority": False,
            "geometry_contract_modified": False,
            "presentation_metadata_only": True,
        },
    }


def rendered() -> str:
    return json.dumps(build_payload(), indent=2, sort_keys=True, allow_nan=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if the generated file is stale")
    args = parser.parse_args()
    expected = rendered()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != expected:
            print(f"{OUTPUT.relative_to(ROOT)} is stale; run scripts/generate_mobile_contract.py", file=sys.stderr)
            return 1
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(expected, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
