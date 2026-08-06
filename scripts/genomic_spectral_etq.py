#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# SPDX-License-Identifier: MPL-2.0
"""Deterministic genomic-window, ETQ-address, spectral, and SNV evidence tooling."""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Sequence

CONTRACT = "RSH-ETQ-GENOMIC-SPECTRAL-V1"
REPORT_SCHEMA = "RSH-ETQ-GENOMIC-SPECTRAL-REPORT-V1"
MANIFEST_SCHEMA = "RSH-ETQ-GENOMIC-SPECTRAL-MANIFEST-V1"
PROFILE_SCHEMA = "RSH-ETQ-GENOMIC-SPECTRAL-CONFORMANCE-V1"
MIDI_SCHEMA_TEXT = CONTRACT.encode("ascii")
CANONICAL_BASES = "ACGT"
IUPAC_DNA = "ACGTRYSWKMBDHVN"
ETQ_SITE_COUNT = 101
FIBRE_COUNT = 3
EVENT_COUNT = 303
MAX_FASTA_CHARACTERS = 2_000_000
MAX_SEQUENCE_BASES = 1_000_000
MAX_VCF_CHARACTERS = 2_000_000
MAX_WINDOW_COUNT = 4_096
MAX_VARIANT_COUNT = 4_096
SCL_STENCIL = (1, -2, 1)
PERIOD3_RE2_WEIGHTS = (2, -1, -1)
PERIOD3_IM_WEIGHTS = (0, 1, -1)
REGISTER_NAMES = ("Low", "Mid", "High")
REGISTER_BASES = (36, 60, 84)
C_MAJOR = (0, 2, 4, 5, 7, 9, 11)
COMPLEMENT = str.maketrans("ACGTRYSWKMBDHVN", "TGCAYRSWMKVHDBN")
DINUCLEOTIDES = tuple(a + b for a in CANONICAL_BASES for b in CANONICAL_BASES)
TRINUCLEOTIDES = tuple(a + b + c for a in CANONICAL_BASES for b in CANONICAL_BASES for c in CANONICAL_BASES)
TRANSITIONS = {("A", "G"), ("G", "A"), ("C", "T"), ("T", "C")}
STANDARD_CODE = {
    "TTT":"F","TTC":"F","TTA":"L","TTG":"L","TCT":"S","TCC":"S","TCA":"S","TCG":"S",
    "TAT":"Y","TAC":"Y","TAA":"*","TAG":"*","TGT":"C","TGC":"C","TGA":"*","TGG":"W",
    "CTT":"L","CTC":"L","CTA":"L","CTG":"L","CCT":"P","CCC":"P","CCA":"P","CCG":"P",
    "CAT":"H","CAC":"H","CAA":"Q","CAG":"Q","CGT":"R","CGC":"R","CGA":"R","CGG":"R",
    "ATT":"I","ATC":"I","ATA":"I","ATG":"M","ACT":"T","ACC":"T","ACA":"T","ACG":"T",
    "AAT":"N","AAC":"N","AAA":"K","AAG":"K","AGT":"S","AGC":"S","AGA":"R","AGG":"R",
    "GTT":"V","GTC":"V","GTA":"V","GTG":"V","GCT":"A","GCC":"A","GCA":"A","GCG":"A",
    "GAT":"D","GAC":"D","GAA":"E","GAG":"E","GGT":"G","GGC":"G","GGA":"G","GGG":"G",
}
CLAIMS = {
    "actual_multi_device_execution": False,
    "biological_function_inferred": False,
    "clinical_variant_interpretation": False,
    "coding_region_annotation_authority": False,
    "distributed_execution": False,
    "etq_canonical_genomic_mapping": False,
    "gene_prediction_demonstrated": False,
    "geometry_receipt_authority": False,
    "physical_dna_storage_demonstrated": False,
    "spectral_feature_is_diagnostic": False,
}
WINDOW_CSV_FIELDS = (
    "window_index", "start_1based", "end_1based_inclusive", "length", "callable_bases",
    "ambiguous_bases", "a_count", "c_count", "g_count", "t_count", "gc_numerator",
    "gc_denominator", "cpg_count", "period3_scaled_power", "scl_energy", "dominant_base",
    "etq_site", "etq_fibre", "etq_event", "midi_channel", "midi_pitch", "midi_velocity",
    "midi_brightness", "midi_scl_controller",
)
VARIANT_CSV_FIELDS = (
    "chrom", "position_1based", "id", "ref", "alt", "substitution_class", "context_3mer",
    "etq_site", "etq_fibre", "etq_event", "window_index", "period3_scaled_power_delta",
    "scl_energy_delta", "gc_count_delta", "cpg_count_delta", "reference_codon", "alternate_codon",
    "reference_amino_acid", "alternate_amino_acid", "frame_relative_effect",
)


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def refget_accession(sequence: str) -> str:
    digest = hashlib.sha512(sequence.encode("ascii")).digest()[:24]
    return "SQ." + base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _trim_blank_edges(lines: list[str]) -> list[str]:
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def parse_fasta(text: str) -> tuple[str, str, str]:
    if not isinstance(text, str):
        raise TypeError("FASTA input must be text")
    if len(text) > MAX_FASTA_CHARACTERS:
        raise ValueError(f"FASTA input exceeds the {MAX_FASTA_CHARACTERS}-character safety limit")
    lines = _trim_blank_edges(text.splitlines())
    headers = [index for index, line in enumerate(lines) if line.startswith(">")]
    if len(headers) > 1:
        raise ValueError("exactly one FASTA record is supported")
    if headers:
        if headers[0] != 0:
            raise ValueError("FASTA definition line must be the first nonempty content")
        header = lines[0][1:].strip()
        if not header:
            raise ValueError("FASTA definition line must contain an identifier")
        record_id = header.split()[0]
        description = header
        sequence_lines = lines[1:]
    else:
        record_id = "sequence"
        description = "sequence"
        sequence_lines = lines
    sequence = "".join(character for line in sequence_lines for character in line.upper() if not character.isspace())
    if not sequence:
        raise ValueError("sequence must not be empty")
    if len(sequence) > MAX_SEQUENCE_BASES:
        raise ValueError(f"sequence exceeds the {MAX_SEQUENCE_BASES}-base safety limit")
    invalid = sorted(set(sequence) - set(IUPAC_DNA))
    if invalid:
        raise ValueError(f"sequence contains invalid IUPAC DNA symbols: {''.join(invalid)}")
    return record_id, description, sequence


