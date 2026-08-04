from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from rsh.evidence import (
    build_and_verify,
    verify_parallel,
    write_report_json,
    write_trace_csv,
    write_verify_csv,
)
from rsh.geometry import ModelConfig
from rsh.visual import write_svg


class EvidenceTests(unittest.TestCase):
    def test_report_passes_and_receipt_replays(self) -> None:
        config = ModelConfig(samples=129)
        rows_a, report_a = build_and_verify(config)
        rows_b, report_b = build_and_verify(config)

        self.assertTrue(report_a.pass_all)
        self.assertEqual(report_a.receipt, report_b.receipt)
        self.assertEqual(len(report_a.receipt), 64)
        int(report_a.receipt, 16)
        self.assertEqual(rows_a, rows_b)

    def test_parameter_change_changes_receipt(self) -> None:
        first = build_and_verify(ModelConfig(samples=129, s1=4.0))[1]
        second = build_and_verify(ModelConfig(samples=129, s1=4.5))[1]
        self.assertNotEqual(first.receipt, second.receipt)

    def test_concurrent_replay_parity(self) -> None:
        baseline, reports, parity_ok = verify_parallel(ModelConfig(samples=65), workers=3)
        self.assertTrue(parity_ok)
        self.assertEqual(len(reports), 3)
        self.assertTrue(all(item.receipt == baseline.receipt for item in reports))

    def test_exports_are_created(self) -> None:
        rows, report = build_and_verify(ModelConfig(samples=65))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trace = root / "trace.csv"
            verify = root / "verify.csv"
            report_json = root / "verify.json"
            visual = root / "visual.svg"

            write_trace_csv(rows, trace)
            write_verify_csv(report, verify)
            write_report_json(report, report_json)
            write_svg(rows, visual)

            self.assertTrue(trace.read_text(encoding="utf-8").startswith("p,s,x,y,z"))
            self.assertIn("metric,value", verify.read_text(encoding="utf-8"))
            self.assertEqual(json.loads(report_json.read_text(encoding="utf-8"))["receipt"], report.receipt)
            self.assertIn('data-model="RSH"', visual.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
