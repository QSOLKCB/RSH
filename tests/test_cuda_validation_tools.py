from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cuda_profile() -> dict[str, object]:
    return {
        "schema": "RSH-CUDA-SCHEDULE-CONFORMANCE-V1",
        "configuration": {
            "samples": 4096,
            "s0": 0.0,
            "s1": 4.0,
            "kappa_fraction": 0.85,
            "tau_floor": 0.22,
            "tau_amplitude": 0.13,
        },
        "precision": "f32",
        "block_size": 128,
        "residual_threshold": 1.0e-4,
    }


def cuda_sidecar() -> dict[str, object]:
    return {
        "schema": "RSH-CUDA-RESIDUAL-SIDECAR-V1",
        "status": "PASS",
        "diagnostic_status": "NOMINAL",
        "actual_cuda_execution": True,
        "device_index": 0,
        "device": "Example GPU",
        "device_uuid": "00000000-0000-0000-0000-000000000000",
        "compute_capability": "12.0",
        "compiled_architectures": "120",
        "cuda_driver_api_version": 13010,
        "cuda_driver_api": "13.1",
        "cuda_runtime_version": 13010,
        "cuda_runtime": "13.1",
        "cuda_compile_version": 13010,
        "cuda_compile": "13.1",
        "host_pointer_width": 64,
        "repeat_run": 1,
        "samples": 4096,
        "block_size": 128,
        "grid_blocks": 32,
        "max_abs_kappa_vs_rust_f64": 4.0e-8,
        "max_abs_tau_vs_rust_f64": 3.0e-8,
        "maximum_residual": 4.0e-8,
        "diagnostic_observation_band": 1.0e-6,
        "threshold": 1.0e-4,
        "geometry_receipt_authority": False,
    }


class CudaValidationToolsTests(unittest.TestCase):
    def test_sidecar_validation_and_repeatability_ignore_run_identifier(self) -> None:
        module = load_script("test_cuda.py")
        profile = cuda_profile()
        sidecar = cuda_sidecar()
        self.assertEqual(module.validate_sidecar(sidecar, profile, expected_run=1), [])
        second = dict(sidecar, repeat_run=2)
        self.assertEqual(
            module.repeatability_record(sidecar),
            module.repeatability_record(second),
        )

    def test_threshold_comparison_tolerates_equivalent_float_formatting(self) -> None:
        module = load_script("test_cuda.py")
        sidecar = cuda_sidecar()
        sidecar["threshold"] = math.nextafter(1.0e-4, math.inf)
        self.assertEqual(module.validate_sidecar(sidecar, cuda_profile()), [])

    def test_sidecar_rejects_receipt_authority_and_component_inconsistency(self) -> None:
        module = load_script("test_cuda.py")
        sidecar = cuda_sidecar()
        sidecar.update(
            geometry_receipt_authority=True,
            max_abs_kappa_vs_rust_f64=2.0e-4,
            maximum_residual=4.0e-8,
        )
        errors = module.validate_sidecar(sidecar, cuda_profile())
        self.assertTrue(any("authority" in error for error in errors))
        self.assertTrue(
            any("max_abs_kappa_vs_rust_f64 exceeds" in error for error in errors)
        )
        self.assertTrue(any("maximum component residual" in error for error in errors))

    def test_sidecar_requires_complete_provenance(self) -> None:
        module = load_script("test_cuda.py")
        sidecar = cuda_sidecar()
        for field in (
            "device_uuid",
            "compiled_architectures",
            "cuda_driver_api_version",
            "cuda_runtime_version",
            "cuda_compile_version",
            "grid_blocks",
            "host_pointer_width",
            "diagnostic_status",
            "repeat_run",
        ):
            sidecar.pop(field)
        errors = module.validate_sidecar(sidecar, cuda_profile(), expected_run=1)
        for field in (
            "device_uuid",
            "compiled_architectures",
            "cuda_driver_api_version",
            "cuda_runtime_version",
            "cuda_compile_version",
            "grid_blocks",
            "host_pointer_width",
            "diagnostic_status",
            "repeat_run",
        ):
            self.assertTrue(any(field in error for error in errors), field)

    def test_profile_rejects_unimplemented_schedule_configuration(self) -> None:
        module = load_script("test_cuda.py")
        profile = cuda_profile()
        profile["configuration"] = dict(profile["configuration"], tau_floor=0.23)
        with self.assertRaisesRegex(ValueError, "sealed value"):
            module.profile_parameters(profile)

    def test_output_directory_must_be_empty(self) -> None:
        module = load_script("test_cuda.py")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "audit"
            output.mkdir()
            (output / "stale.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must be empty"):
                module.prepare_output_directory(output)

    def test_evidence_zip_is_deterministic_and_avoids_self_hashing(self) -> None:
        module = load_script("package_evidence.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "evidence"
            root.mkdir()
            (root / "audit-summary.json").write_text(
                json.dumps({"status": "PASS"}) + "\n", encoding="utf-8"
            )
            (root / "run.json").write_text("{}\n", encoding="utf-8")
            first = Path(directory) / "first.zip"
            second = Path(directory) / "second.zip"
            module.package_evidence(root, first, "evidence")
            module.package_evidence(root, second, "evidence")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            manifest = (root / "SHA256SUMS.txt").read_text(encoding="utf-8")
            self.assertIn("audit-summary.json", manifest)
            self.assertNotIn("SHA256SUMS.txt", manifest)
            with zipfile.ZipFile(first) as archive:
                self.assertIn("evidence/SHA256SUMS.txt", archive.namelist())


if __name__ == "__main__":
    unittest.main()
