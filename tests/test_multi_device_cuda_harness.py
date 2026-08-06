from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts import test_multi_device_cuda as harness

ROOT = Path(__file__).resolve().parents[1]
PROFILE = json.loads(
    (ROOT / "conformance" / "frenet_multi_device_cuda_v1_4097.json").read_text()
)


def valid_sidecar():
    configuration = PROFILE["configuration"]
    sharding = PROFILE["sharding"]
    devices = [0, 1]
    start = 0
    shards = []
    for index in range(sharding["expected_shard_count"]):
        count = (
            sharding["expected_final_shard_interval_count"]
            if index + 1 == sharding["expected_shard_count"]
            else sharding["interval_width"]
        )
        slot = index % 2
        shards.append(
            {
                "shard_index": index,
                "start_interval": start,
                "end_interval_exclusive": start + count,
                "interval_count": count,
                "device_slot": slot,
                "cuda_device_index": devices[slot],
                "stream_ordinal": 0,
            }
        )
        start += count
    sidecar = {
        "schema": harness.SCHEMA,
        "contract": harness.CONTRACT,
        "source_parallel_contract": PROFILE["source_parallel_contract"],
        "source_shard_prefix_contract": PROFILE["source_shard_prefix_contract"],
        "status": "PASS",
        "actual_cuda_execution": True,
        "actual_multi_device_execution": True,
        "single_host_execution": True,
        "distributed_execution": False,
        "universal_speedup_claim": False,
        "geometry_receipt_authority": False,
        "raw_device_uuid_published": False,
        "assignment_policy": PROFILE["assignment_policy"],
        "local_prefix_policy": PROFILE["local_prefix_policy"],
        "shard_prefix_policy": PROFILE["shard_prefix_policy"],
        "assembly_policy": PROFILE["assembly_policy"],
        "repeat_run": 0,
        "detected_device_count": 2,
        "used_device_count": 2,
        "samples": configuration["samples"],
        "intervals": sharding["expected_intervals"],
        "interval_width": sharding["interval_width"],
        "shard_count": sharding["expected_shard_count"],
        "shard_prefix_passes": sharding["expected_shard_prefix_passes"],
        "final_shard_interval_count": sharding[
            "expected_final_shard_interval_count"
        ],
        "block_size": 128,
        "stream_count_per_device": 1,
        "reduction_transfer_bytes": sharding["expected_shard_count"] * 32,
        "base_transfer_bytes": sharding["expected_shard_count"] * 32,
        "inter_device_peer_bytes": 0,
        "final_readback_bytes": configuration["samples"] * 64,
        "readback_point_count": configuration["samples"],
        "readback_float_components_per_point": 16,
        "complete_path_readback": True,
        "compiled_architectures": "120",
        "cuda_driver_api_version": 13010,
        "cuda_runtime_version": 13010,
        "cuda_compile_version": 13010,
        "max_frame_norm_error": 1.0e-7,
        "max_frame_orthogonality_error": 1.0e-7,
        "max_tail_vs_reduction_component_error": 0.0,
        "centre_error": 0.0,
        "frame_gate": 5.0e-5,
        "tail_gate": 1.0e-5,
        "centre_gate": 1.0e-6,
        "pass_finite": True,
        "pass_coverage": True,
        "pass_schedule_bounds": True,
        "pass_frame": True,
        "pass_centre": True,
        "pass_tail_integrity": True,
        "devices": [
            {
                "logical_slot": index,
                "cuda_index": index,
                "name": f"GPU {index}",
                "redacted_device_id": token,
                "compute_capability": "12.0",
                "total_memory_bytes": 1,
                "stream_ordinal": 0,
            }
            for index, token in enumerate(
                ("0123456789abcdef", "fedcba9876543210")
            )
        ],
        "shards": shards,
    }
    return sidecar


class MultiDeviceCudaHarnessTests(unittest.TestCase):
    def test_valid(self):
        harness.validate_sidecar(valid_sidecar(), PROFILE, 0, [0, 1])

    def test_rejects_boundaries(self):
        for field, value in (
            ("used_device_count", 1),
            ("used_device_count", True),
            ("geometry_receipt_authority", True),
        ):
            with self.subTest(field=field):
                sidecar = valid_sidecar()
                sidecar[field] = value
                with self.assertRaises(harness.ValidationError):
                    harness.validate_sidecar(sidecar, PROFILE, 0, [0, 1])
        sidecar = valid_sidecar()
        sidecar["shards"][1]["start_interval"] -= 1
        with self.assertRaises(harness.ValidationError):
            harness.validate_sidecar(sidecar, PROFILE, 0, [0, 1])

    def test_claim_type(self):
        profile = copy.deepcopy(PROFILE)
        profile["portable_claims"]["distributed_execution"] = 0
        with self.assertRaises(harness.ValidationError):
            harness.validate_profile(profile)

    def test_compare_rows(self):
        row = {"index": 0, **{field: 0.0 for field in harness.CSV_FIELDS[1:]}}
        gates = {
            "position_component_gate": 1.0e-3,
            "frame_component_gate": 1.0e-3,
            "schedule_component_gate": 1.0e-3,
        }
        self.assertEqual(
            harness.compare_rows([row], [dict(row)], gates),
            {"position": 0.0, "frame": 0.0, "schedule": 0.0},
        )
        changed = dict(row)
        changed["x"] = 0.01
        with self.assertRaises(harness.ValidationError):
            harness.compare_rows([changed], [row], gates)


if __name__ == "__main__":
    unittest.main()
