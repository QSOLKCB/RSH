# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import json
import sys
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

    def test_fasta_iupac_and_strict_record_boundary(self) -> None:
        record_id, description, sequence = model.parse_fasta(">chr1 description\nacgtryswkmbdhvn\n")
        self.assertEqual((record_id, description), ("chr1", "chr1 description"))
        self.assertEqual(sequence, model.IUPAC_DNA)
        with self.assertRaises(ValueError):
            model.parse_fasta(">one\nACGT\n>two\nACGT\n")
        with self.assertRaises(ValueError):
            model.parse_fasta(">one\nAC-GT\n")

    def test_period_three_and_scl_exact_integer_metrics(self) -> None:
        window = model.analyze_window("ATG" * 4, 0, 0, 12)
        self.assertGreater(window["period3_exact"]["total_scaled_power"], 0)
        self.assertIsInstance(window["period3_exact"]["total_scaled_power"], int)
        self.assertIsInstance(window["scl_exact"]["total_energy"], int)
        self.assertEqual(window["counts"]["ambiguous"], 0)

    def test_vcf_subset_rejects_indels_multiallelic_and_reference_mismatch(self) -> None:
        fasta = ">chr1\nACGTACGTACGT\n"
        _, _, sequence = model.parse_fasta(fasta)
        bad = (
            "##fileformat=VCFv4.5\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
            "chr1\t2\t.\tC\tCA\t.\tPASS\t.\n"
        )
        with self.assertRaises(ValueError):
            model.parse_vcf(bad, "chr1", sequence)
        with self.assertRaises(ValueError):
            model.parse_vcf(bad.replace("CA", "A,G"), "chr1", sequence)
        with self.assertRaises(ValueError):
            model.parse_vcf(bad.replace("C\tCA", "T\tA"), "chr1", sequence)

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

    def test_tampered_profile_fails_closed(self) -> None:
        altered = dict(self.profile)
        altered["expected_hashes"] = dict(altered["expected_hashes"])
        altered["expected_hashes"]["midi_sha256"] = "0" * 64
        temp = ROOT / "conformance" / ".tampered-genomic-profile.json"
        try:
            temp.write_text(json.dumps(altered), encoding="utf-8")
            with self.assertRaises(ValueError):
                model.verify_profile(temp)
        finally:
            temp.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
