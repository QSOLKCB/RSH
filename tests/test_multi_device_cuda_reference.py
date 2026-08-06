from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import multi_device_cuda_reference as reference

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "conformance" / "frenet_multi_device_cuda_v1_4097.json"


class MultiDeviceCudaReferenceTests(unittest.TestCase):
    def test_sealed_profile(self):
        report, csv_text = reference.verify_profile(PROFILE)
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        self.assertEqual(
            report["canonical_sha256"], profile["expected"]["canonical_sha256"]
        )
        self.assertEqual(
            report["path_csv_sha256"], profile["expected"]["path_csv_sha256"]
        )
        self.assertEqual(len(csv_text.rstrip("\n").splitlines()), 4098)

    def test_partition_and_round_robin_assignment(self):
        report, _ = reference.build_reference(
            samples=17, interval_width=3, logical_devices=2
        )
        assignments = report["assignments"]
        self.assertEqual(
            [
                (item["start_interval"], item["end_interval_exclusive"])
                for item in assignments
            ],
            [(0, 3), (3, 6), (6, 9), (9, 12), (12, 15), (15, 16)],
        )
        self.assertEqual(
            [item["logical_device_slot"] for item in assignments],
            [0, 1, 0, 1, 0, 1],
        )
        self.assertEqual(sum(item["interval_count"] for item in assignments), 16)

    def test_input_bounds_and_types(self):
        invalid_arguments = (
            {"samples": True},
            {"samples": 2},
            {"samples": 4},
            {"samples": reference.MAX_SAMPLES + 2},
            {"interval_width": 0},
            {"logical_devices": 1},
            {"logical_devices": reference.MAX_LOGICAL_DEVICES + 1},
        )
        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                reference.build_reference(**arguments)

    def test_claims_are_literal_false(self):
        report, _ = reference.build_reference(
            samples=17, interval_width=3, logical_devices=2
        )
        self.assertEqual(report["claims"], reference.CLAIMS)
        for value in report["claims"].values():
            self.assertIs(value, False)

    def test_complete_readback_shape(self):
        report, csv_text = reference.build_reference(
            samples=33, interval_width=7, logical_devices=3
        )
        rows = csv_text.rstrip("\n").splitlines()
        self.assertEqual(report["path_point_count"], 33)
        self.assertEqual(report["path_float_components_per_point"], 16)
        self.assertTrue(report["complete_path_readback"])
        self.assertEqual(len(rows), 34)
        self.assertEqual(len(rows[1].split(",")), 17)

    def test_tampered_profile_hash_is_rejected(self):
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        profile["expected"]["canonical_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaises(AssertionError):
                reference.verify_profile(path)

    def test_profile_contract_is_enforced(self):
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        profile["contract"] = "WRONG"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaises(ValueError):
                reference.verify_profile(path)

    def test_all_portable_gates_pass(self):
        report, _ = reference.build_reference()
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        for key, gate in profile["gates"].items():
            self.assertLessEqual(report["residuals"][key], gate, key)


if __name__ == "__main__":
    unittest.main()
