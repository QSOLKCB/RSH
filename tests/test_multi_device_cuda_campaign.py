from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_multi_device_cuda_campaign.py"
MANIFEST = (
    ROOT
    / "conformance"
    / "observed"
    / "multi-device-cuda"
    / "2026-08-06"
    / "campaign.json"
)

SPEC = importlib.util.spec_from_file_location(
    "verify_multi_device_cuda_campaign",
    SCRIPT,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MultiDeviceCudaCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = MODULE.load_campaign(MANIFEST)

    def test_checked_in_campaign_passes(self) -> None:
        MODULE.validate_campaign(copy.deepcopy(self.payload))

    def test_rejects_path_hash_mutation(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["observations"][0]["result"]["repeat_runs"][0]["path_sha256"] = "0" * 64
        with self.assertRaises(MODULE.CampaignError):
            MODULE.validate_campaign(payload)

    def test_rejects_authority_promotion(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["observations"][0]["result"]["geometry_receipt_authority"] = True
        with self.assertRaises(MODULE.CampaignError):
            MODULE.validate_campaign(payload)

    def test_rejects_sanitizer_failure(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["observations"][0]["result"]["sanitizers"][0]["exit_code"] = 1
        with self.assertRaises(MODULE.CampaignError):
            MODULE.validate_campaign(payload)

    def test_rejects_broken_same_host_correlation(self) -> None:
        payload = copy.deepcopy(self.payload)
        comparison = payload["controlled_same_host_comparison"]
        comparison["shared_redacted_device_ids_for_cuda_indices_0_1"][0] = "0" * 16
        with self.assertRaises(MODULE.CampaignError):
            MODULE.validate_campaign(payload)

    def test_rejects_false_speedup_arithmetic(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["controlled_same_host_comparison"]["two_over_four_mean_time_ratio"] = 2.0
        with self.assertRaises(MODULE.CampaignError):
            MODULE.validate_campaign(payload)

    def test_rejects_invalid_selected_device_indices(self) -> None:
        for invalid in ("0", True, -1):
            with self.subTest(invalid=invalid):
                payload = copy.deepcopy(self.payload)
                observation = payload["observations"][0]
                observation["workflow"]["selected_device_indices"][0] = invalid
                observation["result"]["used_device_indices"][0] = invalid
                observation["result"]["devices"][0]["cuda_index"] = invalid
                with self.assertRaises(MODULE.CampaignError):
                    MODULE.validate_campaign(payload)


if __name__ == "__main__":
    unittest.main()