def strand_complement(sequence: str) -> str:
    return sequence.translate(COMPLEMENT)[::-1]


def event_index_from_address(site_index: int, fibre_label: int) -> int:
    if not 0 <= site_index < ETQ_SITE_COUNT:
        raise ValueError("site_index must be in [0, 100]")
    if not 0 <= fibre_label < FIBRE_COUNT:
        raise ValueError("fibre_label must be in [0, 2]")
    return site_index + ETQ_SITE_COUNT * ((2 * (fibre_label - site_index % 3)) % 3)


def etq_address_for_offset(offset0: int) -> dict[str, int]:
    if offset0 < 0:
        raise ValueError("offset must be nonnegative")
    event = offset0 % EVENT_COUNT
    site, fibre = event % ETQ_SITE_COUNT, event % FIBRE_COUNT
    if event_index_from_address(site, fibre) != event:
        raise AssertionError("ETQ CRT address invariant failed")
    return {"site_index": site, "fibre_label": fibre, "event_index": event}


def count_kmers(sequence: str, k: int, vocabulary: Sequence[str]) -> tuple[dict[str, int], int]:
    counts = {word: 0 for word in vocabulary}
    valid = 0
    for index in range(max(0, len(sequence) - k + 1)):
        word = sequence[index:index + k]
        if all(base in CANONICAL_BASES for base in word):
            counts[word] += 1
            valid += 1
    return counts, valid


