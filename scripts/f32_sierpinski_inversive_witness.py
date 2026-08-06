#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# SPDX-License-Identifier: MPL-2.0
"""Exact inversion-reflection witnesses for depth-21 f32 Sierpinski cells."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Iterable, Sequence

if __package__:
    from scripts.f32_sierpinski_cell import (
        CONTRACT as CELL_CONTRACT,
        canonical_json_bytes,
        exact_cell_centroid,
        validate_word,
        word_to_cell,
        word_to_trits,
    )
else:
    from f32_sierpinski_cell import (
        CONTRACT as CELL_CONTRACT,
        canonical_json_bytes,
        exact_cell_centroid,
        validate_word,
        word_to_cell,
        word_to_trits,
    )

CONTRACT = "RSH-F32-SIERPINSKI-INVERSIVE-WITNESS-V1"
WITNESS_SCHEMA = "RSH-F32-SIERPINSKI-INVERSIVE-WITNESS-RECORD-V1"
BUNDLE_SCHEMA = "RSH-F32-SIERPINSKI-INVERSIVE-WITNESS-BUNDLE-V1"
PROFILE_SCHEMA = "RSH-F32-SIERPINSKI-INVERSIVE-WITNESS-CONFORMANCE-V1"
AXIS_NAMES = ("median-through-left", "median-through-right", "median-through-apex")
REFLECTION_PERMUTATIONS = ((0, 2, 1), (2, 1, 0), (1, 0, 2))
INVERSION_CONSTANT_SQUARED = (1, 3)
MAX_WITNESS_COUNT = 4_096
CLAIMS = {
    "actual_multi_device_execution": False,
    "clawson_quadrilateral_constructed": False,
    "compression_claim": False,
    "coordinates_are_identity": False,
    "distributed_execution": False,
    "geometry_receipt_authority": False,
    "physical_storage_demonstrated": False,
}
_INTEGER_PATTERN = re.compile(r"-?(?:0|[1-9][0-9]*)\Z")
_POSITIVE_PATTERN = re.compile(r"(?:[1-9][0-9]*)\Z")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _claims_are_exact(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != set(CLAIMS):
        return False
    return all(type(value[key]) is bool and value[key] is expected for key, expected in CLAIMS.items())


def validate_fibre_label(fibre_label: int) -> int:
    if isinstance(fibre_label, bool) or not isinstance(fibre_label, int) or not 0 <= fibre_label < 3:
        raise ValueError("fibre_label must be an integer in [0, 2]")
    return fibre_label


def _normalize_vector(numerators: Sequence[int], denominator: int) -> tuple[list[int], int]:
    if (
        isinstance(denominator, bool)
        or not isinstance(denominator, int)
        or denominator <= 0
        or len(numerators) != 3
        or any(isinstance(value, bool) or not isinstance(value, int) for value in numerators)
    ):
        raise ValueError("barycentric evidence requires three integer numerators and a positive denominator")
    if sum(numerators) != denominator:
        raise ValueError("barycentric numerators must sum to their denominator")
    common = denominator
    for value in numerators:
        common = math.gcd(common, abs(value))
    return [value // common for value in numerators], denominator // common


def _normalize_rational(numerator: int, denominator: int) -> tuple[int, int]:
    if isinstance(numerator, bool) or not isinstance(numerator, int):
        raise ValueError("rational numerator must be an integer")
    if isinstance(denominator, bool) or not isinstance(denominator, int) or denominator == 0:
        raise ValueError("rational denominator must be a nonzero integer")
    if denominator < 0:
        numerator, denominator = -numerator, -denominator
    common = math.gcd(abs(numerator), denominator)
    return numerator // common, denominator // common


def _rational_json(numerator: int, denominator: int) -> dict[str, str]:
    numerator, denominator = _normalize_rational(numerator, denominator)
    return {"numerator": str(numerator), "denominator": str(denominator)}


def _barycentric_json(numerators: Sequence[int], denominator: int) -> dict[str, object]:
    numerators, denominator = _normalize_vector(numerators, denominator)
    return {"numerators": [str(value) for value in numerators], "denominator": str(denominator)}


def _parse_decimal(text: object, *, positive: bool = False) -> int:
    pattern = _POSITIVE_PATTERN if positive else _INTEGER_PATTERN
    if not isinstance(text, str) or pattern.fullmatch(text) is None:
        raise ValueError("exact integer evidence must use canonical decimal strings")
    return int(text)


def parse_barycentric(value: object) -> tuple[list[int], int]:
    if not isinstance(value, dict) or set(value) != {"numerators", "denominator"}:
        raise ValueError("invalid barycentric evidence object")
    raw = value["numerators"]
    if not isinstance(raw, list) or len(raw) != 3:
        raise ValueError("barycentric evidence requires three numerators")
    numerators = [_parse_decimal(item) for item in raw]
    denominator = _parse_decimal(value["denominator"], positive=True)
    return _normalize_vector(numerators, denominator)


def transform_barycentric(
    numerators: Sequence[int],
    denominator: int,
    fibre_label: int,
) -> tuple[list[int], int]:
    """Apply circumcircle inversion and the fibre-selected median reflection."""
    fibre_label = validate_fibre_label(fibre_label)
    numerators, denominator = _normalize_vector(numerators, denominator)
    centred = [3 * value - denominator for value in numerators]
    squared_sum = sum(value * value for value in centred)
    if squared_sum == 0:
        raise ValueError("the inversion centre has no finite conjugate")
    permutation = REFLECTION_PERMUTATIONS[fibre_label]
    reflected = [centred[permutation[index]] for index in range(3)]
    output = [squared_sum + 6 * denominator * value for value in reflected]
    return _normalize_vector(output, 3 * squared_sum)


def radius_squared(numerators: Sequence[int], denominator: int) -> tuple[int, int]:
    numerators, denominator = _normalize_vector(numerators, denominator)
    centred = [3 * value - denominator for value in numerators]
    squared_sum = sum(value * value for value in centred)
    return _normalize_rational(squared_sum, 18 * denominator * denominator)


def _multiply_rationals(left: tuple[int, int], right: tuple[int, int]) -> tuple[int, int]:
    return _normalize_rational(left[0] * right[0], left[1] * right[1])


def word_to_witness(word: int, fibre_label: int) -> dict[str, object]:
    word = validate_word(word)
    fibre_label = validate_fibre_label(fibre_label)
    cell = word_to_cell(word)
    source_numerators = [int(value) for value in cell["cell_centroid_barycentric_numerators"]]
    source_denominator = int(cell["cell_centroid_barycentric_denominator"])
    conjugate_numerators, conjugate_denominator = transform_barycentric(
        source_numerators, source_denominator, fibre_label
    )
    recovered_numerators, recovered_denominator = transform_barycentric(
        conjugate_numerators, conjugate_denominator, fibre_label
    )
    normalized_source = _normalize_vector(source_numerators, source_denominator)
    source_radius = radius_squared(source_numerators, source_denominator)
    conjugate_radius = radius_squared(conjugate_numerators, conjugate_denominator)
    product = _multiply_rationals(source_radius, conjugate_radius)
    expected_product = _normalize_rational(1, 9)
    double_verified = (recovered_numerators, recovered_denominator) == normalized_source
    product_verified = product == expected_product
    if not double_verified or not product_verified:
        raise AssertionError("inversive witness invariant failed")
    return {
        "schema": WITNESS_SCHEMA,
        "contract": CONTRACT,
        "cell_contract": CELL_CONTRACT,
        "word_u32": word,
        "word_hex": f"{word:08x}",
        "address_trits": word_to_trits(word),
        "source_cell_canonical_sha256": sha256_hex(canonical_json_bytes(cell)),
        "fibre_label": fibre_label,
        "reflection_axis": AXIS_NAMES[fibre_label],
        "reflection_permutation": list(REFLECTION_PERMUTATIONS[fibre_label]),
        "inversion_center": "equilateral-triangle-centroid",
        "inversion_constant_squared": _rational_json(*INVERSION_CONSTANT_SQUARED),
        "source_centroid_barycentric": _barycentric_json(source_numerators, source_denominator),
        "conjugate_barycentric": _barycentric_json(conjugate_numerators, conjugate_denominator),
        "double_application_barycentric": _barycentric_json(
            recovered_numerators, recovered_denominator
        ),
        "source_radius_squared": _rational_json(*source_radius),
        "conjugate_radius_squared": _rational_json(*conjugate_radius),
        "squared_radius_product": _rational_json(*product),
        "product_invariant_verified": True,
        "double_conjugation_verified": True,
        "identity_policy": (
            "word-and-trits-identify-cell;"
            "exact-rational-witness-is-independent-sidecar;"
            "rendered-coordinates-are-not-identity"
        ),
        "claims": dict(CLAIMS),
    }


def validate_witness(witness: dict[str, object]) -> int:
    if not isinstance(witness, dict):
        raise TypeError("witness must be an object")
    if witness.get("schema") != WITNESS_SCHEMA or witness.get("contract") != CONTRACT:
        raise ValueError("unexpected inversive witness schema or contract")
    if not _claims_are_exact(witness.get("claims")):
        raise ValueError("inversive witness claim boundary mismatch")
    word = witness.get("word_u32")
    fibre_label = witness.get("fibre_label")
    if isinstance(word, bool) or not isinstance(word, int):
        raise ValueError("inversive witness word is invalid")
    if isinstance(fibre_label, bool) or not isinstance(fibre_label, int):
        raise ValueError("inversive witness fibre label is invalid")
    expected = word_to_witness(word, fibre_label)
    if canonical_json_bytes(witness) != canonical_json_bytes(expected):
        raise ValueError("inversive witness evidence mismatch")
    parse_barycentric(witness["source_centroid_barycentric"])
    parse_barycentric(witness["conjugate_barycentric"])
    parse_barycentric(witness["double_application_barycentric"])
    return word


def witnesses_for_words(
    words: Iterable[int],
    fibre_labels: Sequence[int],
) -> list[dict[str, object]]:
    if isinstance(fibre_labels, (str, bytes)) or not isinstance(fibre_labels, Sequence):
        raise TypeError("fibre_labels must be a sequence")
    if len(fibre_labels) > MAX_WITNESS_COUNT:
        raise ValueError(f"fibre count exceeds the {MAX_WITNESS_COUNT}-witness limit")
    witnesses: list[dict[str, object]] = []
    for index, word in enumerate(words):
        if index >= MAX_WITNESS_COUNT:
            raise ValueError(f"word iterable exceeds the {MAX_WITNESS_COUNT}-witness limit")
        if index >= len(fibre_labels):
            raise ValueError("fibre count must equal word count")
        witnesses.append(word_to_witness(word, fibre_labels[index]))
    if len(witnesses) != len(fibre_labels):
        raise ValueError("fibre count must equal word count")
    return witnesses


def build_bundle(words: Iterable[int], fibre_labels: Sequence[int]) -> dict[str, object]:
    witnesses = witnesses_for_words(words, fibre_labels)
    for witness in witnesses:
        validate_witness(witness)
    bundle = {
        "schema": BUNDLE_SCHEMA,
        "contract": CONTRACT,
        "cell_contract": CELL_CONTRACT,
        "witness_count": len(witnesses),
        "inversion_constant_squared": _rational_json(*INVERSION_CONSTANT_SQUARED),
        "witnesses": witnesses,
        "round_trip_verified": True,
        "product_invariant_verified": True,
        "claims": dict(CLAIMS),
    }
    bundle["canonical_sha256"] = sha256_hex(canonical_json_bytes(bundle))
    return bundle


def verify_bundle(bundle: dict[str, object]) -> list[int]:
    if bundle.get("schema") != BUNDLE_SCHEMA or bundle.get("contract") != CONTRACT:
        raise ValueError("unexpected inversive witness bundle")
    if bundle.get("cell_contract") != CELL_CONTRACT:
        raise ValueError("inversive witness bundle cell contract mismatch")
    if not _claims_are_exact(bundle.get("claims")):
        raise ValueError("inversive witness bundle claim boundary mismatch")
    witnesses = bundle.get("witnesses")
    count = bundle.get("witness_count")
    if (
        not isinstance(witnesses, list)
        or isinstance(count, bool)
        or not isinstance(count, int)
        or count != len(witnesses)
        or count > MAX_WITNESS_COUNT
    ):
        raise ValueError("inversive witness bundle count mismatch")
    words = [validate_witness(witness) for witness in witnesses]
    unsigned = dict(bundle)
    declared_hash = unsigned.pop("canonical_sha256", None)
    if declared_hash != sha256_hex(canonical_json_bytes(unsigned)):
        raise ValueError("inversive witness bundle canonical hash mismatch")
    if bundle.get("round_trip_verified") is not True:
        raise ValueError("inversive witness bundle must declare exact round trip")
    if bundle.get("product_invariant_verified") is not True:
        raise ValueError("inversive witness bundle must declare product verification")
    return words


def verify_profile(path: Path) -> dict[str, object]:
    profile = json.loads(path.read_text(encoding="utf-8"))
    if profile.get("schema") != PROFILE_SCHEMA or profile.get("contract") != CONTRACT:
        raise ValueError("unexpected inversive witness conformance profile")
    if not _claims_are_exact(profile.get("expected_claims")):
        raise ValueError("inversive witness conformance claim boundary mismatch")
    words = [int(text, 16) for text in profile["words_hex"]]
    fibres = profile["fibre_labels"]
    bundle = build_bundle(words, fibres)
    if verify_bundle(bundle) != words:
        raise AssertionError("inversive witness profile round trip failed")
    if bundle["canonical_sha256"] != profile["expected_bundle_sha256"]:
        raise ValueError("inversive witness profile bundle hash mismatch")
    return {
        "status": "PASS",
        "contract": CONTRACT,
        "witness_count": len(words),
        "bundle_sha256": bundle["canonical_sha256"],
        "claims": dict(CLAIMS),
    }


def _parse_word(text: str) -> int:
    value = text.strip().lower()
    base = 16 if value.startswith("0x") else 10
    try:
        return validate_word(int(value, base))
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "word must be decimal or 0x-prefixed hexadecimal in [0, 2^32)"
        ) from error


def _parse_fibre(text: str) -> int:
    try:
        return validate_fibre_label(int(text, 10))
    except ValueError as error:
        raise argparse.ArgumentTypeError("fibre must be 0, 1, or 2") from error


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--word", action="append", type=_parse_word, default=[])
    parser.add_argument("--fibre", action="append", type=_parse_fibre, default=[])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-profile", type=Path)
    args = parser.parse_args(argv)
    if args.verify_profile:
        print(json.dumps(verify_profile(args.verify_profile), indent=2, sort_keys=True))
        return 0
    if not args.word or len(args.word) != len(args.fibre):
        raise SystemExit("provide equal nonzero counts of --word and --fibre")
    bundle = build_bundle(args.word, args.fibre)
    payload = canonical_json_bytes(bundle) + b"\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(payload)
    print(payload.decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
