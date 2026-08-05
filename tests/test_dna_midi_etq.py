# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.dna_midi_etq import (
    CLAIMS,
    EVENT_COUNT,
    build_artifacts,
    decode_midi,
    decode_records,
    encode_records,
    event_address,
    event_index_from_address,
    normalize_sequence,
    verify_profile,
)

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "conformance" / "dna_midi_etq_exploratory_v1.json"


def determinant3(a, b, c):
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


def has_rank_three(records):
    points = [(float(row["x"]), float(row["y"]), float(row["z"])) for row in records]
    origin = points[0]
    vectors = [tuple(point[axis] - origin[axis] for axis in range(3)) for point in points[1:]]
    for left in range(len(vectors)):
        for middle in range(left + 1, len(vectors)):
            for right in range(middle + 1, len(vectors)):
                if abs(determinant3(vectors[left], vectors[middle], vectors[right])) > 1e-10:
                    return True
    return False


class DnaMidiEtqTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        self.sequence = self.profile["sequence"]

    def test_crt_event_addresses_are_bijective(self):
        visited = set()
        for event_index in range(EVENT_COUNT):
            site_index, fibre_label = event_address(event_index)
            self.assertEqual(event_index_from_address(site_index, fibre_label), event_index)
            visited.add((site_index, fibre_label))
        self.assertEqual(len(visited), EVENT_COUNT)

    def test_record_and_midi_round_trip(self):
        artifacts = build_artifacts(self.sequence)
        self.assertEqual(decode_records(artifacts["records"]), self.sequence)
        self.assertEqual(decode_midi(artifacts["midi"]), self.sequence)
        self.assertTrue(artifacts["manifest"]["round_trip_verified"])

    def test_cross_runtime_fixture_hashes(self):
        manifest = verify_profile(PROFILE)
        for key, expected in self.profile["expected_hashes"].items():
            self.assertEqual(manifest[key], expected)

    def test_embedding_is_genuinely_three_dimensional_for_fixture(self):
        records = encode_records(self.sequence)
        self.assertTrue(has_rank_three(records))
        self.assertTrue(any(abs(float(record["z"])) > 1e-9 for record in records))

    def test_claim_boundaries_remain_false(self):
        artifacts = build_artifacts(self.sequence)
        self.assertEqual(artifacts["report"]["claims"], CLAIMS)
        self.assertEqual(artifacts["manifest"]["claims"], CLAIMS)
        self.assertTrue(all(value is False for value in CLAIMS.values()))

    def test_invalid_symbols_are_rejected_not_deleted(self):
        with self.assertRaisesRegex(ValueError, "invalid symbols"):
            normalize_sequence("ATG-NNN")

    def test_incomplete_codons_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "multiple of 3"):
            normalize_sequence("ATGC")

    def test_midi_metadata_tampering_is_rejected(self):
        artifacts = build_artifacts(self.sequence)
        midi = bytearray(artifacts["midi"])
        marker = bytes((0xB0, 20, 14))
        index = midi.find(marker)
        self.assertGreater(index, 0)
        midi[index + 2] = 15
        with self.assertRaisesRegex(ValueError, "disagrees|inconsistent"):
            decode_midi(bytes(midi))


if __name__ == "__main__":
    unittest.main()
