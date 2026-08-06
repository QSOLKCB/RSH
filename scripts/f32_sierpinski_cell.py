#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# SPDX-License-Identifier: MPL-2.0
"""Exact IEEE-754 binary32 to depth-21 Sierpinski-cell codec."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Iterable, Sequence

CONTRACT = "RSH-F32-SIERPINSKI-CELL-V1"
CELL_SCHEMA = "RSH-F32-SIERPINSKI-CELL-RECORD-V1"
BUNDLE_SCHEMA = "RSH-F32-SIERPINSKI-CELL-BUNDLE-V1"
PROFILE_SCHEMA = "RSH-F32-SIERPINSKI-CELL-CONFORMANCE-V1"
DEPTH = 21
WORD_LIMIT = 1 << 32
TRIT_CAPACITY = 3**DEPTH
MAX_BUNDLE_CELLS = 16_384
MAX_FIELD_CHARACTERS = 128
VERTEX_LABELS = ("left", "right", "apex")
CLAIMS = {
    "actual_multi_device_execution": False,
    "compression_claim": False,
    "coordinates_are_identity": False,
    "distributed_execution": False,
    "geometry_receipt_authority": False,
    "physical_storage_demonstrated": False,
}

if not 3**20 < WORD_LIMIT < TRIT_CAPACITY:
    raise RuntimeError("depth-21 ternary capacity invariant failed")


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _claims_are_exact(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != set(CLAIMS):
        return False
    return all(type(value[key]) is bool and value[key] is expected for key, expected in CLAIMS.items())


def validate_word(word: int) -> int:
    if isinstance(word, bool) or not isinstance(word, int) or not 0 <= word < WORD_LIMIT:
        raise ValueError("binary32 word must be an integer in [0, 2^32)")
    return word


def validate_field(field: str | None) -> str | None:
    if field is None:
        return None
    if not isinstance(field, str) or not field:
        raise ValueError("field must be nonempty text")
    if len(field) > MAX_FIELD_CHARACTERS:
        raise ValueError(f"field exceeds the {MAX_FIELD_CHARACTERS}-character safety limit")
    if any(ord(character) < 0x20 or ord(character) > 0x7E for character in field):
        raise ValueError("field must contain printable ASCII only for cross-runtime canonicalization")
    return field


def word_to_trits(word: int) -> str:
    value = validate_word(word)
    digits = ["0"] * DEPTH
    for index in range(DEPTH - 1, -1, -1):
        value, digit = divmod(value, 3)
        digits[index] = str(digit)
    if value:
        raise AssertionError("binary32 word escaped depth-21 ternary capacity")
    return "".join(digits)


def trits_to_word(trits: str) -> int:
    if not isinstance(trits, str) or len(trits) != DEPTH or any(ch not in "012" for ch in trits):
        raise ValueError(f"Sierpinski address must contain exactly {DEPTH} trits")
    value = 0
    for character in trits:
        value = value * 3 + int(character)
    if value >= WORD_LIMIT:
        raise ValueError("Sierpinski address is outside the binary32 word domain")
    return value


def exact_cell_vertices(trits: str) -> tuple[list[list[int]], int]:
    """Return exact barycentric vertex numerators and common power-of-two denominator."""
    trits_to_word(trits)
    vertices = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    denominator = 1
    for character in trits:
        selected = int(character)
        for vertex in vertices:
            vertex[selected] += denominator
        denominator *= 2
    return vertices, denominator


def exact_cell_centroid(trits: str) -> tuple[list[int], int]:
    vertices, denominator = exact_cell_vertices(trits)
    return [sum(vertex[axis] for vertex in vertices) for axis in range(3)], 3 * denominator


def classify_word(word: int) -> str:
    validate_word(word)
    exponent = (word >> 23) & 0xFF
    fraction = word & 0x7FFFFF
    if exponent == 0:
        return "zero" if fraction == 0 else "subnormal"
    if exponent == 0xFF:
        if fraction == 0:
            return "infinity"
        return "quiet-nan" if fraction & (1 << 22) else "signaling-nan"
    return "normal"


def word_to_f32(word: int) -> float:
    validate_word(word)
    return struct.unpack(">f", struct.pack(">I", word))[0]


def f32_to_word(value: float) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("f32 input must be numeric")
    try:
        return struct.unpack(">I", struct.pack(">f", float(value)))[0]
    except OverflowError as error:
        raise ValueError("value cannot be represented as IEEE-754 binary32") from error


def word_to_cell(word: int, *, cell_index: int | None = None, field: str | None = None) -> dict[str, object]:
    word = validate_word(word)
    if cell_index is not None and (isinstance(cell_index, bool) or not isinstance(cell_index, int) or cell_index < 0):
        raise ValueError("cell_index must be a nonnegative integer")
    field = validate_field(field)
    trits = word_to_trits(word)
    vertices, vertex_denominator = exact_cell_vertices(trits)
    centroid, centroid_denominator = exact_cell_centroid(trits)
    record: dict[str, object] = {
        "schema": CELL_SCHEMA,
        "contract": CONTRACT,
        "depth": DEPTH,
        "address_radix": 3,
        "address_trits": trits,
        "word_u32": word,
        "word_hex": f"{word:08x}",
        "sign_bit": (word >> 31) & 1,
        "exponent_bits": (word >> 23) & 0xFF,
        "fraction_bits": word & 0x7FFFFF,
        "classification": classify_word(word),
        "cell_vertex_barycentric_numerators": vertices,
        "cell_vertex_barycentric_denominator": vertex_denominator,
        "cell_centroid_barycentric_numerators": centroid,
        "cell_centroid_barycentric_denominator": centroid_denominator,
        "identity_policy": "word_u32-and-address_trits-exact;coordinates-derived-not-identity",
        "claims": dict(CLAIMS),
    }
    if cell_index is not None:
        record["cell_index"] = cell_index
    if field is not None:
        record["field"] = field
    return record


def validate_cell(cell: dict[str, object]) -> int:
    if not isinstance(cell, dict):
        raise TypeError("cell must be an object")
    if cell.get("schema") != CELL_SCHEMA or cell.get("contract") != CONTRACT:
        raise ValueError("unexpected Sierpinski cell schema or contract")
    if not _claims_are_exact(cell.get("claims")):
        raise ValueError("Sierpinski cell claim boundary mismatch")
    trits = cell.get("address_trits")
    word = trits_to_word(trits if isinstance(trits, str) else "")
    if cell.get("word_u32") != word or cell.get("word_hex") != f"{word:08x}":
        raise ValueError("Sierpinski address and binary32 word disagree")
    if cell.get("depth") != DEPTH or cell.get("address_radix") != 3:
        raise ValueError("Sierpinski cell depth or radix mismatch")
    if cell.get("sign_bit") != (word >> 31) & 1:
        raise ValueError("binary32 sign bit mismatch")
    if cell.get("exponent_bits") != (word >> 23) & 0xFF:
        raise ValueError("binary32 exponent bits mismatch")
    if cell.get("fraction_bits") != word & 0x7FFFFF:
        raise ValueError("binary32 fraction bits mismatch")
    if cell.get("classification") != classify_word(word):
        raise ValueError("binary32 classification mismatch")
    if "field" in cell:
        validate_field(cell.get("field"))
    vertices, vertex_denominator = exact_cell_vertices(trits)
    centroid, centroid_denominator = exact_cell_centroid(trits)
    if cell.get("cell_vertex_barycentric_numerators") != vertices:
        raise ValueError("Sierpinski cell vertex evidence mismatch")
    if cell.get("cell_vertex_barycentric_denominator") != vertex_denominator:
        raise ValueError("Sierpinski cell vertex denominator mismatch")
    if cell.get("cell_centroid_barycentric_numerators") != centroid:
        raise ValueError("Sierpinski cell centroid evidence mismatch")
    if cell.get("cell_centroid_barycentric_denominator") != centroid_denominator:
        raise ValueError("Sierpinski cell centroid denominator mismatch")
    return word


def cells_for_words(words: Iterable[int], fields: Sequence[str] | None = None) -> list[dict[str, object]]:
    if fields is not None:
        if isinstance(fields, (str, bytes)) or not isinstance(fields, Sequence):
            raise TypeError("fields must be a sequence of text labels")
        if len(fields) > MAX_BUNDLE_CELLS:
            raise ValueError(f"field count exceeds the {MAX_BUNDLE_CELLS}-cell bundle limit")
    cells: list[dict[str, object]] = []
    for index, word in enumerate(words):
        if index >= MAX_BUNDLE_CELLS:
            raise ValueError(f"word iterable exceeds the {MAX_BUNDLE_CELLS}-cell bundle limit")
        if fields is not None and index >= len(fields):
            raise ValueError("field count must equal word count")
        cells.append(
            word_to_cell(word, cell_index=index, field=None if fields is None else fields[index])
        )
    if fields is not None and len(fields) != len(cells):
        raise ValueError("field count must equal word count")
    return cells


def build_bundle(words: Iterable[int], fields: Sequence[str] | None = None) -> dict[str, object]:
    cells = cells_for_words(words, fields)
    for cell in cells:
        validate_cell(cell)
    bundle = {
        "schema": BUNDLE_SCHEMA,
        "contract": CONTRACT,
        "depth": DEPTH,
        "cell_count": len(cells),
        "capacity_words": WORD_LIMIT,
        "ternary_address_capacity": TRIT_CAPACITY,
        "cells": cells,
        "round_trip_verified": True,
        "claims": dict(CLAIMS),
    }
    bundle["canonical_sha256"] = sha256_hex(canonical_json_bytes(bundle))
    return bundle


def verify_bundle(bundle: dict[str, object]) -> list[int]:
    if bundle.get("schema") != BUNDLE_SCHEMA or bundle.get("contract") != CONTRACT:
        raise ValueError("unexpected Sierpinski bundle schema or contract")
    if not _claims_are_exact(bundle.get("claims")):
        raise ValueError("Sierpinski bundle claim boundary mismatch")
    cells = bundle.get("cells")
    cell_count = bundle.get("cell_count")
    if (
        not isinstance(cells, list)
        or isinstance(cell_count, bool)
        or not isinstance(cell_count, int)
        or cell_count != len(cells)
        or cell_count > MAX_BUNDLE_CELLS
    ):
        raise ValueError("Sierpinski bundle cell count mismatch")
    words = [validate_cell(cell) for cell in cells]
    unsigned = dict(bundle)
    declared_hash = unsigned.pop("canonical_sha256", None)
    if declared_hash != sha256_hex(canonical_json_bytes(unsigned)):
        raise ValueError("Sierpinski bundle canonical hash mismatch")
    if bundle.get("round_trip_verified") is not True:
        raise ValueError("Sierpinski bundle must declare verified round trip")
    return words


def verify_profile(path: Path) -> dict[str, object]:
    profile = json.loads(path.read_text(encoding="utf-8"))
    if profile.get("schema") != PROFILE_SCHEMA or profile.get("contract") != CONTRACT:
        raise ValueError("unexpected Sierpinski conformance profile")
    if not _claims_are_exact(profile.get("expected_claims")):
        raise ValueError("Sierpinski conformance claim boundary mismatch")
    words = [int(text, 16) for text in profile["words_hex"]]
    bundle = build_bundle(words, profile.get("fields"))
    if verify_bundle(bundle) != words:
        raise AssertionError("Sierpinski profile round trip failed")
    if bundle["canonical_sha256"] != profile["expected_bundle_sha256"]:
        raise ValueError("Sierpinski profile bundle hash mismatch")
    return {
        "status": "PASS",
        "contract": CONTRACT,
        "cell_count": len(words),
        "bundle_sha256": bundle["canonical_sha256"],
        "claims": dict(CLAIMS),
    }


def _parse_word(text: str) -> int:
    value = text.strip().lower()
    base = 16 if value.startswith("0x") else 10
    try:
        parsed = int(value, base)
    except ValueError as error:
        raise argparse.ArgumentTypeError("word must be decimal or 0x-prefixed hexadecimal") from error
    try:
        return validate_word(parsed)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--word", action="append", type=_parse_word, default=[])
    parser.add_argument("--value", action="append", type=float, default=[])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-profile", type=Path)
    args = parser.parse_args(argv)
    if args.verify_profile:
        print(json.dumps(verify_profile(args.verify_profile), indent=2, sort_keys=True))
        return 0
    words = [*args.word, *(f32_to_word(value) for value in args.value)]
    if not words:
        raise SystemExit("provide at least one --word, --value, or --verify-profile")
    bundle = build_bundle(words)
    payload = canonical_json_bytes(bundle) + b"\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(payload)
    print(payload.decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
