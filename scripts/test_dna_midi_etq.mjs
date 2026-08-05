#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  CLAIMS,
  EVENT_COUNT,
  buildArtifacts,
  decodeMidi,
  decodeRecords,
  eventAddress,
  eventIndexFromAddress,
  normalizeSequence,
} from "../web/dna-midi/model.js";

const profilePath = process.argv[2] ?? "conformance/dna_midi_etq_exploratory_v1.json";
const profile = JSON.parse(await readFile(profilePath, "utf8"));
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

const visited = new Set();
for (let eventIndex = 0; eventIndex < EVENT_COUNT; eventIndex += 1) {
  const address = eventAddress(eventIndex);
  assert.equal(eventIndexFromAddress(address.siteIndex, address.fibreLabel), eventIndex);
  visited.add(`${address.siteIndex}:${address.fibreLabel}`);
}
assert.equal(visited.size, EVENT_COUNT);

assert.throws(() => normalizeSequence("ATG-NNN"), /invalid symbols/);
assert.throws(() => normalizeSequence("ATGC"), /multiple of 3/);

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

console.log(JSON.stringify({
  schema: "RSH-ETQ-DNA-MIDI-CROSS-RUNTIME-CONFORMANCE-V1",
  status: "PASS",
  contract: profile.contract,
  record_count: artifacts.records.length,
  hashes: profile.expected_hashes,
  round_trip_verified: true,
  claims: CLAIMS,
}, null, 2));
