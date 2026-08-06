# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.dna_midi_etq import (
    CLAIMS,
    CODONS,
    EVENT_COUNT,
    MAX_INPUT_CHARACTERS,
    MAX_SEQUENCE_BASES,
    build_artifacts,
    decode_midi,
    decode_records,
    encode_records,
    event_address,
    event_index_from_address,
    normalize_sequence,
    sha256_hex,
    verify_profile,
    write_artifacts,
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


def replace_nth(data: bytearray, pattern: bytes, occurrence: int, replacement: bytes) -> None:
    offset = -1
    cursor = 0
    for _ in range(occurrence + 1):
        offset = data.find(pattern, cursor)
        if offset < 0:
            raise AssertionError(f"pattern {pattern!r} occurrence {occurrence} not found")
        cursor = offset + 1
    data[offset : offset + len(pattern)] = replacement


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

    def test_sequence_and_raw_input_are_bounded(self):
        with self.assertRaisesRegex(ValueError, "base safety limit"):
            normalize_sequence("A" * (MAX_SEQUENCE_BASES + 3))
        with self.assertRaisesRegex(ValueError, "character safety limit"):
            normalize_sequence(" " * (MAX_INPUT_CHARACTERS + 1))

    def test_midi_metadata_tampering_is_rejected(self):
        artifacts = build_artifacts(self.sequence)
        midi = bytearray(artifacts["midi"])
        marker = bytes((0xB0, 20, 14))
        index = midi.find(marker)
        self.assertGreater(index, 0)
        midi[index + 2] = 15
        with self.assertRaisesRegex(ValueError, "disagrees|inconsistent"):
            decode_midi(bytes(midi))

    def test_each_note_requires_fresh_ordered_metadata(self):
        midi = bytearray(build_artifacts("AAAAAA")["midi"])
        replace_nth(midi, bytes((0xB0, 20, 0)), 1, bytes((0xB0, 30, 0)))
        with self.assertRaisesRegex(ValueError, "missing or reordered|fresh"):
            decode_midi(bytes(midi))

    def test_records_and_midi_require_one_site_per_codon(self):
        records = copy.deepcopy(encode_records("AAA"))
        records[1]["site_index"] = 16
        records[1]["codon"] = CODONS[16]
        records[1]["event_index"] = event_index_from_address(16, 1)
        with self.assertRaisesRegex(ValueError, "one site index"):
            decode_records(records)

        midi = bytearray(build_artifacts("AAA")["midi"])
        replace_nth(midi, bytes((0xB1, 20, 0)), 0, bytes((0xB1, 20, 16)))
        replace_nth(midi, bytes((0xB1, 22, 1)), 0, bytes((0xB1, 22, 0)))
        replace_nth(midi, bytes((0xB1, 23, 74)), 0, bytes((0xB1, 23, 16)))
        with self.assertRaisesRegex(ValueError, "one site index"):
            decode_midi(bytes(midi))

    def test_truncated_midi_events_raise_value_error(self):
        header = (
            b"MThd" + (6).to_bytes(4, "big") + (0).to_bytes(2, "big")
            + (1).to_bytes(2, "big") + (480).to_bytes(2, "big")
        )
        for track in (b"\x00", b"\x00\xFF"):
            midi = header + b"MTrk" + len(track).to_bytes(4, "big") + track
            with self.assertRaisesRegex(ValueError, "truncated MIDI"):
                decode_midi(midi)

    def test_profile_contract_and_claims_are_enforced(self):
        for mutation, message in (
            (("contract", "WRONG"), "contract"),
            (("expected_claims", {**CLAIMS, "geometry_receipt_authority": True}), "expected_claims"),
        ):
            altered = copy.deepcopy(self.profile)
            altered[mutation[0]] = mutation[1]
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "profile.json"
                path.write_text(json.dumps(altered), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    verify_profile(path)

    def test_exported_report_bytes_match_manifest_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            artifacts = write_artifacts(self.sequence, output)
            report_bytes = (output / "report.json").read_bytes()
            csv_bytes = (output / "mapping.csv").read_bytes()
            self.assertEqual(
                sha256_hex(report_bytes),
                artifacts["manifest"]["report_canonical_sha256"],
            )
            self.assertEqual(sha256_hex(csv_bytes), artifacts["manifest"]["csv_sha256"])
            self.assertEqual(report_bytes, artifacts["report_canonical"].encode("utf-8"))
            self.assertNotIn(b"\r\n", report_bytes + csv_bytes)


if __name__ == "__main__":
    unittest.main()
