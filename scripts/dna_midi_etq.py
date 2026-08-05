#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# SPDX-License-Identifier: MPL-2.0
"""Bounded exploratory DNA -> ETQ-303 address -> MIDI codec for RSH."""
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
MIDI_SCHEMA_TEXT = SCHEMA.encode("ascii")
BASES = "ACGT"
BASE_TO_DIGIT = {base: index for index, base in enumerate(BASES)}
CODONS = tuple(a + b + c for a in BASES for b in BASES for c in BASES)
CODON_TO_INDEX = {codon: index for index, codon in enumerate(CODONS)}
ETQ_SITE_COUNT, FIBRE_COUNT, EVENT_COUNT = 101, 3, 303
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
    "base_index", "codon_index", "codon", "codon_offset", "base", "site_index",
    "fibre_label", "event_index", "register", "midi_channel", "midi_pitch",
    "scl_value", "phase_gaussian_exponent", "x", "y", "z",
)


def modulo(value: int, modulus: int) -> int:
    if not isinstance(value, int) or not isinstance(modulus, int) or modulus <= 0:
        raise ValueError("modulo requires integers and a positive modulus")
    return value % modulus


def event_index_from_address(site_index: int, fibre_label: int) -> int:
    if not 0 <= site_index < ETQ_SITE_COUNT:
        raise ValueError("site_index must be in [0, 100]")
    if not 0 <= fibre_label < FIBRE_COUNT:
        raise ValueError("fibre_label must be in [0, 2]")
    return site_index + ETQ_SITE_COUNT * modulo(2 * (fibre_label - site_index % 3), 3)


def event_address(event_index: int) -> tuple[int, int]:
    if not 0 <= event_index < EVENT_COUNT:
        raise ValueError("event_index must be in [0, 302]")
    return event_index % ETQ_SITE_COUNT, event_index % FIBRE_COUNT


def normalize_sequence(sequence: str) -> str:
    if not isinstance(sequence, str):
        raise TypeError("DNA sequence must be text")
    compact = "".join(character for character in sequence.upper() if not character.isspace())
    invalid = sorted(set(compact) - set(BASES))
    if invalid:
        raise ValueError(f"DNA sequence contains invalid symbols: {''.join(invalid)}")
    if not compact:
        raise ValueError("DNA sequence must contain at least one codon")
    if len(compact) % 3:
        raise ValueError("DNA sequence length must be a multiple of 3; incomplete codons are rejected")
    return compact


