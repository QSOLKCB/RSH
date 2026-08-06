# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import copy
import itertools
import json
import random
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.f32_sierpinski_inversive_witness import (
    AXIS_NAMES,
    CLAIMS,
    MAX_WITNESS_COUNT,
    build_bundle,
    radius_squared,
    transform_barycentric,
    validate_witness,
    verify_bundle,
    verify_profile,
    witnesses_for_words,
    word_to_witness,
)

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "conformance" / "f32_sierpinski_inversive_witness_v1.json"


class F32SierpinskiInversiveWitnessTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        self.words = [int(text, 16) for text in self.profile["words_hex"]]
        self.fibres = self.profile["fibre_labels"]

    def test_profile_and_cross_class_fixture(self):
        result = verify_profile(PROFILE)
        self.assertEqual(result["bundle_sha256"], self.profile["expected_bundle_sha256"])
        self.assertEqual(result["claims"], CLAIMS)
        self.assertEqual(result["witness_count"], len(self.words))

    def test_all_axes_are_exact_involutions(self):
        for word in self.words:
            for fibre in range(3):
                witness = word_to_witness(word, fibre)
                self.assertEqual(validate_witness(witness), word)
                self.assertEqual(witness["reflection_axis"], AXIS_NAMES[fibre])
                self.assertTrue(witness["product_invariant_verified"])
                self.assertTrue(witness["double_conjugation_verified"])
                self.assertEqual(
                    witness["squared_radius_product"],
                    {"numerator": "1", "denominator": "9"},
                )
                self.assertEqual(
                    witness["double_application_barycentric"],
                    witness["source_centroid_barycentric"],
                )

    def test_random_word_bundle_round_trip(self):
        randomizer = random.Random(0x5F3759DF)
        words = [randomizer.getrandbits(32) for _ in range(512)]
        fibres = [randomizer.randrange(3) for _ in words]
        bundle = build_bundle(words, fibres)
        self.assertEqual(verify_bundle(bundle), words)

    def test_radius_product_is_circumcircle_invariant(self):
        witness = word_to_witness(0x5F3759DF, 0)
        source = witness["source_centroid_barycentric"]
        conjugate = witness["conjugate_barycentric"]
        source_radius = radius_squared(
            [int(value) for value in source["numerators"]],
            int(source["denominator"]),
        )
        conjugate_radius = radius_squared(
            [int(value) for value in conjugate["numerators"]],
            int(conjugate["denominator"]),
        )
        self.assertEqual(
            source_radius[0] * conjugate_radius[0] * 9,
            source_radius[1] * conjugate_radius[1],
        )

    def test_inversion_centre_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "no finite conjugate"):
            transform_barycentric([1, 1, 1], 3, 0)

    def test_tampering_and_numeric_claims_are_rejected(self):
        witness = word_to_witness(0x3F800000, 2)
        tampered = copy.deepcopy(witness)
        tampered["conjugate_barycentric"]["numerators"][0] = str(
            int(tampered["conjugate_barycentric"]["numerators"][0]) + 1
        )
        with self.assertRaisesRegex(ValueError, "evidence mismatch"):
            validate_witness(tampered)
        tampered = copy.deepcopy(witness)
        tampered["claims"]["geometry_receipt_authority"] = 0
        with self.assertRaisesRegex(ValueError, "claim boundary"):
            validate_witness(tampered)

    def test_word_iterables_are_bounded_before_materialization(self):
        fibres = [0] * MAX_WITNESS_COUNT
        with patch(
            "scripts.f32_sierpinski_inversive_witness.word_to_witness",
            return_value={},
        ):
            with self.assertRaisesRegex(ValueError, str(MAX_WITNESS_COUNT)):
                witnesses_for_words(itertools.repeat(0), fibres)

    def test_quake_lineage_word_remains_data_not_algorithm(self):
        witness = word_to_witness(0x5F3759DF, 0)
        self.assertEqual(witness["word_hex"], "5f3759df")
        self.assertFalse(witness["claims"]["compression_claim"])
        self.assertFalse(witness["claims"]["clawson_quadrilateral_constructed"])


if __name__ == "__main__":
    unittest.main()
