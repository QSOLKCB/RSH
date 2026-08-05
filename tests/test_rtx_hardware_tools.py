from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_rtx_hardware.py"
SPEC = importlib.util.spec_from_file_location("verify_rtx_hardware", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TrustedRtxValidationTests(unittest.TestCase):
    def cuda_summary(self) -> dict:
        return {
            "schema": "RSH-CUDA-HARDWARE-TEST-RESULT-V1",
            "status": "PASS",
            "runs_completed": 3,
            "repeatable": True,
            "sidecar": {
                "actual_cuda_execution": True,
                "geometry_receipt_authority": False,
                "device": "NVIDIA GeForce RTX 5060 Ti",
                "device_uuid": "11111111-2222-3333-4444-555555555555",
                "compute_capability": "12.0",
                "compiled_architectures": "120",
                "maximum_residual": 4.1e-8,
                "threshold": 1e-4,
            },
            "sanitizers": [
                {"tool": "memcheck", "available": True, "status": "PASS"},
                {"tool": "racecheck", "available": True, "status": "PASS"},
            ],
        }

    def schedule(self) -> dict:
        return {
            "schema": "RSH-TRUSTED-RTX-WEBGPU-SCHEDULE-V1",
            "status": "PASS",
            "adapter": "nvidia · blackwell",
            "maximum_residual": 6.7e-8,
            "threshold": 1e-4,
            "actual_gpu_execution": True,
            "complete_field_readback": True,
            "speedup_claim": False,
            "universal_speedup_claim": False,
            "geometry_receipt_authority": False,
        }

    def parallel(self) -> dict:
        return {
            "schema": "RSH-WEBGPU-FRENET-PARALLEL-BENCHMARK-V1",
            "status": "PASS",
            "configuration": {"samples": 4097},
            "metadata": {
                "adapter": "nvidia · blackwell",
                "scan_passes": 13,
                "transform_bytes": 32,
            },
            "residuals": {
                "max_position_component_vs_f64": 5e-7,
                "max_frame_component_vs_f64": 4.5e-7,
                "max_schedule_component_vs_f64": 6.3e-8,
                "max_frame_norm_error": 3.8e-7,
                "max_frame_orthogonality_error": 4.9e-7,
            },
            "gates": {
                "position_component_gate": 5e-4,
                "frame_component_gate": 5e-4,
                "schedule_component_gate": 1e-4,
                "frame_norm_gate": 5e-5,
                "frame_orthogonality_gate": 5e-5,
            },
            "benchmark": {
                "warmup_runs": 2,
                "measured_runs": 7,
                "observed_speedup": 1.6,
            },
            "actual_gpu_execution": True,
            "parallel_scan_execution": True,
            "complete_path_readback": True,
            "actual_multi_device_execution": False,
            "distributed_execution": False,
            "speedup_claim": True,
            "speedup_claim_scope": "observed adapter only",
            "universal_speedup_claim": False,
            "geometry_receipt_authority": False,
        }

    def test_passing_evidence_is_accepted_and_redacted(self) -> None:
        cuda_errors, redacted = MODULE.validate_cuda(self.cuda_summary())
        schedule_errors, _ = MODULE.validate_schedule(self.schedule())
        parallel_errors, _ = MODULE.validate_parallel(self.parallel())
        self.assertEqual(cuda_errors, [])
        self.assertEqual(schedule_errors, [])
        self.assertEqual(parallel_errors, [])
        self.assertNotIn("device_uuid", redacted)

    def test_software_webgpu_adapter_is_rejected(self) -> None:
        schedule = self.schedule()
        schedule["adapter"] = "Google SwiftShader software adapter"
        errors, _ = MODULE.validate_schedule(schedule)
        self.assertTrue(any("NVIDIA" in error or "software" in error for error in errors))

    def test_missing_required_sanitizer_is_rejected(self) -> None:
        cuda = self.cuda_summary()
        cuda["sanitizers"] = [
            {"tool": "memcheck", "available": True, "status": "PASS"}
        ]
        errors, _ = MODULE.validate_cuda(cuda)
        self.assertIn("CUDA racecheck result is missing", errors)

    def test_parallel_gate_failure_is_rejected(self) -> None:
        parallel = self.parallel()
        parallel["residuals"]["max_frame_component_vs_f64"] = 6e-4
        errors, _ = MODULE.validate_parallel(parallel)
        self.assertIn(
            "parallel max_frame_component_vs_f64 exceeds its gate",
            errors,
        )

    def test_authority_promotion_is_rejected(self) -> None:
        parallel = self.parallel()
        parallel["geometry_receipt_authority"] = True
        errors, _ = MODULE.validate_parallel(parallel)
        self.assertIn(
            "parallel geometry_receipt_authority must be False",
            errors,
        )


if __name__ == "__main__":
    unittest.main()
