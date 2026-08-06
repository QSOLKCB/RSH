# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import copy
import json
import random
import unittest
from pathlib import Path

from scripts.f32_sierpinski_cell import (
    CLAIMS,
    DEPTH,
    build_bundle,
    classify_word,
    exact_cell_vertices,
    f32_to_word,
    trits_to_word,
    validate_cell,
    verify_bundle,
    verify_profile,
    word_to_cell,
    word_to_trits,
)

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "conformance" / "f32_sierpinski_cell_v1.json"


class F32SierpinskiCellTests(unittest.TestCase):
    def test_capacity_and_exact_round_trip(self):
        words = [
            0x00000000, 0x80000000, 0x00000001, 0x007FFFFF,
            0x00800000, 0x3F800000, 0xBF800000, 0x40490FDB,
            0x5F3759DF, 0x7F7FFFFF, 0x7F800000, 0xFF800000,
            0x7FC00001, 0x7FA00001, 0xFFFFFFFF,
        ]
        for word in words:
            trits = word_to_trits(word)
            self.assertEqual(len(trits), DEPTH)
            self.assertEqual(trits_to_word(trits), word)
            self.assertEqual(validate_cell(word_to_cell(word)), word)

    def test_random_word_round_trip(self):
        randomizer = random.Random(0x5F3759DF)
        words = [randomizer.getrandbits(32) for _ in range(10_000)]
        bundle = build_bundle(words)
        self.assertEqual(verify_bundle(bundle), words)

    def test_exact_cell_vertices_have_power_of_two_denominator(self):
        vertices, denominator = exact_cell_vertices(word_to_trits(0x5F3759DF))
        self.assertEqual(denominator, 1 << DEPTH)
        for vertex in vertices:
            self.assertEqual(sum(vertex), denominator)

    def test_ieee_classification_preserves_payload_classes(self):
        expected = {
            0x00000000: "zero",
            0x80000000: "zero",
            0x00000001: "subnormal",
            0x3F800000: "normal",
            0x7F800000: "infinity",
            0x7FC00001: "quiet-nan",
            0x7FA00001: "signaling-nan",
        }
        for word, classification in expected.items():
            self.assertEqual(classify_word(word), classification)

    def test_quake_magic_word_is_lineage_fixture_not_algorithm(self):
        cell = word_to_cell(0x5F3759DF, field="quake3-lineage-word")
        self.assertEqual(cell["word_hex"], "5f3759df")
        self.assertEqual(trits_to_word(cell["address_trits"]), 0x5F3759DF)
        self.assertFalse(cell["claims"]["compression_claim"])

    def test_tampering_is_rejected(self):
        cell = word_to_cell(0x3F800000)
        tampered = copy.deepcopy(cell)
        tampered["address_trits"] = "2" + tampered["address_trits"][1:]
        with self.assertRaisesRegex(ValueError, "outside|disagree"):
            validate_cell(tampered)
        tampered = copy.deepcopy(cell)
        tampered["cell_vertex_barycentric_numerators"][0][0] += 1
        with self.assertRaisesRegex(ValueError, "vertex evidence"):
            validate_cell(tampered)
        tampered = copy.deepcopy(cell)
        tampered["claims"]["physical_storage_demonstrated"] = True
        with self.assertRaisesRegex(ValueError, "claim boundary"):
            validate_cell(tampered)

    def test_numeric_projection_is_binary32(self):
        self.assertEqual(f32_to_word(1.0), 0x3F800000)
        self.assertEqual(f32_to_word(-0.0), 0x80000000)
        self.assertEqual(f32_to_word(3.141592653589793), 0x40490FDB)

    def test_profile(self):
        result = verify_profile(PROFILE)
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        self.assertEqual(result["bundle_sha256"], profile["expected_bundle_sha256"])
        self.assertEqual(result["claims"], CLAIMS)


if __name__ == "__main__":
    unittest.main()
