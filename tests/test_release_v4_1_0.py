import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "4.1.0"
RSH_V4_COMMIT = "79b8481639fb4187c41035de4e707545db93f59a"
FORMALIZATION_MERGE_COMMIT = "124af8283dd69f78031d3a92249fdd7ea4a60508"
GLUBALL_V1_COMMIT = "80941183d14531093117e122da0fc32c13d2464b"


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class ReleaseV410Test(unittest.TestCase):
    def test_release_versions_are_synchronized(self):
        self.assertIn('version = "4.1.0"', _read("pyproject.toml"))
        self.assertIn('[workspace.package]\nversion = "4.1.0"', _read("Cargo.toml"))
        self.assertIn("version: 4.1.0", _read("CITATION.cff"))
        self.assertIn("**Release:** 4.1.0", _read("README.md"))

        lock = _read("Cargo.lock")
        local_packages = re.findall(
            r'\[\[package\]\]\nname = "(rsh-[^"]+)"\nversion = "([^"]+)"',
            lock,
        )
        self.assertTrue(local_packages)
        self.assertEqual({version for _, version in local_packages}, {VERSION})

    def test_archive_metadata_describes_gluball_formalization(self):
        zenodo = json.loads(_read(".zenodo.json"))
        self.assertEqual(zenodo["version"], VERSION)
        self.assertIn("RSH-GLUBALL-FORMAL-V1", zenodo["description"])
        self.assertIn("RSH-GLUBALL-FORMAL-V1", zenodo["keywords"])

        citation = _read("CITATION.cff")
        self.assertIn("RSH-FORMAL-V1", citation)
        self.assertIn("RSH-GLUBALL-FORMAL-V1", citation)

    def test_release_manifest_pins_frozen_boundaries(self):
        manifest = json.loads(_read("release/manifest-v4.1.0.json"))
        self.assertEqual(manifest["release"]["version"], VERSION)
        self.assertEqual(manifest["release"]["tag"], "v4.1.0")
        self.assertEqual(manifest["release"]["status"], "release-ready")
        self.assertEqual(manifest["release"]["base_release_commit"], RSH_V4_COMMIT)
        self.assertEqual(
            manifest["release"]["formalization_merge_commit"],
            FORMALIZATION_MERGE_COMMIT,
        )
        self.assertEqual(manifest["gluball_source"]["commit"], GLUBALL_V1_COMMIT)
        self.assertEqual(
            manifest["theorem_surfaces"],
            {
                "preserved": "RSH-FORMAL-V1",
                "additive": "RSH-GLUBALL-FORMAL-V1",
            },
        )
        self.assertEqual(manifest["preserved_contracts"]["geometry_model"], "2.0.0")
        self.assertEqual(
            manifest["preserved_contracts"]["epistemic_governance"],
            "RSH-EPISTEMIC-V1",
        )
        self.assertEqual(
            manifest["preserved_contracts"]["conformance_governance"],
            "RSH-CONFORMANCE-V1",
        )

    def test_release_notes_and_readme_expose_additive_surface(self):
        notes = _read("RELEASE_NOTES_v4.1.0.md")
        readme = _read("README.md")
        self.assertIn("RSH-GLUBALL-FORMAL-V1", notes)
        self.assertIn(FORMALIZATION_MERGE_COMMIT, notes)
        self.assertIn("RSH-GLUBALL-FORMAL-V1", readme)
        self.assertIn("GLUBALL integration", readme)


if __name__ == "__main__":
    unittest.main()
