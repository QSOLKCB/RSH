import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "4.1.0"
RSH_V4_COMMIT = "79b8481639fb4187c41035de4e707545db93f59a"
FORMALIZATION_MERGE_COMMIT = "124af8283dd69f78031d3a92249fdd7ea4a60508"
GLUBALL_V1_COMMIT = "80941183d14531093117e122da0fc32c13d2464b"


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_release_versions_are_synchronized():
    assert 'version = "4.1.0"' in _read("pyproject.toml")
    assert '[workspace.package]\nversion = "4.1.0"' in _read("Cargo.toml")
    assert "version: 4.1.0" in _read("CITATION.cff")
    assert "**Release:** 4.1.0" in _read("README.md")

    lock = _read("Cargo.lock")
    local_packages = re.findall(
        r'\[\[package\]\]\nname = "(rsh-[^"]+)"\nversion = "([^"]+)"',
        lock,
    )
    assert local_packages
    assert {version for _, version in local_packages} == {VERSION}


def test_archive_metadata_describes_gluball_formalization():
    zenodo = json.loads(_read(".zenodo.json"))
    assert zenodo["version"] == VERSION
    assert "RSH-GLUBALL-FORMAL-V1" in zenodo["description"]
    assert "RSH-GLUBALL-FORMAL-V1" in zenodo["keywords"]

    citation = _read("CITATION.cff")
    assert "RSH-FORMAL-V1" in citation
    assert "RSH-GLUBALL-FORMAL-V1" in citation


def test_release_manifest_pins_frozen_boundaries():
    manifest = json.loads(_read("release/manifest-v4.1.0.json"))
    assert manifest["release"]["version"] == VERSION
    assert manifest["release"]["tag"] == "v4.1.0"
    assert manifest["release"]["status"] == "release-ready"
    assert manifest["release"]["base_release_commit"] == RSH_V4_COMMIT
    assert manifest["release"]["formalization_merge_commit"] == FORMALIZATION_MERGE_COMMIT
    assert manifest["gluball_source"]["commit"] == GLUBALL_V1_COMMIT
    assert manifest["theorem_surfaces"] == {
        "preserved": "RSH-FORMAL-V1",
        "additive": "RSH-GLUBALL-FORMAL-V1",
    }
    assert manifest["preserved_contracts"]["geometry_model"] == "2.0.0"
    assert manifest["preserved_contracts"]["epistemic_governance"] == "RSH-EPISTEMIC-V1"
    assert manifest["preserved_contracts"]["conformance_governance"] == "RSH-CONFORMANCE-V1"


def test_release_notes_and_readme_expose_additive_surface():
    notes = _read("RELEASE_NOTES_v4.1.0.md")
    readme = _read("README.md")
    assert "RSH-GLUBALL-FORMAL-V1" in notes
    assert FORMALIZATION_MERGE_COMMIT in notes
    assert "RSH-GLUBALL-FORMAL-V1" in readme
    assert "GLUBALL integration" in readme