def midi_pitch(site_index: int, fibre_label: int) -> int:
    pitch = REGISTER_BASES[fibre_label] + C_MAJOR[site_index % 7] + 12 * ((site_index // 7) % 2)
    return min(127, max(0, pitch))


def _decimal12(value: float) -> str:
    return f"{value:.12f}"


def tetrahedral_path(sequence: str) -> list[tuple[str, str, str]]:
    point = list(TETRAHEDRON_CENTROID)
    output = []
    for base in sequence:
        vertex = TETRAHEDRON_VERTICES[base]
        point = [(point[axis] + vertex[axis]) / 2.0 for axis in range(3)]
        output.append(tuple(_decimal12(value) for value in point))
    return output


def encode_records(sequence: str) -> list[dict[str, object]]:
    sequence = normalize_sequence(sequence)
    coordinates = tetrahedral_path(sequence)
    records = []
    for base_index, base in enumerate(sequence):
        codon_index = base_index // 3
        fibre_label = base_index % 3
        codon = sequence[codon_index * 3 : codon_index * 3 + 3]
        site_index = CODON_TO_INDEX[codon]
        x, y, z = coordinates[base_index]
        records.append({
            "base_index": base_index,
            "codon_index": codon_index,
            "codon": codon,
            "codon_offset": fibre_label,
            "base": base,
            "site_index": site_index,
            "fibre_label": fibre_label,
            "event_index": event_index_from_address(site_index, fibre_label),
            "register": REGISTER_NAMES[fibre_label],
            "midi_channel": fibre_label,
            "midi_pitch": midi_pitch(site_index, fibre_label),
            "scl_value": SCL_STENCIL[fibre_label],
            "phase_gaussian_exponent": PHASE_GAUSSIAN_EXPONENTS[fibre_label],
            "x": x, "y": y, "z": z,
        })
    return records


def decode_records(records: Sequence[dict[str, object]]) -> str:
    if not records or len(records) % 3:
        raise ValueError("record count must contain complete codons")
    decoded = []
    for index, record in enumerate(records):
        base = str(record["base"])
        site = int(record["site_index"])
        fibre = int(record["fibre_label"])
        event = int(record["event_index"])
        if base not in BASES:
            raise ValueError("record contains an invalid base")
        if int(record["base_index"]) != index:
            raise ValueError("record ordering is not canonical")
        if fibre != index % 3:
            raise ValueError("record fibre label does not match codon offset")
        if event_index_from_address(site, fibre) != event:
            raise ValueError("record ETQ event index is inconsistent")
        if CODONS[site][fibre] != base:
            raise ValueError("record base does not match codon site and fibre")
        decoded.append(base)
    return "".join(decoded)


def _vlq(value: int) -> bytes:
    if value < 0:
        raise ValueError("VLQ value must be nonnegative")
    output = bytearray([value & 0x7F])
    value >>= 7
    while value:
        output.insert(0, (value & 0x7F) | 0x80)
        value >>= 7
    return bytes(output)


def _read_vlq(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    for _ in range(4):
        if offset >= len(data):
            raise ValueError("truncated MIDI VLQ")
        byte = data[offset]
        offset += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, offset
    raise ValueError("MIDI VLQ exceeds four bytes")


def create_midi(records: Sequence[dict[str, object]]) -> bytes:
    events: list[tuple[int, int, bytes]] = [
        (0, 0, b"\xFF\x03" + _vlq(len(MIDI_SCHEMA_TEXT)) + MIDI_SCHEMA_TEXT),
        (0, 0, b"\xFF\x51\x03\x07\xA1\x20"),
    ]
    for record in records:
        start = int(record["base_index"]) * 120
        channel = int(record["midi_channel"])
        site = int(record["site_index"])
        event = int(record["event_index"])
        phase = int(record["phase_gaussian_exponent"])
        pitch = int(record["midi_pitch"])
        scl = int(record["scl_value"])
        controls = (
            (20, site), (21, BASE_TO_DIGIT[str(record["base"])]),
            (22, event // 128), (23, event % 128), (24, phase),
            (74, 64 if phase == 2 else 96),
        )
        events.extend((start, 2, bytes((0xB0 | channel, control, value))) for control, value in controls)
        events.append((start, 3, bytes((0x90 | channel, pitch, 104 if scl < 0 else 82))))
        events.append((start + (240 if scl < 0 else 180), 1, bytes((0x80 | channel, pitch, 0))))
    events.sort(key=lambda item: (item[0], item[1], item[2]))
    track, previous = bytearray(), 0
    for tick, _, payload in events:
        track.extend(_vlq(tick - previous))
        track.extend(payload)
        previous = tick
    track.extend(b"\x00\xFF\x2F\x00")
    header = b"MThd" + (6).to_bytes(4, "big") + (0).to_bytes(2, "big") + (1).to_bytes(2, "big") + (480).to_bytes(2, "big")
    return header + b"MTrk" + len(track).to_bytes(4, "big") + bytes(track)


def decode_midi(midi: bytes) -> str:
    if len(midi) < 22 or midi[:4] != b"MThd":
        raise ValueError("not a MIDI file")
    header_length = int.from_bytes(midi[4:8], "big")
    if header_length != 6 or int.from_bytes(midi[8:10], "big") != 0:
        raise ValueError("only format-0 MIDI is supported")
    if int.from_bytes(midi[10:12], "big") != 1 or int.from_bytes(midi[12:14], "big") != 480:
        raise ValueError("MIDI must contain one 480-PPQ track")
    offset = 8 + header_length
    if midi[offset:offset + 4] != b"MTrk":
        raise ValueError("MIDI track chunk is missing")
    length = int.from_bytes(midi[offset + 4:offset + 8], "big")
    track = midi[offset + 8:offset + 8 + length]
    if len(track) != length:
        raise ValueError("truncated MIDI track")
    offset = tick = 0
    running = None
    controls = [dict() for _ in range(16)]
    notes = []
    schema_seen = False
    while offset < len(track):
        delta, offset = _read_vlq(track, offset)
        tick += delta
        status = track[offset]
        if status < 0x80:
            if running is None:
                raise ValueError("MIDI running status has no predecessor")
            status = running
        else:
            offset += 1
            if status < 0xF0:
                running = status
        if status == 0xFF:
            meta_type = track[offset]
            offset += 1
            size, offset = _read_vlq(track, offset)
            payload = track[offset:offset + size]
            offset += size
            if len(payload) != size:
                raise ValueError("truncated MIDI meta payload")
            schema_seen |= meta_type == 0x03 and payload == MIDI_SCHEMA_TEXT
            if meta_type == 0x2F:
                break
            continue
        kind, channel = status & 0xF0, status & 0x0F
        size = 1 if kind in (0xC0, 0xD0) else 2
        if offset + size > len(track):
            raise ValueError("truncated MIDI channel event")
        first, second = track[offset], track[offset + 1] if size == 2 else 0
        offset += size
        if kind == 0xB0:
            controls[channel][first] = second
        elif kind == 0x90 and second > 0:
            state = controls[channel]
            if any(control not in state for control in (20, 21, 22, 23)):
                raise ValueError("MIDI note is missing DNA metadata controls")
            notes.append((tick, channel, state[20], state[21], state[22] * 128 + state[23]))
    if not schema_seen:
        raise ValueError("MIDI schema marker is missing")
    if not notes or len(notes) % 3:
        raise ValueError("MIDI note count does not contain complete codons")
    decoded, previous = [], -1
    for index, (tick, fibre, site, digit, event) in enumerate(notes):
        if tick <= previous:
            raise ValueError("MIDI DNA note ordering is not strictly increasing")
        previous = tick
        if fibre != index % 3:
            raise ValueError("MIDI channel does not match codon offset")
        if not 0 <= site < len(CODONS) or not 0 <= digit < len(BASES):
            raise ValueError("MIDI DNA metadata is out of range")
        if event_index_from_address(site, fibre) != event:
            raise ValueError("MIDI ETQ event index is inconsistent")
        base = BASES[digit]
        if CODONS[site][fibre] != base:
            raise ValueError("MIDI base metadata disagrees with codon site")
        decoded.append(base)
    return "".join(decoded)


def report_for(sequence: str, records: Sequence[dict[str, object]]) -> dict[str, object]:
    return {
        "schema": REPORT_SCHEMA,
        "contract": SCHEMA,
        "input": {
            "dna_sequence": sequence, "base_count": len(sequence),
            "codon_count": len(sequence) // 3, "alphabet": BASES,
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
            "initial_point": [_decimal12(value) for value in TETRAHEDRON_CENTROID],
            "vertices": {base: [_decimal12(value) for value in vertex] for base, vertex in TETRAHEDRON_VERTICES.items()},
            "coordinate_encoding": "fixed-decimal-12",
        },
        "midi": {
            "format": 0, "tracks": 1, "ppq": 480, "tempo_bpm": 120,
            "metadata_controls": {
                "cc20": "codon-site-index", "cc21": "base-digit-A0-C1-G2-T3",
                "cc22": "event-index-msb-base128", "cc23": "event-index-lsb-base128",
                "cc24": "phase-gaussian-exponent", "cc74": "audible-phase-brightness",
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
    writer.writerows({field: record[field] for field in CSV_FIELDS} for record in records)
    return stream.getvalue()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_artifacts(sequence: str) -> dict[str, object]:
    sequence = normalize_sequence(sequence)
    records = encode_records(sequence)
    midi = create_midi(records)
    if decode_records(records) != sequence or decode_midi(midi) != sequence:
        raise AssertionError("codec round-trip failed")
    report = report_for(sequence, records)
    canonical = canonical_json(report)
    csv_payload = csv_text(records)
    manifest = {
        "schema": MANIFEST_SCHEMA, "contract": SCHEMA,
        "sequence_sha256": sha256_hex(sequence.encode("ascii")),
        "report_canonical_sha256": sha256_hex(canonical.encode()),
        "csv_sha256": sha256_hex(csv_payload.encode()),
        "midi_sha256": sha256_hex(midi),
        "record_count": len(records), "round_trip_verified": True,
        "claims": dict(CLAIMS),
    }
    return {"sequence": sequence, "records": records, "report": report, "report_canonical": canonical, "csv": csv_payload, "midi": midi, "manifest": manifest}


def write_artifacts(sequence: str, output_directory: Path) -> dict[str, object]:
    artifacts = build_artifacts(sequence)
    output_directory.mkdir(parents=True, exist_ok=True)
    (output_directory / "report.json").write_text(json.dumps(artifacts["report"], indent=2, sort_keys=True) + "\n")
    (output_directory / "mapping.csv").write_text(str(artifacts["csv"]))
    (output_directory / "sequence.mid").write_bytes(bytes(artifacts["midi"]))
    (output_directory / "manifest.json").write_text(json.dumps(artifacts["manifest"], indent=2, sort_keys=True) + "\n")
    return artifacts


def verify_profile(profile_path: Path) -> dict[str, object]:
    profile = json.loads(profile_path.read_text())
    if profile.get("schema") != "RSH-ETQ-DNA-MIDI-CONFORMANCE-V1":
        raise ValueError("unexpected conformance profile schema")
    manifest = build_artifacts(profile["sequence"])["manifest"]
    for key, expected in profile["expected_hashes"].items():
        if manifest[key] != expected:
            raise AssertionError(f"{key} mismatch: {manifest[key]} != {expected}")
    if manifest["record_count"] != profile["expected_record_count"]:
        raise AssertionError("record count mismatch")
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequence")
    parser.add_argument("--sequence-file", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-profile", type=Path)
    args = parser.parse_args(argv)
    if args.verify_profile:
        print(json.dumps(verify_profile(args.verify_profile), indent=2, sort_keys=True))
        return 0
    if bool(args.sequence) == bool(args.sequence_file):
        raise SystemExit("provide exactly one of --sequence or --sequence-file")
    sequence = args.sequence if args.sequence is not None else args.sequence_file.read_text()
    artifacts = write_artifacts(sequence, args.output) if args.output else build_artifacts(sequence)
    print(json.dumps(artifacts["manifest"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
