from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path
import tempfile
import unittest

from rsh.evidence import (
    build_and_verify,
    verify,
    verify_parallel,
    write_report_json,
    write_trace_csv,
    write_verify_csv,
)
from rsh.geometry import ModelConfig
from rsh.visual import write_svg


GOLDEN_RECEIPT_129 = (
    "407fc894060a179e8fc857d8b4abe2e8b6cd18b58663f610fc60f4e13ec0ddd1"
)
GOLDEN_ENTRY_129 = (
    -1.8484919565721223,
    -0.6353766408175766,
    -0.16593646474199972,
)
GOLDEN_EXIT_129 = (
    1.2097010814305758,
    1.2168907843927106,
    0.9663511535281694,
)


class EvidenceTests(unittest.TestCase):
    def test_report_matches_golden_reference_and_replays(self) -> None:
        config = ModelConfig(samples=129)
        rows_a, report_a = build_and_verify(config)
        rows_b, report_b = build_and_verify(config)

        self.assertTrue(report_a.pass_all)
        self.assertEqual(report_a.receipt, GOLDEN_RECEIPT_129)
        self.assertEqual(report_a.receipt, report_b.receipt)
        self.assertEqual(len(report_a.receipt), 64)
        int(report_a.receipt, 16)
        self.assertEqual(rows_a, rows_b)

        for actual, expected in zip(
            rows_a[0].position,
            GOLDEN_ENTRY_129,
        ):
            self.assertAlmostEqual(actual, expected, places=15)
        for actual, expected in zip(
            rows_a[-1].position,
            GOLDEN_EXIT_129,
        ):
            self.assertAlmostEqual(actual, expected, places=15)

    def test_schedule_parameters_are_in_report_and_receipt(self) -> None:
        config = ModelConfig(
            samples=129,
            kappa_fraction=0.73,
            tau_floor=0.31,
            tau_amplitude=0.08,
        )
        report = build_and_verify(config)[1]
        default_report = build_and_verify(ModelConfig(samples=129))[1]

        self.assertEqual(report.kappa_fraction, config.kappa_fraction)
        self.assertEqual(report.tau_floor, config.tau_floor)
        self.assertEqual(report.tau_amplitude, config.tau_amplitude)
        self.assertNotEqual(report.receipt, default_report.receipt)

    def test_parameter_change_changes_receipt(self) -> None:
        first = build_and_verify(
            ModelConfig(samples=129, s1=4.0)
        )[1]
        second = build_and_verify(
            ModelConfig(samples=129, s1=4.5)
        )[1]
        self.assertNotEqual(first.receipt, second.receipt)

    def test_non_finite_frame_is_rejected(self) -> None:
        config = ModelConfig(samples=65)
        rows, _report = build_and_verify(config)
        invalid_rows = list(rows)
        invalid_rows[0] = replace(invalid_rows[0], tx=math.nan)

        with self.assertRaisesRegex(
            ValueError,
            "non-finite frame component",
        ):
            verify(invalid_rows, config)

    def test_concurrent_replay_parity(self) -> None:
        baseline, reports, parity_ok = verify_parallel(
            ModelConfig(samples=65),
            workers=3,
        )
        self.assertTrue(parity_ok)
        self.assertEqual(len(reports), 3)
        self.assertTrue(
            all(item.receipt == baseline.receipt for item in reports)
        )

    def test_exports_are_created(self) -> None:
        rows, report = build_and_verify(ModelConfig(samples=65))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trace = root / "trace.csv"
            verify_csv = root / "verify.csv"
            report_json = root / "verify.json"
            visual = root / "visual.svg"

            write_trace_csv(rows, trace)
            write_verify_csv(report, verify_csv)
            write_report_json(report, report_json)
            write_svg(rows, visual)

            self.assertTrue(
                trace.read_text(encoding="utf-8").startswith(
                    "p,s,x,y,z"
                )
            )
            self.assertIn(
                "metric,value",
                verify_csv.read_text(encoding="utf-8"),
            )
            exported_report = json.loads(
                report_json.read_text(encoding="utf-8")
            )
            self.assertEqual(
                exported_report["receipt"],
                report.receipt,
            )
            self.assertEqual(
                exported_report["kappa_fraction"],
                report.kappa_fraction,
            )
            visual_text = visual.read_text(encoding="utf-8")
            self.assertIn('data-model="RSH"', visual_text)
            self.assertIn("data-pixels-per-unit=", visual_text)


if __name__ == "__main__":
    unittest.main()