def period3_channel(sequence: str, base: str) -> dict[str, int]:
    re2 = 0
    im = 0
    for index, symbol in enumerate(sequence):
        if symbol == base:
            phase = index % 3
            re2 += PERIOD3_RE2_WEIGHTS[phase]
            im += PERIOD3_IM_WEIGHTS[phase]
    return {"re2": re2, "im_sqrt3_coefficient": im, "scaled_power": re2 * re2 + 3 * im * im}


def scl_channel_energy(sequence: str, base: str) -> int:
    values = [1 if symbol == base else 0 for symbol in sequence]
    return sum((values[index] - 2 * values[index + 1] + values[index + 2]) ** 2 for index in range(max(0, len(values) - 2)))


def midi_pitch(site_index: int, fibre_label: int) -> int:
    pitch = REGISTER_BASES[fibre_label] + C_MAJOR[site_index % 7] + 12 * ((site_index // 7) % 2)
    return min(127, max(0, pitch))


def _fraction(numerator: int, denominator: int) -> dict[str, int]:
    return {"numerator": numerator, "denominator": denominator}


def analyze_window(sequence: str, window_index: int, start0: int, end0: int) -> dict[str, object]:
    window = sequence[start0:end0]
    counts = {base: window.count(base) for base in CANONICAL_BASES}
    callable_count = sum(counts.values())
    ambiguous_count = len(window) - callable_count
    dinucleotides, valid_dinucleotides = count_kmers(window, 2, DINUCLEOTIDES)
    trinucleotides, valid_trinucleotides = count_kmers(window, 3, TRINUCLEOTIDES)
    period3 = {base: period3_channel(window, base) for base in CANONICAL_BASES}
    scl = {base: scl_channel_energy(window, base) for base in CANONICAL_BASES}
    period3_total = sum(int(channel["scaled_power"]) for channel in period3.values())
    scl_total = sum(scl.values())
    max_count = max(counts.values()) if callable_count else 0
    dominant = next((base for base in CANONICAL_BASES if counts[base] == max_count), None) if callable_count else None
    address = etq_address_for_offset(start0)
    gc_count = counts["G"] + counts["C"]
    gc_denominator = callable_count
    velocity = min(127, 32 + math.isqrt(period3_total))
    brightness = 0 if gc_denominator == 0 else (127 * gc_count) // gc_denominator
    scl_controller = min(127, math.isqrt(scl_total * 16))
    receiver = {
        "register": REGISTER_NAMES[address["fibre_label"]],
        "midi_channel": address["fibre_label"],
        "midi_pitch": midi_pitch(address["site_index"], address["fibre_label"]),
        "midi_velocity": velocity,
        "midi_brightness_cc74": brightness,
        "midi_scl_cc71": scl_controller,
        "duration_ticks": 120 + min(840, dinucleotides["CG"] * 30 + ambiguous_count * 10),
    }
    return {
        "window_index": window_index,
        "start_1based": start0 + 1,
        "end_1based_inclusive": end0,
        "length": len(window),
        "sequence_sha256": sha256_hex(window.encode("ascii")),
        "counts": {**counts, "ambiguous": ambiguous_count, "callable": callable_count},
        "gc_fraction": _fraction(gc_count, gc_denominator),
        "gc_skew": _fraction(counts["G"] - counts["C"], counts["G"] + counts["C"]),
        "at_skew": _fraction(counts["A"] - counts["T"], counts["A"] + counts["T"]),
        "cpg_count": dinucleotides["CG"],
        "dinucleotide_valid_count": valid_dinucleotides,
        "dinucleotide_counts": dinucleotides,
        "trinucleotide_valid_count": valid_trinucleotides,
        "trinucleotide_counts": trinucleotides,
        "period3_exact": {
            "definition": "four-times-unnormalized-voss-dft-power-at-frequency-one-third",
            "channels": period3,
            "total_scaled_power": period3_total,
        },
        "scl_exact": {"stencil": list(SCL_STENCIL), "channel_energy": scl, "total_energy": scl_total},
        "dominant_base": dominant,
        "etq_address": address,
        "spectral_receiver": receiver,
    }


def _window_count(sequence_length: int, window_size: int, stride: int) -> int:
    if sequence_length <= window_size:
        return 1
    return 1 + (sequence_length - window_size + stride - 1) // stride


def build_windows(sequence: str, window_size: int = 303, stride: int | None = None) -> list[dict[str, object]]:
    if not isinstance(window_size, int) or not 3 <= window_size <= 4095:
        raise ValueError("window_size must be an integer in [3, 4095]")
    stride = window_size if stride is None else stride
    if not isinstance(stride, int) or not 1 <= stride <= window_size:
        raise ValueError("stride must be an integer in [1, window_size]")
    count = _window_count(len(sequence), window_size, stride)
    if count > MAX_WINDOW_COUNT:
        raise ValueError(f"analysis would create {count} windows; limit is {MAX_WINDOW_COUNT}")
    windows = []
    for window_index, start0 in enumerate(range(0, len(sequence), stride)):
        end0 = min(len(sequence), start0 + window_size)
        windows.append(analyze_window(sequence, window_index, start0, end0))
        if end0 == len(sequence):
            break
    return windows


def parse_vcf(text: str | None, record_id: str, sequence: str) -> list[dict[str, object]]:
    if not text:
        return []
    if len(text) > MAX_VCF_CHARACTERS:
        raise ValueError(f"VCF input exceeds the {MAX_VCF_CHARACTERS}-character safety limit")
    variants: list[dict[str, object]] = []
    format_seen = False
    header_seen = False
    seen_loci: set[int] = set()
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("##"):
            if line.startswith("##fileformat="):
                if format_seen:
                    raise ValueError("VCF fileformat declaration is duplicated")
                if line != "##fileformat=VCFv4.5":
                    raise ValueError("VCF fileformat must be exactly VCFv4.5")
                format_seen = True
            continue
        if line.startswith("#CHROM"):
            if header_seen:
                raise ValueError("VCF #CHROM header is duplicated")
            columns = line.split("\t")
            if columns != ["#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO"]:
                raise ValueError("VCF header must contain exactly the canonical eight columns")
            if not format_seen:
                raise ValueError("VCF 4.5 fileformat declaration must precede the #CHROM header")
            header_seen = True
            continue
        if line.startswith("#"):
            raise ValueError(f"unsupported VCF header at line {line_number}")
        if not header_seen:
            raise ValueError("VCF data requires a #CHROM header")
        columns = line.split("\t")
        if len(columns) != 8:
            raise ValueError(f"VCF record at line {line_number} must contain exactly eight columns")
        chrom, pos_text, identifier, ref, alt, qual, filter_value, info = columns
        if chrom != record_id:
            raise ValueError(f"VCF CHROM {chrom!r} does not match FASTA record {record_id!r}")
        if "," in alt or len(ref) != 1 or len(alt) != 1 or ref not in CANONICAL_BASES or alt not in CANONICAL_BASES:
            raise ValueError("only biallelic A/C/G/T SNVs are supported")
        if ref == alt:
            raise ValueError("VCF REF and ALT must differ")
        try:
            pos = int(pos_text)
        except ValueError as error:
            raise ValueError("VCF POS must be an integer") from error
        if not 1 <= pos <= len(sequence):
            raise ValueError("VCF POS is outside the supplied sequence")
        if pos in seen_loci:
            raise ValueError(f"duplicate VCF position is not supported: {pos}")
        if sequence[pos - 1] != ref:
            raise ValueError(f"VCF REF mismatch at position {pos}: expected {sequence[pos - 1]}, received {ref}")
        variants.append({
            "chrom": chrom, "position_1based": pos, "id": identifier, "ref": ref, "alt": alt,
            "qual": qual, "filter": filter_value, "info": info,
        })
        seen_loci.add(pos)
        if len(variants) > MAX_VARIANT_COUNT:
            raise ValueError(f"VCF contains more than the {MAX_VARIANT_COUNT}-variant safety limit")
    if not format_seen or not header_seen:
        raise ValueError("VCF must contain VCFv4.5 fileformat and #CHROM headers")
    return variants


def _cpg_count(sequence: str) -> int:
    return sum(sequence[index:index + 2] == "CG" for index in range(max(0, len(sequence) - 1)))


def _validate_frame_origin(frame_origin_1based: int | None, sequence_length: int) -> None:
    if frame_origin_1based is None:
        return
    if not isinstance(frame_origin_1based, int) or isinstance(frame_origin_1based, bool):
        raise ValueError("frame origin must be an integer")
    if not 1 <= frame_origin_1based <= sequence_length:
        raise ValueError("frame origin must fall within the supplied sequence")


def _frame_effect(sequence: str, position0: int, alt: str, frame_origin_1based: int | None) -> dict[str, str | None]:
    empty = {
        "reference_codon": None, "alternate_codon": None, "reference_amino_acid": None,
        "alternate_amino_acid": None, "frame_relative_effect": "not-evaluated",
    }
    if frame_origin_1based is None:
        return empty
    origin0 = frame_origin_1based - 1
    if position0 < origin0:
        return empty
    codon_start = position0 - ((position0 - origin0) % 3)
    codon = sequence[codon_start:codon_start + 3]
    if len(codon) != 3 or any(base not in CANONICAL_BASES for base in codon):
        return {**empty, "frame_relative_effect": "unresolved-ambiguous-or-incomplete-codon"}
    alternate = list(codon)
    alternate[position0 - codon_start] = alt
    alternate_codon = "".join(alternate)
    ref_aa = STANDARD_CODE[codon]
    alt_aa = STANDARD_CODE[alternate_codon]
    if codon_start == origin0 and ref_aa == "M" and alt_aa != "M":
        effect = "start-lost"
    elif ref_aa == alt_aa:
        effect = "synonymous"
    elif ref_aa != "*" and alt_aa == "*":
        effect = "stop-gained"
    elif ref_aa == "*" and alt_aa != "*":
        effect = "stop-lost"
    else:
        effect = "missense"
    return {
        "reference_codon": codon, "alternate_codon": alternate_codon,
        "reference_amino_acid": ref_aa, "alternate_amino_acid": alt_aa,
        "frame_relative_effect": effect,
    }


def analyze_variants(
    sequence: str,
    variants: Sequence[dict[str, object]],
    windows: Sequence[dict[str, object]],
    frame_origin_1based: int | None,
) -> list[dict[str, object]]:
    output = []
    for variant in variants:
        position0 = int(variant["position_1based"]) - 1
        ref = str(variant["ref"])
        alt = str(variant["alt"])
        containing = [window for window in windows if int(window["start_1based"]) - 1 <= position0 < int(window["end_1based_inclusive"])]
        if len(containing) != 1:
            raise ValueError("variant evidence requires exactly one containing analysis window")
        window = containing[0]
        start0 = int(window["start_1based"]) - 1
        end0 = int(window["end_1based_inclusive"])
        reference_window = sequence[start0:end0]
        alternate_window = list(reference_window)
        alternate_window[position0 - start0] = alt
        alternate_window_text = "".join(alternate_window)
        alternate_metrics = analyze_window(alternate_window_text, int(window["window_index"]), 0, len(alternate_window_text))
        before_period3 = int(window["period3_exact"]["total_scaled_power"])
        after_period3 = int(alternate_metrics["period3_exact"]["total_scaled_power"])
        before_scl = int(window["scl_exact"]["total_energy"])
        after_scl = int(alternate_metrics["scl_exact"]["total_energy"])
        context = "".join(sequence[index] if 0 <= index < len(sequence) else "N" for index in (position0 - 1, position0, position0 + 1))
        output.append({
            **variant,
            "substitution_class": "transition" if (ref, alt) in TRANSITIONS else "transversion",
            "context_3mer": context,
            "etq_address": etq_address_for_offset(position0),
            "window_index": int(window["window_index"]),
            "window_membership_count": 1,
            "period3_scaled_power_delta": after_period3 - before_period3,
            "scl_energy_delta": after_scl - before_scl,
            "gc_count_delta": int(alt in "GC") - int(ref in "GC"),
            "cpg_count_delta": _cpg_count(alternate_window_text) - _cpg_count(reference_window),
            **_frame_effect(sequence, position0, alt, frame_origin_1based),
        })
    return output


def _vlq(value: int) -> bytes:
    if value < 0:
        raise ValueError("VLQ value must be nonnegative")
    output = bytearray([value & 0x7F])
    value >>= 7
    while value:
        output.insert(0, (value & 0x7F) | 0x80)
        value >>= 7
    return bytes(output)


def create_midi(windows: Sequence[dict[str, object]]) -> bytes:
    events: list[tuple[int, int, bytes]] = [
        (0, 0, b"\xFF\x03" + _vlq(len(MIDI_SCHEMA_TEXT)) + MIDI_SCHEMA_TEXT),
        (0, 0, b"\xFF\x51\x03\x07\xA1\x20"),
    ]
    for window in windows:
        receiver = window["spectral_receiver"]
        tick = int(window["window_index"]) * 480
        channel = int(receiver["midi_channel"])
        pitch = int(receiver["midi_pitch"])
        velocity = int(receiver["midi_velocity"])
        duration = int(receiver["duration_ticks"])
        controls = (
            (20, int(window["etq_address"]["site_index"])),
            (21, int(window["etq_address"]["fibre_label"])),
            (22, int(window["etq_address"]["event_index"]) // 128),
            (23, int(window["etq_address"]["event_index"]) % 128),
            (71, int(receiver["midi_scl_cc71"])),
            (74, int(receiver["midi_brightness_cc74"])),
        )
        events.extend((tick, 1, bytes((0xB0 | channel, control, value))) for control, value in controls)
        events.append((tick, 2, bytes((0x90 | channel, pitch, velocity))))
        events.append((tick + duration, 0, bytes((0x80 | channel, pitch, 0))))
    events.sort(key=lambda item: (item[0], item[1], item[2]))
    track = bytearray()
    previous = 0
    for tick, _, payload in events:
        track.extend(_vlq(tick - previous))
        track.extend(payload)
        previous = tick
    track.extend(b"\x00\xFF\x2F\x00")
    header = b"MThd" + (6).to_bytes(4, "big") + (0).to_bytes(2, "big") + (1).to_bytes(2, "big") + (480).to_bytes(2, "big")
    return header + b"MTrk" + len(track).to_bytes(4, "big") + bytes(track)


def window_csv_bytes(windows: Sequence[dict[str, object]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=WINDOW_CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for window in windows:
        counts = window["counts"]
        receiver = window["spectral_receiver"]
        address = window["etq_address"]
        writer.writerow({
            "window_index": window["window_index"], "start_1based": window["start_1based"],
            "end_1based_inclusive": window["end_1based_inclusive"], "length": window["length"],
            "callable_bases": counts["callable"], "ambiguous_bases": counts["ambiguous"],
            "a_count": counts["A"], "c_count": counts["C"], "g_count": counts["G"], "t_count": counts["T"],
            "gc_numerator": window["gc_fraction"]["numerator"], "gc_denominator": window["gc_fraction"]["denominator"],
            "cpg_count": window["cpg_count"], "period3_scaled_power": window["period3_exact"]["total_scaled_power"],
            "scl_energy": window["scl_exact"]["total_energy"], "dominant_base": window["dominant_base"],
            "etq_site": address["site_index"], "etq_fibre": address["fibre_label"], "etq_event": address["event_index"],
            "midi_channel": receiver["midi_channel"], "midi_pitch": receiver["midi_pitch"],
            "midi_velocity": receiver["midi_velocity"], "midi_brightness": receiver["midi_brightness_cc74"],
            "midi_scl_controller": receiver["midi_scl_cc71"],
        })
    return stream.getvalue().encode("utf-8")


def variant_csv_bytes(variants: Sequence[dict[str, object]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=VARIANT_CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for variant in variants:
        address = variant["etq_address"]
        writer.writerow({
            "chrom": variant["chrom"], "position_1based": variant["position_1based"], "id": variant["id"],
            "ref": variant["ref"], "alt": variant["alt"], "substitution_class": variant["substitution_class"],
            "context_3mer": variant["context_3mer"], "etq_site": address["site_index"],
            "etq_fibre": address["fibre_label"], "etq_event": address["event_index"],
            "window_index": variant["window_index"], "period3_scaled_power_delta": variant["period3_scaled_power_delta"],
            "scl_energy_delta": variant["scl_energy_delta"], "gc_count_delta": variant["gc_count_delta"],
            "cpg_count_delta": variant["cpg_count_delta"], "reference_codon": variant["reference_codon"],
            "alternate_codon": variant["alternate_codon"], "reference_amino_acid": variant["reference_amino_acid"],
            "alternate_amino_acid": variant["alternate_amino_acid"], "frame_relative_effect": variant["frame_relative_effect"],
        })
    return stream.getvalue().encode("utf-8")


def build_report(
    fasta_text: str,
    vcf_text: str | None = None,
    window_size: int = 303,
    stride: int | None = None,
    frame_origin_1based: int | None = None,
) -> tuple[dict[str, object], bytes, bytes, bytes]:
    record_id, description, sequence = parse_fasta(fasta_text)
    _validate_frame_origin(frame_origin_1based, len(sequence))
    stride_value = window_size if stride is None else stride
    windows = build_windows(sequence, window_size, stride_value)
    parsed_variants = parse_vcf(vcf_text, record_id, sequence)
    if parsed_variants and stride_value != window_size:
        raise ValueError("variant evidence requires non-overlapping windows (stride equals window_size)")
    variants = analyze_variants(sequence, parsed_variants, windows, frame_origin_1based)
    partner = strand_complement(sequence)
    report = {
        "schema": REPORT_SCHEMA,
        "contract": CONTRACT,
        "input": {
            "record_id": record_id, "description": description, "sequence_length": len(sequence),
            "iupac_alphabet": IUPAC_DNA, "canonical_bases": CANONICAL_BASES,
            "sequence_sha256": sha256_hex(sequence.encode("ascii")),
            "refget_accession": refget_accession(sequence),
            "re" + "verse_complement_sha256": sha256_hex(partner.encode("ascii")),
            "canonical_strand_sha256": sha256_hex(min(sequence, partner).encode("ascii")),
            "window_size": window_size, "stride": stride_value,
            "tail_policy": "include-unpadded-partial-window",
            "frame_origin_1based": frame_origin_1based,
            "variant_profile": "vcf-4.5-text-biallelic-snv-subset",
        },
        "method": {
            "position_address": "event=offset0-mod-303;site=event-mod-101;fibre=event-mod-3",
            "period3": "four-times-unnormalized-voss-dft-power-at-frequency-one-third",
            "period3_re2_weights": list(PERIOD3_RE2_WEIGHTS),
            "period3_im_sqrt3_weights": list(PERIOD3_IM_WEIGHTS),
            "scl_stencil": list(SCL_STENCIL),
            "frequency_surface": "exact-dinucleotide-and-trinucleotide-counts;no-pseudocounts",
            "midi_role": "deterministic-derived-spectral-receiver-not-sequence-identity",
            "genetic_code": "NCBI-translation-table-1-standard-code",
        },
        "window_count": len(windows), "variant_count": len(variants),
        "windows": windows, "variants": variants, "claims": dict(CLAIMS),
    }
    return report, window_csv_bytes(windows), variant_csv_bytes(variants), create_midi(windows)


def manifest_for(report_bytes: bytes, windows_csv: bytes, variants_csv: bytes, midi: bytes) -> dict[str, object]:
    return {
        "schema": MANIFEST_SCHEMA, "contract": CONTRACT,
        "files": {
            "report.json": {"sha256": sha256_hex(report_bytes), "bytes": len(report_bytes)},
            "windows.csv": {"sha256": sha256_hex(windows_csv), "bytes": len(windows_csv)},
            "variants.csv": {"sha256": sha256_hex(variants_csv), "bytes": len(variants_csv)},
            "spectrum.mid": {"sha256": sha256_hex(midi), "bytes": len(midi)},
        },
        "claims": dict(CLAIMS),
    }


def write_outputs(output: Path, report: dict[str, object], windows_csv: bytes, variants_csv: bytes, midi: bytes) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    report_bytes = canonical_json_bytes(report)
    manifest = manifest_for(report_bytes, windows_csv, variants_csv, midi)
    artifacts = {
        "report.json": report_bytes,
        "windows.csv": windows_csv,
        "variants.csv": variants_csv,
        "spectrum.mid": midi,
        "manifest.json": canonical_json_bytes(manifest) + b"\n",
    }
    for name, data in artifacts.items():
        (output / name).write_bytes(data)
    return manifest


def verify_profile(path: Path) -> dict[str, object]:
    profile = json.loads(path.read_text(encoding="utf-8"))
    if profile.get("schema") != PROFILE_SCHEMA:
        raise ValueError("unexpected conformance profile schema")
    if profile.get("contract") != CONTRACT:
        raise ValueError("conformance profile contract mismatch")
    if profile.get("expected_claims") != CLAIMS:
        raise ValueError("conformance profile claim boundary mismatch")
    if not all(value is False for value in profile["expected_claims"].values()):
        raise ValueError("conformance profile attempts to promote a mandatory non-claim")
    report, windows_csv, variants_csv, midi = build_report(
        profile["fasta"], profile.get("vcf"), int(profile["window_size"]),
        int(profile["stride"]), profile.get("frame_origin_1based"),
    )
    report_bytes = canonical_json_bytes(report)
    actual = {
        "report_canonical_sha256": sha256_hex(report_bytes),
        "windows_csv_sha256": sha256_hex(windows_csv),
        "variants_csv_sha256": sha256_hex(variants_csv),
        "midi_sha256": sha256_hex(midi),
    }
    if actual != profile["expected_hashes"]:
        raise ValueError(f"profile hash mismatch: {actual}")
    expected = profile.get("expected", {})
    checks = {
        "sequence_length": report["input"]["sequence_length"],
        "refget_accession": report["input"]["refget_accession"],
        "window_count": report["window_count"],
        "variant_count": report["variant_count"],
        "variant_effects": [entry["frame_relative_effect"] for entry in report["variants"]],
        "substitution_classes": [entry["substitution_class"] for entry in report["variants"]],
    }
    for key, value in checks.items():
        if expected.get(key) != value:
            raise ValueError(f"profile expected {key} mismatch")
    if report["claims"] != CLAIMS:
        raise ValueError("generated report claim boundary mismatch")
    return actual


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--fasta", type=Path, help="single-record FASTA or plain IUPAC DNA file")
    source.add_argument("--sequence", help="plain IUPAC DNA sequence")
    parser.add_argument("--record-id", default="sequence", help="record identifier for --sequence input")
    parser.add_argument("--vcf", type=Path, help="optional VCF 4.5 biallelic SNV subset")
    parser.add_argument("--window-size", type=int, default=303)
    parser.add_argument("--stride", type=int)
    parser.add_argument("--frame-origin", type=int, help="optional 1-based positive-strand frame origin")
    parser.add_argument("--output", type=Path, default=Path("target/genomic-spectral"))
    parser.add_argument("--verify-profile", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.verify_profile:
        print(json.dumps(verify_profile(args.verify_profile), sort_keys=True, indent=2))
        return 0
    if args.fasta:
        fasta_text = args.fasta.read_text(encoding="utf-8")
    elif args.sequence:
        fasta_text = f">{args.record_id}\n{args.sequence}\n"
    else:
        raise SystemExit("one of --fasta, --sequence, or --verify-profile is required")
    vcf_text = args.vcf.read_text(encoding="utf-8") if args.vcf else None
    report, windows_csv, variants_csv, midi = build_report(
        fasta_text, vcf_text, args.window_size, args.stride, args.frame_origin
    )
    manifest = write_outputs(args.output, report, windows_csv, variants_csv, midi)
    print(json.dumps(manifest, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
