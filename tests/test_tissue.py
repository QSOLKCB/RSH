from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import asdict
import io
import json
import math
from pathlib import Path
import platform
import sys
import tempfile
import unittest

from rsh.cli import main
from rsh.constitution import (
    constitution_hash,
    constitution_report,
    validate_constitution,
)
from rsh.refinement import (
    RefinementProposal,
    evaluate_refinement,
    proposal_from_dict,
)
from rsh.tissue import (
    TissueConfig,
    simulate_tissue,
    validate_audit_chain,
    write_tissue_report_json,
    write_tissue_trace_csv,
)

ROOT = Path(__file__).resolve().parents[1]


class ConstitutionTests(unittest.TestCase):
    def test_default_constitution_is_valid_stable_and_isolated(self) -> None:
        expected_hash = (
            "090416435f8ae2adc7555dab356eafef7aadfeabdb99c68e7c381ddf3bf9e544"
        )
        self.assertEqual(validate_constitution(), ())
        self.assertEqual(constitution_hash(), expected_hash)
        report = constitution_report()
        self.assertTrue(report["pass_all"])
        published = json.loads(
            (ROOT / "conformance" / "constitution_v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(report["constitution"], published)
        self.assertIn(
            "subjective-awareness-or-qualia-claim",
            report["constitution"]["refusals"],
        )

        report["constitution"]["invariants"]["psi"] = 0.0
        self.assertEqual(constitution_hash(), expected_hash)
        self.assertTrue(constitution_report()["pass_all"])

    def test_malformed_constitution_is_rejected(self) -> None:
        self.assertEqual(
            validate_constitution([]),
            ("constitution must be a JSON object",),
        )
        report = constitution_report()
        altered = report["constitution"]
        altered["ordered_objectives"] = list(
            reversed(altered["ordered_objectives"])
        )
        self.assertIn(
            "ordered objectives mismatch",
            validate_constitution(altered),
        )


class TissueRuntimeTests(unittest.TestCase):
    def test_default_profile_matches_sealed_conformance(self) -> None:
        profile = json.loads(
            (ROOT / "conformance" / "tissue_v1_8x20.json").read_text(
                encoding="utf-8"
            )
        )
        expected = profile["expected"]
        tolerance = float(expected["observable_absolute_tolerance"])
        report = simulate_tissue()

        self.assertTrue(report.pass_all)
        self.assertTrue(report.audit_chain_valid)
        self.assertTrue(
            validate_audit_chain(
                report.ticks,
                report.seed_geometry_receipt,
            )
        )
        self.assertEqual(
            report.constitution_hash,
            expected["constitution_hash"],
        )
        self.assertEqual(
            report.seed_geometry_receipt,
            expected["seed_geometry_receipt"],
        )

        reference = profile["reference_runtime"]
        on_reference_runtime = (
            platform.python_implementation() == reference["implementation"]
            and sys.version_info[:2]
            == (reference["major"], reference["minor"])
        )
        if on_reference_runtime:
            self.assertEqual(
                report.ticks[0].receipt,
                expected["reference_first_tick_receipt"],
            )
            self.assertEqual(
                report.ticks[-1].receipt,
                expected["reference_last_tick_receipt"],
            )
            self.assertEqual(
                report.receipt,
                expected["reference_report_receipt"],
            )

        observables = (
            (report.ticks[0].metrics.q_f, expected["first_q_f"]),
            (report.final_q_f, expected["final_q_f"]),
            (report.min_q_f, expected["minimum_q_f"]),
            (report.max_q_f, expected["maximum_q_f"]),
            (
                report.ticks[-1].metrics.dissociation,
                expected["final_dissociation"],
            ),
        )
        for actual, reference_value in observables:
            self.assertTrue(
                math.isclose(
                    actual,
                    reference_value,
                    rel_tol=0.0,
                    abs_tol=tolerance,
                ),
                (actual, reference_value),
            )
        self.assertLessEqual(
            max(tick.centre_error for tick in report.ticks),
            expected["maximum_centre_error"],
        )

    def test_replay_is_identical(self) -> None:
        first = simulate_tissue()
        second = simulate_tissue()
        self.assertEqual(first.receipt, second.receipt)
        self.assertEqual(
            [tick.receipt for tick in first.ticks],
            [tick.receipt for tick in second.ticks],
        )
        self.assertEqual(asdict(first), asdict(second))

    def test_sidecar_acceptance_and_fallback_are_explicit(self) -> None:
        accepted = simulate_tissue(
            TissueConfig(
                sidecar_backend="npu",
                sidecar_residual=5.0e-5,
            )
        )
        self.assertTrue(accepted.sidecar_accepted)
        self.assertFalse(accepted.fallback_used)
        self.assertTrue(accepted.pass_all)

        fallback = simulate_tissue(
            TissueConfig(
                sidecar_backend="npu",
                sidecar_residual=1.0e-3,
            )
        )
        self.assertFalse(fallback.sidecar_accepted)
        self.assertTrue(fallback.fallback_used)
        self.assertTrue(fallback.pass_all)
        self.assertLess(fallback.final_q_f, accepted.final_q_f)

    def test_configuration_rejects_unbounded_or_inconsistent_work(self) -> None:
        invalid = (
            TissueConfig(cells=2),
            TissueConfig(ticks=0),
            TissueConfig(cells=4096, ticks=2000),
            TissueConfig(geometry_samples=128),
            TissueConfig(sidecar_backend="none", sidecar_residual=1.0e-8),
            TissueConfig(qf_floor=1.1),
        )
        for config in invalid:
            with self.subTest(config=config):
                with self.assertRaises(ValueError):
                    config.validate()

    def test_json_and_csv_exports_are_complete(self) -> None:
        report = simulate_tissue(TissueConfig(ticks=3))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            json_path = root / "tissue.json"
            csv_path = root / "tissue.csv"
            write_tissue_report_json(report, json_path)
            write_tissue_trace_csv(report, csv_path)
            decoded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(decoded["receipt"], report.receipt)
            lines = csv_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 4)
            self.assertIn("q_f", lines[0])


class RefinementPolicyTests(unittest.TestCase):
    def test_non_escalating_improvement_is_recommended_only(self) -> None:
        proposal = RefinementProposal(
            id="increase-binding-diffusion",
            changes={"binding_diffusion": 0.2},
        )
        decision = evaluate_refinement(proposal)
        self.assertEqual(decision.disposition, "KEEP_CANDIDATE")
        self.assertEqual(decision.reason, "ordered-objectives-improved")
        self.assertTrue(decision.dry_run_only)
        self.assertFalse(decision.human_ack_required)
        self.assertIsNotNone(decision.candidate_receipt)
        self.assertEqual(
            decision.receipt,
            evaluate_refinement(proposal).receipt,
        )

    def test_escalation_requires_declaration_and_acknowledgement(self) -> None:
        undeclared = evaluate_refinement(
            RefinementProposal(
                id="raise-qf-floor",
                changes={"qf_floor": 0.2},
            )
        )
        self.assertEqual(
            undeclared.reason,
            "contract-escalation-not-declared",
        )

        unacknowledged = evaluate_refinement(
            RefinementProposal(
                id="raise-qf-floor",
                changes={"qf_floor": 0.2},
                escalates_contract=True,
            )
        )
        self.assertEqual(unacknowledged.reason, "human-ack-required")

        acknowledged = evaluate_refinement(
            RefinementProposal(
                id="raise-qf-floor",
                changes={"qf_floor": 0.2},
                escalates_contract=True,
                human_ack=True,
            )
        )
        self.assertTrue(acknowledged.human_ack_present)
        self.assertEqual(acknowledged.disposition, "REVERT")
        self.assertEqual(acknowledged.reason, "objectives-not-improved")

    def test_proposal_parser_is_strict(self) -> None:
        with self.assertRaises(ValueError):
            proposal_from_dict(
                {
                    "id": "bad-bool",
                    "changes": {"ticks": 21},
                    "human_ack": "yes",
                }
            )
        with self.assertRaises(ValueError):
            proposal_from_dict(
                {
                    "id": "unknown",
                    "changes": {"source_code": "rewrite"},
                }
            )


class TissueCliTests(unittest.TestCase):
    def test_constitution_tissue_and_refinement_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            constitution_path = root / "constitution.json"
            tissue_path = root / "tissue.json"
            trace_path = root / "tissue.csv"
            proposal_path = root / "proposal.json"
            decision_path = root / "decision.json"
            proposal_path.write_text(
                json.dumps(
                    {
                        "schema": "RSH-REFINEMENT-PROPOSAL-V1",
                        "id": "increase-binding-diffusion",
                        "changes": {"binding_diffusion": 0.2},
                    }
                ),
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(["constitution", "--json", str(constitution_path)]),
                    0,
                )
                self.assertEqual(
                    main(
                        [
                            "tissue",
                            "--ticks",
                            "3",
                            "--json",
                            str(tissue_path),
                            "--trace",
                            str(trace_path),
                        ]
                    ),
                    0,
                )
                self.assertEqual(
                    main(
                        [
                            "refine-dry-run",
                            str(proposal_path),
                            "--json",
                            str(decision_path),
                        ]
                    ),
                    0,
                )

            self.assertTrue(constitution_path.is_file())
            self.assertTrue(tissue_path.is_file())
            self.assertTrue(trace_path.is_file())
            self.assertTrue(decision_path.is_file())
            self.assertIn("RSH tissue [PASS]", output.getvalue())
            decision = json.loads(decision_path.read_text(encoding="utf-8"))
            self.assertEqual(decision["disposition"], "KEEP_CANDIDATE")
            self.assertTrue(decision["dry_run_only"])


if __name__ == "__main__":
    unittest.main()
