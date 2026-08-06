# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import genomic_spectral_etq as model


class GenomicSpectralTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile_path = ROOT / "conformance" / "genomic_spectral_v1_606.json"
        self.profile = json.loads(self.profile_path.read_text(encoding="utf-8"))

    def test_refget_known_answer(self) -> None:
        self.assertEqual(model.refget_accession("ACGT"), "SQ.aKF498dAxcJAqme6QYQ7EZ07-fiw8Kw2")

    def test_etq_position_address_is_bijective_over_one_cycle(self) -> None:
        addresses = [model.etq_address_for_offset(i) for i in range(303)]
        self.assertEqual({entry["event_index"] for entry in addresses}, set(range(303)))
        for entry in addresses:
            self.assertEqual(
                model.event_index_from_address(entry["site_index"], entry["fibre_label"]),
                entry["event_index"],
            )

    def test_fasta_iupac_bounds_and_record_boundary(self) -> None:
        record_id, description, sequence = model.parse_fasta("\n>chr1 description\nacgtryswkmbdhvn\n")
        self.assertEqual((record_id, description), ("chr1", "chr1 description"))
        self.assertEqual(sequence, model.IUPAC_DNA)
        with self.assertRaisesRegex(ValueError, "exactly one"):
            model.parse_fasta(">one\nACGT\n>two\nACGT\n")
        with self.assertRaisesRegex(ValueError, "invalid IUPAC"):
            model.parse_fasta(">one\nAC-GT\n")
        with self.assertRaisesRegex(ValueError, "base safety limit"):
            model.parse_fasta("A" * (model.MAX_SEQUENCE_BASES + 1))

    def test_window_count_and_frame_origin_are_bounded(self) -> None:
        with self.assertRaisesRegex(ValueError, "windows; limit"):
            model.build_windows("A" * 5000, 3, 1)
        with self.assertRaisesRegex(ValueError, "frame origin"):
            model.build_report(">x\nACGTAC\n", frame_origin_1based=99)

    def test_period_three_and_scl_exact_integer_metrics(self) -> None:
        window = model.analyze_window("ATG" * 4, 0, 0, 12)
        self.assertGreater(window["period3_exact"]["total_scaled_power"], 0)
        self.assertIsInstance(window["period3_exact"]["total_scaled_power"], int)
        self.assertIsInstance(window["scl_exact"]["total_energy"], int)
        self.assertEqual(window["counts"]["ambiguous"], 0)
        ambiguous = model.analyze_window("NNN", 0, 0, 3)
        self.assertIsNone(ambiguous["dominant_base"])

    def test_vcf_subset_rejects_invalid_structure_and_overlap(self) -> None:
        fasta = ">chr1\nACGTACGTACGT\n"
        _, _, sequence = model.parse_fasta(fasta)
        header = "##fileformat=VCFv4.5\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        bad = header + "chr1\t2\t.\tC\tCA\t.\tPASS\t.\n"
        with self.assertRaisesRegex(ValueError, "biallelic"):
            model.parse_vcf(bad, "chr1", sequence)
        with self.assertRaisesRegex(ValueError, "fileformat"):
            model.parse_vcf(bad.replace("##fileformat=VCFv4.5\n", ""), "chr1", sequence)
        duplicate = header + "chr1\t2\ta\tC\tA\t.\tPASS\t.\nchr1\t2\tb\tC\tG\t.\tPASS\t.\n"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            model.parse_vcf(duplicate, "chr1", sequence)
        valid = header + "chr1\t2\t.\tC\tA\t.\tPASS\t.\n"
        with self.assertRaisesRegex(ValueError, "non-overlapping"):
            model.build_report(fasta, valid, 6, 3, 1)

    def test_sealed_profile_and_variant_effects(self) -> None:
        actual = model.verify_profile(self.profile_path)
        self.assertEqual(actual, self.profile["expected_hashes"])
        report, *_ = model.build_report(
            self.profile["fasta"], self.profile["vcf"], 303, 303, 1
        )
        self.assertEqual(report["input"]["refget_accession"], self.profile["expected"]["refget_accession"])
        self.assertEqual([v["frame_relative_effect"] for v in report["variants"]], ["stop-gained", "missense"])
        self.assertEqual([v["substitution_class"] for v in report["variants"]], ["transversion", "transition"])
        self.assertEqual(report["claims"], model.CLAIMS)
        self.assertTrue(all(value is False for value in report["claims"].values()))

    def test_profile_contract_claims_and_expected_fields_fail_closed(self) -> None:
        mutations = (
            ("contract", "WRONG", "contract"),
            ("schema", "WRONG", "schema"),
            ("expected_claims", {**model.CLAIMS, "geometry_receipt_authority": True}, "claim"),
            ("expected", {**self.profile["expected"], "window_count": 99}, "window_count"),
        )
        for key, value, message in mutations:
            altered = copy.deepcopy(self.profile)
            altered[key] = value
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "profile.json"
                path.write_text(json.dumps(altered), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    model.verify_profile(path)

    def test_exported_report_bytes_match_manifest(self) -> None:
        report, windows_csv, variants_csv, midi = model.build_report(
            self.profile["fasta"], self.profile["vcf"], 303, 303, 1
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            manifest = model.write_outputs(output, report, windows_csv, variants_csv, midi)
            report_bytes = (output / "report.json").read_bytes()
            self.assertEqual(report_bytes, model.canonical_json_bytes(report))
            self.assertEqual(
                hashlib.sha256(report_bytes).hexdigest(),
                manifest["files"]["report.json"]["sha256"],
            )
            self.assertNotIn(b"\r\n", report_bytes + (output / "windows.csv").read_bytes())


if __name__ == "__main__":
    unittest.main()
