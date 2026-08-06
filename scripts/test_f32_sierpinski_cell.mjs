#!/usr/bin/env node
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  F32_CELL_CLAIMS,
  F32_CELL_CONTRACT,
  MAX_F32_BUNDLE_CELLS,
  buildCellBundle,
  classifyWord,
  exactCellVertices,
  f32ToWord,
  tritsToWord,
  validateCell,
  verifyCellBundle,
  wordToCell,
  wordToTrits,
} from "../web/genomic-spectrum/f32-cell.js";

const profilePath = process.argv[2] ?? "conformance/f32_sierpinski_cell_v1.json";
const profile = JSON.parse(await readFile(profilePath, "utf8"));
assert.equal(profile.contract, F32_CELL_CONTRACT);
assert.deepEqual(profile.expected_claims, F32_CELL_CLAIMS);
const words = profile.words_hex.map((value) => Number.parseInt(value, 16) >>> 0);
const bundle = await buildCellBundle(words, profile.fields);
assert.equal(bundle.canonical_sha256, profile.expected_bundle_sha256);
assert.deepEqual(await verifyCellBundle(bundle), words);

for (const word of words) {
  const trits = wordToTrits(word);
  assert.equal(tritsToWord(trits), word);
  assert.equal(validateCell(wordToCell(word)), word);
}

let state = 0x5f3759df;
const randomWords = [];
for (let index = 0; index < 10_000; index += 1) {
  state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
  randomWords.push(state);
}
assert.deepEqual(await verifyCellBundle(await buildCellBundle(randomWords)), randomWords);

const vertices = exactCellVertices(wordToTrits(0x5f3759df));
assert.equal(vertices.denominator, 2 ** 21);
for (const vertex of vertices.numerators) assert.equal(vertex.reduce((a, b) => a + b, 0), vertices.denominator);
assert.equal(classifyWord(0x7fc00001), "quiet-nan");
assert.equal(classifyWord(0x7fa00001), "signaling-nan");
assert.equal(f32ToWord(1.0), 0x3f800000);
assert.equal(f32ToWord(-0.0), 0x80000000);
assert.equal(f32ToWord(Math.PI), 0x40490fdb);

const tampered = structuredClone(wordToCell(0x3f800000));
tampered.claims.physical_storage_demonstrated = true;
assert.throws(() => validateCell(tampered), /claim boundary/);
const numericClaim = structuredClone(wordToCell(0x3f800000));
numericClaim.claims.physical_storage_demonstrated = 0;
assert.throws(() => validateCell(numericClaim), /claim boundary/);
assert.throws(() => wordToCell(0, { field: "chré" }), /printable ASCII/);
assert.throws(
  () => buildCellBundle(Array(MAX_F32_BUNDLE_CELLS + 1).fill(0)),
  new RegExp(String(MAX_F32_BUNDLE_CELLS)),
);

console.log(JSON.stringify({
  schema: "RSH-F32-SIERPINSKI-CELL-CROSS-RUNTIME-V1",
  status: "PASS",
  contract: F32_CELL_CONTRACT,
  cell_count: words.length,
  bundle_sha256: bundle.canonical_sha256,
  claims: F32_CELL_CLAIMS,
}, null, 2));
