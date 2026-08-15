from __future__ import annotations

import json
from pathlib import Path
import unittest

from rsh.governance import (
    ClaimTier,
    EpistemicState,
    EvidenceClass,
    ExperimentEnvelope,
    RuntimeIdentity,
    RSH_CONFORMANCE_V1,
    adjudicate_claim,
    canonical_experiment_json,
    compare_observables,
    experiment_receipt,
    ledger_digest,
    require_backend,
)

ROOT = Path(__file__).resolve().parents[1]
VECTOR = json.loads((ROOT / "conformance/rsh_v4_governance_vector_v1.json").read_text())


def envelope_from_dict(payload: dict) -> ExperimentEnvelope:
    runtime = payload["runtime"]
    return ExperimentEnvelope(
        contract=payload["contract"],
        experiment=payload["experiment"],
        input_sha256=payload["input_sha256"],
        runtime=RuntimeIdentity(
            backend=runtime["backend"],
            implementation=runtime["implementation"],
            implementation_version=runtime["implementation_version"],
            source_revision=runtime["source_revision"],
            fallback_used=runtime["fallback_used"],
            fallback_from=runtime["fallback_from"],
        ),
        parameters=payload["parameters"],
        seed=payload["seed"],
        observables=payload["observables"],
    )


class GovernanceContractTests(unittest.TestCase):
    def test_sealed_cross_runtime_vector(self) -> None:
        envelope = envelope_from_dict(VECTOR["envelope"])
        self.assertEqual(canonical_experiment_json(envelope), VECTOR["canonical_json"])
        self.assertEqual(experiment_receipt(envelope), VECTOR["expected_receipt"])
        self.assertEqual(ledger_digest(VECTOR["ledger_receipts"]), VECTOR["expected_ledger_digest"])

    def test_claim_vectors(self) -> None:
        for vector in VECTOR["claim_vectors"]:
            with self.subTest(vector=vector["name"]):
                decision = adjudicate_claim(
                    epistemic_state=EpistemicState(vector["epistemic_state"]),
                    evidence_class=EvidenceClass(vector["evidence_class"]),
                    receipt_present=vector["receipt_present"],
                    proof_checked=vector["proof_checked"],
                    measurement_identified=vector["measurement_identified"],
                )
                self.assertEqual(decision.tier, ClaimTier(vector["expected_tier"]))

    def test_non_boolean_evidence_flags_fail_closed(self) -> None:
        for field in ("receipt_present", "proof_checked", "measurement_identified"):
            kwargs = {
                "epistemic_state": EpistemicState.KNOWN,
                "evidence_class": EvidenceClass.PROOF_RECEIPT,
                "receipt_present": True,
                "proof_checked": True,
                "measurement_identified": False,
            }
            kwargs[field] = "false"
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, rf"{field} must be boolean"):
                    adjudicate_claim(**kwargs)

    def test_formal_syntax_is_never_promoted_to_proof(self) -> None:
        decision = adjudicate_claim(
            epistemic_state=EpistemicState.KNOWN,
            evidence_class=EvidenceClass.FORMAL_SYNTAX,
            receipt_present=True,
            proof_checked=True,
        )
        self.assertEqual(decision.tier, ClaimTier.HYPOTHESIS)

    def test_model_output_is_not_execution_evidence(self) -> None:
        decision = adjudicate_claim(
            epistemic_state=EpistemicState.KNOWN,
            evidence_class=EvidenceClass.MODEL_PROPOSAL,
            receipt_present=True,
        )
        self.assertEqual(decision.tier, ClaimTier.PROPOSAL)

    def test_unknown_is_not_false_and_caps_claim_tier(self) -> None:
        decision = adjudicate_claim(
            epistemic_state=EpistemicState.UNKNOWN,
            evidence_class=EvidenceClass.PROOF_RECEIPT,
            receipt_present=True,
            proof_checked=True,
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.tier, ClaimTier.HYPOTHESIS)
        self.assertIn("unknown-is-not-false", decision.reason)

    def test_conflict_fails_closed(self) -> None:
        decision = adjudicate_claim(
            epistemic_state=EpistemicState.CONFLICT,
            evidence_class=EvidenceClass.PROOF_RECEIPT,
            receipt_present=True,
            proof_checked=True,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.tier, ClaimTier.BLOCKED)

    def test_runtime_identity_requires_explicit_fallback(self) -> None:
        with self.assertRaisesRegex(ValueError, "fallback_used=true"):
            RuntimeIdentity(
                backend="python-reference",
                implementation="rsh-geometry",
                implementation_version="4.0.0",
                source_revision="fixture",
                fallback_used=True,
                fallback_from=None,
            ).validate()

    def test_declared_fallback_is_rejected_by_default(self) -> None:
        payload = json.loads(json.dumps(VECTOR["envelope"]))
        payload["runtime"]["backend"] = "python-reference"
        payload["runtime"]["fallback_used"] = True
        payload["runtime"]["fallback_from"] = "cuda"
        envelope = envelope_from_dict(payload)
        with self.assertRaisesRegex(ValueError, "declared fallback"):
            require_backend(envelope, "python-reference")
        require_backend(envelope, "python-reference", allow_declared_fallback=True)

    def test_backend_mismatch_fails_closed(self) -> None:
        envelope = envelope_from_dict(VECTOR["envelope"])
        with self.assertRaisesRegex(ValueError, "backend mismatch"):
            require_backend(envelope, "cuda")

    def test_portable_observables_may_match_while_receipts_differ(self) -> None:
        a = envelope_from_dict(VECTOR["envelope"])
        runtime = RuntimeIdentity(
            backend="rust-native",
            implementation="rsh-governance",
            implementation_version="4.0.0",
            source_revision="fixture-v4.0.0",
        )
        b = ExperimentEnvelope(
            contract=RSH_CONFORMANCE_V1,
            experiment=a.experiment,
            input_sha256=a.input_sha256,
            runtime=runtime,
            parameters=a.parameters,
            seed=a.seed,
            observables=a.observables,
        )
        self.assertTrue(compare_observables(a, b))
        self.assertNotEqual(experiment_receipt(a), experiment_receipt(b))

    def test_receipt_has_no_wall_clock_field(self) -> None:
        envelope = envelope_from_dict(VECTOR["envelope"])
        canonical = canonical_experiment_json(envelope)
        self.assertNotIn("timestamp", canonical.lower())
        self.assertNotIn("time_ns", canonical.lower())

    def test_invalid_receipt_ledger_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            ledger_digest(["not-a-receipt"])


if __name__ == "__main__":
    unittest.main()
