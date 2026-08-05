#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 Trent Slade / QSOL-IMC.

"""Deterministic exploratory DNA -> ETQ-303 -> MIDI codec for RSH.

This module deliberately defines a separately named exploratory contract. It is
not a biological storage implementation and does not modify the canonical RSH
geometry or ETQ-303 protocol.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Sequence

SCHEMA = "RSH-ETQ-DNA-MIDI-EXPLORATORY-V1"
REPORT_SCHEMA = "RSH-ETQ-DNA-MIDI-REPORT-V1"
MANIFEST_SCHEMA = "RSH-ETQ-DNA-MIDI-MANIFEST-V1"
MIDI_SCHEMA_TEXT = b"RSH-ETQ-DNA-MIDI-EXPLORATORY-V1"

BASES = "ACGT"
BASE_TO_DIGIT = {base: index for index, base in enumerate(BASES)}
CODONS = tuple(a + b + c for a in BASES for b in BASES for c in BASES)
CODON_TO_INDEX = {codon: index for index, codon in enumerate(CODONS)}

ETQ_SITE_COUNT = 101
FIBRE_COUNT = 3
EVENT_COUNT = ETQ_SITE_COUNT * FIBRE_COUNT
SCL_STENCIL = (1, -2, 1)
PHASE_GAUSSIAN_EXPONENTS = (3, 2, 3)
REGISTER_NAMES = ("Low", "Mid", "High")
REGISTER_BASES = (36, 60, 84)
C_MAJOR = (0, 2, 4, 5, 7, 9, 11)

TETRAHEDRON_VERTICES = {
    "A": (0.0, 0.0, 0.0),
    "C": (1.0, 0.0, 0.0),
    "G": (0.5, math.sqrt(3.0) / 2.0, 0.0),
    "T": (0.5, math.sqrt(3.0) / 6.0, math.sqrt(2.0 / 3.0)),
}
TETRAHEDRON_CENTROID = tuple(
    sum(vertex[axis] for vertex in TETRAHEDRON_VERTICES.values()) / 4.0
    for axis in range(3)
)

CLAIMS = {
    "physical_dna_storage_demonstrated": False,
    "biological_error_correction_demonstrated": False,
    "sierpinski_embedding_is_physical_geometry": False,
    "etq_canonical_dna_mapping": False,
    "actual_multi_device_execution": False,
    "distributed_execution": False,
    "geometry_receipt_authority": False,
}

CSV_FIELDS = (
    "base_index",
    "codon_index",
    "codon",
    "codon_offset",
    "base",
    "site_index",
    "fibre_label",
    "event_index",
    "register",
    "midi_channel",
    "midi_pitch",
    "scl_value",
    "phase_gaussian_exponent",
    "x",
    "y",
    "z",
)


def modulo(value: int, modulus: int) -> int:
    if not isinstance(value, int) or not isinstance(modulus, int) or modulus <= 0:
        raise ValueError("modulo requires integers and a positive modulus")
    return ((value % modulus) + modulus) % modulus


def event_index_from_address(site_index: int, fibre_label: int) -> int:
    if not 0 <= site_index < ETQ_SITE_COUNT:
        raise ValueError("site_index must be in [0, 100]")
    if not 0 <= fibre_label < FIBRE_COUNT:
        raise ValueError("fibre_label must be in [0, 2]")
    k = modulo(2 * (fibre_label - modulo(site_index, FIBRE_COUNT)), FIBRE_COUNT)
    event_index = site_index + ETQ_SITE_COUNT * k
    if event_index >= EVENT_COUNT:
        raise AssertionError("CRT inverse escaped ETQ-303 domain")
    return event_index


def event_address(event_index: int) -> tuple[int, int]:
    if not 0 <= event_index < EVENT_COUNT:
        raise ValueError("event_index must be in [0, 302]")
    return event_index % ETQ_SITE_COUNT, event_index % FIBRE_COUNT


def normalize_sequence(sequence: str) -> str:
    if not isinstance(sequence, str):
        raise TypeError("DNA sequence must be text")
    compact = "".join(character for character in sequence.upper() if character.isspace() is False)
    invalid = sorted(set(compact) - set(BASES))
    if invalid:
        raise ValueError(f"DNA sequence contains invalid symbols: {''.join(invalid)}")
    if not compact:
        raise ValueError("DNA sequence must contain at least one codon")
    if len(compact) % 3 != 0:
        raise ValueError("DNA sequence length must be a multiple of 3; incomplete codons are rejected")
    return compact


def codon_index(codon: str) -> int:
    try:
        return CODON_TO_INDEX[codon]
    except KeyError as error:
        raise ValueError(f"invalid codon: {codon!r}") from error


def midi_pitch(site_index: int, fibre_label: int) -> int:
    register = REGISTER_BASES[fibre_label]
    pitch = register + C_MAJOR[site_index % len(C_MAJOR)] + 12 * ((site_index // 7) % 2)
    return max(0, min(127, pitch))


def decimal12(value: float) -> str:
    return f"{value:.12f}"


def tetrahedral_path(sequence: str) -> list[tuple[str, str, str]]:
    point = list(TETRAHEDRON_CENTROID)
    points: list[tuple[str, str, str]] = []
    for base in sequence:
        vertex = TETRAHEDRON_VERTICES[base]
        point = [(point[axis] + vertex[axis]) / 2.0 for axis in range(3)]
        points.append(tuple(decimal12(value) for value in point))
    return points


def encode_records(sequence: str) -> list[dict[str, object]]:
    sequence = normalize_sequence(sequence)
    coordinates = tetrahedral_path(sequence)
    records: list[dict[str, object]] = []
    for base_index, base in enumerate(sequence):
        codon_start = (base_index // 3) * 3
        codon = sequence[codon_start : codon_start + 3]
        site_index = codon_index(codon)
        fibre_label = base_index % 3
        event_index = event_index_from_address(site_index, fibre_label)
        x, y, z = coordinates[base_index]
        records.append(
            {
                "base_index": base_index,
                "codon_index": base_index // 3,
                "codon": codon,
                "codon_offset": fibre_label,
                "base": base,
                "site_index": site_index,
                "fibre_label": fibre_label,
                "event_index": event_index,
                "register": REGISTER_NAMES[fibre_label],
                "midi_channel": fibre_label,
                "midi_pitch": midi_pitch(site_index, fibre_label),
                "scl_value": SCL_STENCIL[fibre_label],
                "phase_gaussian_exponent": PHASE_GAUSSIAN_EXPONENTS[fibre_label],
                "x": x,
                "y": y,
                "z": z,
            }
        )
    return records


def decode_records(records: Sequence[dict[str, object]]) -> str:
    if not records or len(records) % 3 != 0:
        raise ValueError("record count must contain complete codons")
    bases: list[str] = []
    for expected_index, record in enumerate(records):
        base = str(record["base"])
        if base not in BASES:
            raise ValueError("record contains an invalid base")
        site_index = int(record["site_index"])
        fibre_label = int(record["fibre_label"])
        event_index = int(record["event_index"])
        if int(record["base_index"]) != expected_index:
            raise ValueError("record ordering is not canonical")
        if fibre_label != expected_index % 3:
            raise ValueError("record fibre label does not match codon offset")
        if event_index_from_address(site_index, fibre_label) != event_index:
            raise ValueError("record ETQ event index is inconsistent")
        codon = CODONS[site_index]
        if codon[fibre_label] != base:
            raise ValueError("record base does not match codon site and fibre")
        bases.append(base)
    return "".join(bases)


def _vlq(value: int) -> bytes:
    if value < 0:
        raise ValueError("VLQ value must be nonnegative")
    output = bytearray([value & 0x7F])
    value >>= 7
    while value:
        output.append((value & 0x7F) | 0x80)
        value >>= 7
    output.reverse()
    return bytes(output)


def _read_vlq(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    for _ in range(4):
        if offset >= len(data):
            raise ValueError("truncated MIDI VLQ")
        byte = data[offset]
        offset += 1
        value = (value << 7) | (byte & 0x7F)
        if byte & 0x80 == 0:
            return value, offset
    raise ValueError("MIDI VLQ exceeds four bytes")


def create_midi(records: Sequence[dict[str, object]]) -> bytes:
    events: list[tuple[int, int, bytes]] = []
    events.append((0, 0, b"\xFF\x03" + _vlq(len(MIDI_SCHEMA_TEXT)) + MIDI_SCHEMA_TEXT))
    events.append((0, 0, b"\xFF\x51\x03\x07\xA1\x20"))

    for record in records:
        base_index = int(record["base_index"])
        start_tick = base_index * 120
        channel = int(record["midi_channel"])
        site_index = int(record["site_index"])
        base_digit = BASE_TO_DIGIT[str(record["base"])]
        event_index = int(record["event_index"])
        phase = int(record["phase_gaussian_exponent"])
        pitch = int(record["midi_pitch"])
        scl = int(record["scl_value"])
        velocity = 104 if scl < 0 else 82
        duration = 240 if scl < 0 else 180

        controls = (
            (20, site_index),
            (21, base_digit),
            (22, event_index // 128),
            (23, event_index % 128),
            (24, phase),
            (74, 64 if phase == 2 else 96),
        )
        for control, value in controls:
            events.append((start_tick, 2, bytes((0xB0 | channel, control, value))))
        events.append((start_tick, 3, bytes((0x90 | channel, pitch, velocity))))
        events.append((start_tick + duration, 1, bytes((0x80 | channel, pitch, 0))))

    events.sort(key=lambda item: (item[0], item[1], item[2]))
    track = bytearray()
    previous_tick = 0
    for tick, _priority, payload in events:
        track.extend(_vlq(tick - previous_tick))
        track.extend(payload)
        previous_tick = tick
    track.extend(b"\x00\xFF\x2F\x00")

    header = b"MThd" + (6).to_bytes(4, "big") + (0).to_bytes(2, "big") + (1).to_bytes(2, "big") + (480).to_bytes(2, "big")
    return header + b"MTrk" + len(track).to_bytes(4, "big") + bytes(track)


def decode_midi(midi: bytes) -> str:
    if midi[:4] != b"MThd" or len(midi) < 22:
        raise ValueError("not a MIDI file")
    header_length = int.from_bytes(midi[4:8], "big")
    if header_length != 6:
        raise ValueError("unsupported MIDI header length")
    if int.from_bytes(midi[8:10], "big") != 0:
        raise ValueError("only format-0 MIDI is supported")
    if int.from_bytes(midi[10:12], "big") != 1:
        raise ValueError("MIDI must contain exactly one track")
    if int.from_bytes(midi[12:14], "big") != 480:
        raise ValueError("MIDI division must be 480 PPQ")
    track_offset = 8 + header_length
    if midi[track_offset : track_offset + 4] != b"MTrk":
        raise ValueError("MIDI track chunk is missing")
    track_length = int.from_bytes(midi[track_offset + 4 : track_offset + 8], "big")
    track = midi[track_offset + 8 : track_offset + 8 + track_length]
    if len(track) != track_length:
        raise ValueError("truncated MIDI track")

    offset = 0
    absolute_tick = 0
    running_status: int | None = None
    controls = [dict() for _ in range(16)]
    decoded: list[tuple[int, int, int, int, int]] = []
    schema_seen = False

    while offset < len(track):
        delta, offset = _read_vlq(track, offset)
        absolute_tick += delta
        if offset >= len(track):
            raise ValueError("truncated MIDI event")
        status = track[offset]
        if status < 0x80:
            if running_status is None:
                raise ValueError("MIDI running status has no predecessor")
            status = running_status
        else:
            offset += 1
            if status < 0xF0:
                running_status = status

        if status == 0xFF:
            if offset >= len(track):
                raise ValueError("truncated MIDI meta event")
            meta_type = track[offset]
            offset += 1
            length, offset = _read_vlq(track, offset)
            payload = track[offset : offset + length]
            offset += length
            if len(payload) != length:
                raise ValueError("truncated MIDI meta payload")
            if meta_type == 0x03 and payload == MIDI_SCHEMA_TEXT:
                schema_seen = True
            if meta_type == 0x2F:
                break
            continue

        message_type = status & 0xF0
        channel = status & 0x0F
        data_length = 1 if message_type in (0xC0, 0xD0) else 2
        if offset + data_length > len(track):
            raise ValueError("truncated MIDI channel event")
        data1 = track[offset]
        data2 = track[offset + 1] if data_length == 2 else 0
        offset += data_length

        if message_type == 0xB0:
            controls[channel][data1] = data2
        elif message_type == 0x90 and data2 > 0:
            state = controls[channel]
            required = (20, 21, 22, 23)
            if any(control not in state for control in required):
                raise ValueError("MIDI note is missing DNA metadata controls")
            site_index = state[20]
            base_digit = state[21]
            event_index = state[22] * 128 + state[23]
            decoded.append((absolute_tick, channel, site_index, base_digit, event_index))

    if not schema_seen:
        raise ValueError("MIDI schema marker is missing")
    if not decoded or len(decoded) % 3 != 0:
        raise ValueError("MIDI note count does not contain complete codons")

    sequence: list[str] = []
    previous_tick = -1
    for record_index, (tick, fibre_label, site_index, base_digit, event_index) in enumerate(decoded):
        if tick <= previous_tick:
            raise ValueError("MIDI DNA note ordering is not strictly increasing")
        previous_tick = tick
        if fibre_label != record_index % 3:
            raise ValueError("MIDI channel does not match codon offset")
        if not 0 <= site_index < len(CODONS):
            raise ValueError("MIDI codon index is out of range")
        if not 0 <= base_digit < len(BASES):
            raise ValueError("MIDI base digit is out of range")
        if event_index_from_address(site_index, fibre_label) != event_index:
            raise ValueError("MIDI ETQ event index is inconsistent")
        base = BASES[base_digit]
        if CODONS[site_index][fibre_label] != base:
            raise ValueError("MIDI base metadata disagrees with codon site")
        sequence.append(base)
    return "".join(sequence)


def report_for(sequence: str, records: Sequence[dict[str, object]]) -> dict[str, object]:
    return {
        "schema": REPORT_SCHEMA,
        "contract": SCHEMA,
        "input": {
            "dna_sequence": sequence,
            "base_count": len(sequence),
            "codon_count": len(sequence) // 3,
            "alphabet": BASES,
            "incomplete_codon_policy": "reject",
        },
        "etq_mapping": {
            "site_domain": "alphabetic-codon-index-0-to-63-within-etq-site-domain-0-to-100",
            "fibre_semantics": "codon-offset-0-1-2",
            "event_formula": "n=j+101*((2*(a-(j mod 3))) mod 3)",
            "event_count": EVENT_COUNT,
            "scl_stencil": list(SCL_STENCIL),
            "phase_gaussian_exponents": list(PHASE_GAUSSIAN_EXPONENTS),
        },
        "tetrahedral_embedding": {
            "construction": "global-sierpinski-tetrahedron-ifs",
            "recurrence": "p_next=(p_current+vertex(base))/2",
            "initial_point": [decimal12(value) for value in TETRAHEDRON_CENTROID],
            "vertices": {
                base: [decimal12(value) for value in vertex]
                for base, vertex in TETRAHEDRON_VERTICES.items()
            },
            "coordinate_encoding": "fixed-decimal-12",
        },
        "midi": {
            "format": 0,
            "tracks": 1,
            "ppq": 480,
            "tempo_bpm": 120,
            "metadata_controls": {
                "cc20": "codon-site-index",
                "cc21": "base-digit-A0-C1-G2-T3",
                "cc22": "event-index-msb-base128",
                "cc23": "event-index-lsb-base128",
                "cc24": "phase-gaussian-exponent",
                "cc74": "audible-phase-brightness",
            },
        },
        "records": list(records),
        "claims": dict(CLAIMS),
    }


def canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def csv_text(records: Sequence[dict[str, object]]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for record in records:
        writer.writerow({field: record[field] for field in CSV_FIELDS})
    return stream.getvalue()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_artifacts(sequence: str) -> dict[str, object]:
    sequence = normalize_sequence(sequence)
    records = encode_records(sequence)
    if decode_records(records) != sequence:
        raise AssertionError("record round-trip failed")
    midi = create_midi(records)
    if decode_midi(midi) != sequence:
        raise AssertionError("MIDI round-trip failed")
    report = report_for(sequence, records)
    report_canonical = canonical_json(report)
    csv_payload = csv_text(records)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "contract": SCHEMA,
        "sequence_sha256": sha256_hex(sequence.encode("ascii")),
        "report_canonical_sha256": sha256_hex(report_canonical.encode("utf-8")),
        "csv_sha256": sha256_hex(csv_payload.encode("utf-8")),
        "midi_sha256": sha256_hex(midi),
        "record_count": len(records),
        "round_trip_verified": True,
        "claims": dict(CLAIMS),
    }
    return {
        "sequence": sequence,
        "records": records,
        "report": report,
        "report_canonical": report_canonical,
        "csv": csv_payload,
        "midi": midi,
        "manifest": manifest,
    }


def write_artifacts(sequence: str, output_directory: Path) -> dict[str, object]:
    artifacts = build_artifacts(sequence)
    output_directory.mkdir(parents=True, exist_ok=True)
    (output_directory / "report.json").write_text(
        json.dumps(artifacts["report"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_directory / "mapping.csv").write_text(str(artifacts["csv"]), encoding="utf-8")
    (output_directory / "sequence.mid").write_bytes(bytes(artifacts["midi"]))
    (output_directory / "manifest.json").write_text(
        json.dumps(artifacts["manifest"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return artifacts


def verify_profile(profile_path: Path) -> dict[str, object]:
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    if profile.get("schema") != "RSH-ETQ-DNA-MIDI-CONFORMANCE-V1":
        raise ValueError("unexpected conformance profile schema")
    artifacts = build_artifacts(profile["sequence"])
    for key, expected in profile["expected_hashes"].items():
        actual = artifacts["manifest"][key]
        if actual != expected:
            raise AssertionError(f"{key} mismatch: {actual} != {expected}")
    if artifacts["manifest"]["record_count"] != profile["expected_record_count"]:
        raise AssertionError("record count mismatch")
    return artifacts["manifest"]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequence", help="DNA sequence containing A, C, G, and T")
    parser.add_argument("--sequence-file", type=Path, help="read DNA sequence from a text file")
    parser.add_argument("--output", type=Path, help="write report.json, mapping.csv, sequence.mid, and manifest.json")
    parser.add_argument("--verify-profile", type=Path, help="verify a conformance profile and print its manifest")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if arguments.verify_profile:
        manifest = verify_profile(arguments.verify_profile)
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0
    if bool(arguments.sequence) == bool(arguments.sequence_file):
        raise SystemExit("provide exactly one of --sequence or --sequence-file")
    sequence = arguments.sequence if arguments.sequence is not None else arguments.sequence_file.read_text(encoding="utf-8")
    if arguments.output is None:
        artifacts = build_artifacts(sequence)
        print(json.dumps(artifacts["manifest"], indent=2, sort_keys=True))
    else:
        artifacts = write_artifacts(sequence, arguments.output)
        print(json.dumps(artifacts["manifest"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
