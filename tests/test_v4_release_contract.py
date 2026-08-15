from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class V4ReleaseContractTests(unittest.TestCase):
    def test_machine_contracts_and_manifest_align(self) -> None:
        epistemic = json.loads((ROOT / "contracts/rsh-epistemic-v1.json").read_text())
        conformance = json.loads((ROOT / "contracts/rsh-conformance-v1.json").read_text())
        manifest = json.loads((ROOT / "release/manifest-v4.0.0.json").read_text())
        vector = json.loads((ROOT / "conformance/rsh_v4_governance_vector_v1.json").read_text())
        self.assertEqual(epistemic["contract"], "RSH-EPISTEMIC-V1")
        self.assertEqual(conformance["contract"], "RSH-CONFORMANCE-V1")
        self.assertEqual(manifest["release"]["version"], "4.0.0")
        self.assertEqual(manifest["release"]["base_release"], "v3.0.0")
        self.assertEqual(manifest["release"]["base_commit"], "2f9dea41d112539426e1462cbf37c8fcbd5eec01")
        self.assertEqual(manifest["new_contracts"]["epistemic"], epistemic["contract"])
        self.assertEqual(manifest["new_contracts"]["conformance_governance"], conformance["contract"])
        self.assertEqual(vector["contracts"]["epistemic"], epistemic["contract"])
        self.assertEqual(vector["contracts"]["conformance"], conformance["contract"])

    def test_v4_manifest_preserves_software_and_geometry_boundary(self) -> None:
        manifest = json.loads((ROOT / "release/manifest-v4.0.0.json").read_text())
        constants = (ROOT / "src/rsh/constants.py").read_text()
        rust_core = (ROOT / "crates/rsh-core/src/lib.rs").read_text()
        self.assertEqual(manifest["implementation"]["python_package_version"], "4.0.0")
        self.assertEqual(manifest["implementation"]["rust_workspace_version"], "4.0.0")
        self.assertIn('VERSION: str = "2.0.0"', constants)
        self.assertIn('MODEL_VERSION: &str = "2.0.0"', rust_core)

    def test_existing_formal_surface_remains_frozen(self) -> None:
        main_lean = (ROOT / "formal/lean/RSH/Main.lean").read_text()
        lake = (ROOT / "formal/lean/lakefile.toml").read_text()
        self.assertIn('def formalContract : String := "RSH-FORMAL-V1"', main_lean)
        self.assertRegex(lake, r'(?m)^version = "3\.0\.0"$')

    def test_v4_contract_has_no_gluball_implementation(self) -> None:
        manifest = json.loads((ROOT / "release/manifest-v4.0.0.json").read_text())
        deferred = manifest["deferred_gluball"]
        self.assertFalse(deferred["integrated_in_v4_0_0"])
        self.assertEqual(deferred["future_formal_surface"], "RSH-GLUBALL-FORMAL-V1")
        self.assertEqual(deferred["required_gluball_tag_commit"], "80941183d14531093117e122da0fc32c13d2464b")

    def test_release_notes_state_core_claim_boundaries(self) -> None:
        notes = (ROOT / "RELEASE_NOTES_v4.0.0.md").read_text()
        for required in (
            "RSH-EPISTEMIC-V1",
            "RSH-CONFORMANCE-V1",
            "formal syntax is not proof",
            "unknown is not false",
            "no-silent-fallback",
            "RSH-FORMAL-V1",
            "RSH-GLUBALL-FORMAL-V1",
        ):
            self.assertIn(required, notes)

    def test_machine_contract_forbids_text_proof_inference_and_silent_fallback(self) -> None:
        epistemic = json.loads((ROOT / "contracts/rsh-epistemic-v1.json").read_text())
        conformance = json.loads((ROOT / "contracts/rsh-conformance-v1.json").read_text())
        self.assertFalse(epistemic["classification_policy"]["natural_language_proof_inference"])
        self.assertFalse(epistemic["classification_policy"]["keyword_or_regex_proof_detection"])
        self.assertTrue(conformance["runtime_identity"]["no_silent_fallback"])
        self.assertFalse(conformance["receipt"]["wall_clock_in_canonical_identity"])


if __name__ == "__main__":
    unittest.main()
