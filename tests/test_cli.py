from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "rsh_runner.py"


class CliTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(RUNNER), *arguments],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_info(self) -> None:
        result = self.run_cli("info")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["model"], "Robitaille-Slade-Helix")
        self.assertEqual(payload["version"], "2.0.0")

    def test_verify_and_json_export(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "verify.csv"
            json_path = Path(directory) / "verify.json"
            result = self.run_cli(
                "verify",
                "-n",
                "65",
                "-o",
                str(csv_path),
                "--json",
                str(json_path),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("RSH verify [PASS]", result.stdout)
            self.assertTrue(csv_path.is_file())
            self.assertTrue(json_path.is_file())

    def test_receipt_and_parallel_parity(self) -> None:
        receipt = self.run_cli("receipt", "-n", "65")
        self.assertEqual(receipt.returncode, 0, receipt.stderr)
        self.assertIn("replay_identical=true", receipt.stdout)

        parity = self.run_cli("parity", "-n", "65", "--workers", "2")
        self.assertEqual(parity.returncode, 0, parity.stderr)
        self.assertIn("parity_ok=true", parity.stdout)

    def test_even_sample_count_fails_cleanly(self) -> None:
        result = self.run_cli("verify", "-n", "64")
        self.assertEqual(result.returncode, 2)
        self.assertIn("samples must be odd", result.stderr)


if __name__ == "__main__":
    unittest.main()
