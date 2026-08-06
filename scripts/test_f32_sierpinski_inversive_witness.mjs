#!/usr/bin/env node
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  AXIS_NAMES,
  CLAIMS,
  CONTRACT,
  MAX_WITNESS_COUNT,
  buildBundle,
  transformBarycentric,
  validateWitness,
  verifyBundle,
  wordToWitness,
} from "../web/inversive-witness/model.js";

const profilePath = process.argv[2] ?? "conformance/f32_sierpinski_inversive_witness_v1.json";
const profile = JSON.parse(await readFile(profilePath, "utf8"));
assert.equal(profile.contract, CONTRACT);
assert.deepEqual(profile.expected_claims, CLAIMS);
const words = profile.words_hex.map(value => Number.parseInt(value, 16) >>> 0);
const bundle = await buildBundle(words, profile.fibre_labels);
assert.equal(bundle.canonical_sha256, profile.expected_bundle_sha256);
assert.deepEqual(await verifyBundle(bundle), words);

for (const word of words) {
  for (let fibre = 0; fibre < 3; fibre += 1) {
    const witness = await wordToWitness(word, fibre);
    assert.equal(await validateWitness(witness), word);
    assert.equal(witness.reflection_axis, AXIS_NAMES[fibre]);
    assert.deepEqual(witness.squared_radius_product, { numerator: "1", denominator: "9" });
    assert.deepEqual(witness.double_application_barycentric, witness.source_centroid_barycentric);
  }
}

let state = 0x5f3759df;
const randomWords = [];
const randomFibres = [];
for (let index = 0; index < 512; index += 1) {
  state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
  randomWords.push(state);
  randomFibres.push(state % 3);
}
assert.deepEqual(await verifyBundle(await buildBundle(randomWords, randomFibres)), randomWords);

const tampered = structuredClone(await wordToWitness(0x3f800000, 2));
tampered.conjugate_barycentric.numerators[0] = String(
  BigInt(tampered.conjugate_barycentric.numerators[0]) + 1n,
);
await assert.rejects(validateWitness(tampered), /evidence mismatch/);
const numericClaim = structuredClone(await wordToWitness(0x3f800000, 2));
numericClaim.claims.geometry_receipt_authority = 0;
await assert.rejects(validateWitness(numericClaim), /claim boundary/);
assert.throws(() => transformBarycentric([1n, 1n, 1n], 3n, 0), /no finite conjugate/);
await assert.rejects(
  buildBundle(Array(MAX_WITNESS_COUNT + 1).fill(0), Array(MAX_WITNESS_COUNT + 1).fill(0)),
  new RegExp(String(MAX_WITNESS_COUNT)),
);

const lineage = await wordToWitness(0x5f3759df, 0);
assert.equal(lineage.word_hex, "5f3759df");
assert.equal(lineage.claims.compression_claim, false);
assert.equal(lineage.claims.clawson_quadrilateral_constructed, false);

console.log(JSON.stringify({
  schema: "RSH-F32-SIERPINSKI-INVERSIVE-WITNESS-CROSS-RUNTIME-V1",
  status: "PASS",
  contract: CONTRACT,
  witness_count: words.length,
  bundle_sha256: bundle.canonical_sha256,
  claims: CLAIMS,
}, null, 2));
