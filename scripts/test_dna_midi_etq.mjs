#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  CLAIMS,
  CODONS,
  CONTRACT,
  EVENT_COUNT,
  MAX_INPUT_CHARACTERS,
  MAX_SEQUENCE_BASES,
  buildArtifacts,
  createMidi,
  decodeMidi,
  decodeRecords,
  encodeRecords,
  eventAddress,
  eventIndexFromAddress,
  normalizeSequence,
  sha256Hex,
} from "../web/dna-midi/model.js";

const profilePath = process.argv[2] ?? "conformance/dna_midi_etq_exploratory_v1.json";
const profile = JSON.parse(await readFile(profilePath, "utf8"));
assert.equal(profile.contract, CONTRACT);
assert.deepEqual(profile.expected_claims, CLAIMS);
const artifacts = await buildArtifacts(profile.sequence);

assert.equal(artifacts.records.length, profile.expected_record_count);
assert.equal(decodeRecords(artifacts.records), profile.sequence);
assert.equal(decodeMidi(artifacts.midi), profile.sequence);
assert.equal(artifacts.manifest.round_trip_verified, true);
for (const [key, expected] of Object.entries(profile.expected_hashes)) {
  assert.equal(artifacts.manifest[key], expected, `${key} differs from the sealed fixture`);
}
assert.deepEqual(artifacts.report.claims, profile.expected_claims);
assert.deepEqual(artifacts.manifest.claims, profile.expected_claims);
for (const [name, value] of Object.entries(CLAIMS)) {
  assert.equal(value, false, `${name} must remain false`);
}
assert.equal(await sha256Hex(artifacts.reportCanonical), artifacts.manifest.report_canonical_sha256);

const visited = new Set();
for (let eventIndex = 0; eventIndex < EVENT_COUNT; eventIndex += 1) {
  const address = eventAddress(eventIndex);
  assert.equal(eventIndexFromAddress(address.siteIndex, address.fibreLabel), eventIndex);
  visited.add(`${address.siteIndex}:${address.fibreLabel}`);
}
assert.equal(visited.size, EVENT_COUNT);

assert.throws(() => normalizeSequence("ATG-NNN"), /invalid symbols/);
assert.throws(() => normalizeSequence("ATGC"), /multiple of 3/);
assert.throws(() => normalizeSequence("A".repeat(MAX_SEQUENCE_BASES + 3)), /base safety limit/);
assert.throws(() => normalizeSequence(" ".repeat(MAX_INPUT_CHARACTERS + 1)), /character safety limit/);

const tampered = artifacts.midi.slice();
let tamperOffset = -1;
for (let index = 0; index < tampered.length - 2; index += 1) {
  if (tampered[index] === 0xb0 && tampered[index + 1] === 20 && tampered[index + 2] === 14) {
    tamperOffset = index;
    break;
  }
}
assert.ok(tamperOffset > 0);
tampered[tamperOffset + 2] = 15;
assert.throws(() => decodeMidi(tampered), /disagrees|inconsistent/);

function replaceNth(data, pattern, occurrence, replacement) {
  let seen = -1;
  for (let offset = 0; offset <= data.length - pattern.length; offset += 1) {
    if (pattern.every((byte, index) => data[offset + index] === byte)) {
      seen += 1;
      if (seen === occurrence) {
        data.set(replacement, offset);
        return;
      }
    }
  }
  throw new Error(`pattern occurrence ${occurrence} was not found`);
}

const stale = (await buildArtifacts("AAAAAA")).midi.slice();
replaceNth(stale, [0xb0, 20, 0], 1, Uint8Array.of(0xb0, 30, 0));
assert.throws(() => decodeMidi(stale), /missing or reordered|fresh/);

const mixedRecords = structuredClone(encodeRecords("AAA"));
mixedRecords[1].site_index = 16;
mixedRecords[1].codon = CODONS[16];
mixedRecords[1].event_index = eventIndexFromAddress(16, 1);
assert.throws(() => decodeRecords(mixedRecords), /one site index/);

const mixedMidi = (await buildArtifacts("AAA")).midi.slice();
replaceNth(mixedMidi, [0xb1, 20, 0], 0, Uint8Array.of(0xb1, 20, 16));
replaceNth(mixedMidi, [0xb1, 22, 1], 0, Uint8Array.of(0xb1, 22, 0));
replaceNth(mixedMidi, [0xb1, 23, 74], 0, Uint8Array.of(0xb1, 23, 16));
assert.throws(() => decodeMidi(mixedMidi), /one site index/);

const invalidRecord = structuredClone(artifacts.records[0]);
invalidRecord.base = "N";
assert.throws(() => createMidi([invalidRecord]), /invalid base/);

console.log(JSON.stringify({
  schema: "RSH-ETQ-DNA-MIDI-CROSS-RUNTIME-CONFORMANCE-V1",
  status: "PASS",
  contract: profile.contract,
  record_count: artifacts.records.length,
  hashes: profile.expected_hashes,
  round_trip_verified: true,
  claims: CLAIMS,
}, null, 2));
