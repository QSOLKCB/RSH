from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "rsh_runner.py"
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsh.constants import KAPPA_MAX
from rsh.reference_spine import (  # noqa: E402
    GAMMASEED_RESTRICTED_V1_HASH,
    SEED_T1,
    admission_certificate,
    build_reference_spine_audit,
    reference_curvature,
    reference_torsion,
    restricted_seed_start,
    sample_reference_spine,
)


class ReferenceSpineTests(unittest.TestCase):
    def test_origin_exceeds_constitutional_curvature_bound(self) -> None:
        self.assertAlmostEqual(
            reference_curvature(0.0),
            0.4755038230472298,
            places=15,
        )
        self.assertGreater(reference_curvature(0.0), KAPPA_MAX)
        self.assertAlmostEqual(
            reference_torsion(0.0),
            0.09549150281252636,
            places=15,
        )

    def test_restricted_start_is_unique_admissible_crossing(self) -> None:
        t_star = restricted_seed_start()
        self.assertAlmostEqual(t_star, 0.04797981890307021, places=14)
        self.assertAlmostEqual(reference_curvature(t_star), KAPPA_MAX, places=12)
        self.assertGreater(reference_curvature(0.5 * t_star), KAPPA_MAX)
        self.assertLess(reference_curvature(2.0 * t_star), KAPPA_MAX)

    def test_full_seed_refuses_and_restricted_seed_admits(self) -> None:
        t_star = restricted_seed_start()
        full = admission_certificate(0.0, SEED_T1)
        restricted = admission_certificate(t_star, SEED_T1)

        self.assertEqual(full.disposition, "REFUSE")
        self.assertFalse(full.admitted)
        self.assertFalse(full.pass_kappa)
        self.assertTrue(full.pass_tau)

        self.assertEqual(restricted.disposition, "ADMIT")
        self.assertTrue(restricted.admitted)
        self.assertTrue(restricted.pass_kappa)
        self.assertTrue(restricted.pass_tau)
        self.assertFalse(restricted.geometry_contract_modified)
        self.assertFalse(restricted.geometry_receipt_authority)

    def test_torsion_stays_inside_open_interval_on_restricted_seed(self) -> None:
        t_star = restricted_seed_start()
        self.assertGreater(reference_torsion(SEED_T1), 0.0)
        self.assertLess(reference_torsion(t_star), 1.0)
        self.assertGreater(reference_torsion(t_star), reference_torsion(SEED_T1))

    def test_receipts_are_deterministic_and_domain_separated(self) -> None:
        point_a = sample_reference_spine(1.0)
        point_b = sample_reference_spine(1.0)
        certificate = admission_certificate(restricted_seed_start(), SEED_T1)
        audit_a = build_reference_spine_audit()
        audit_b = build_reference_spine_audit()

        self.assertEqual(point_a.receipt, point_b.receipt)
        self.assertEqual(audit_a.receipt, audit_b.receipt)
        self.assertEqual(len(point_a.receipt), 64)
        self.assertEqual(len(certificate.receipt), 64)
        self.assertEqual(len(audit_a.receipt), 64)
        self.assertNotEqual(point_a.receipt, certificate.receipt)
        self.assertNotEqual(certificate.receipt, audit_a.receipt)

    def test_audit_binds_frozen_seed_without_promoting_authority(self) -> None:
        audit = build_reference_spine_audit()
        self.assertTrue(audit.pass_all)
        self.assertTrue(audit.pass_full_domain_refusal)
        self.assertTrue(audit.pass_restricted_domain_admission)
        self.assertTrue(audit.pass_unique_curvature_crossing)
        self.assertEqual(audit.source_seed_hash, GAMMASEED_RESTRICTED_V1_HASH)
        self.assertFalse(audit.geometry_contract_modified)
        self.assertFalse(audit.geometry_receipt_authority)
        self.assertTrue(math.isclose(audit.seed_t1, 2.0 * math.pi))

    def test_cli_exports_reference_spine_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            json_path = Path(directory) / "spine_admission.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "spine-admission",
                    "--json",
                    str(json_path),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("RSH reference spine admission [PASS]", result.stdout)
            self.assertIn("full_domain          = REFUSE", result.stdout)
            self.assertIn("restricted_domain    = ADMIT", result.stdout)
            self.assertTrue(json_path.is_file())

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["pass_all"])
            self.assertEqual(payload["full_domain"]["disposition"], "REFUSE")
            self.assertEqual(payload["restricted_domain"]["disposition"], "ADMIT")
            self.assertFalse(payload["geometry_receipt_authority"])


if __name__ == "__main__":
    unittest.main()
