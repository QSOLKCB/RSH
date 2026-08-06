// This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
// SPDX-License-Identifier: MPL-2.0
import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const source = await fs.readFile(path.join(root, "web/genomic-spectrum/model.js"), "utf8");
const model = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
const profile = JSON.parse(await fs.readFile(path.join(root, "conformance/genomic_spectral_v1_606.json"), "utf8"));
const hash = value => crypto.createHash("sha256").update(value).digest("hex");

assert.equal(await model.refgetAccession("ACGT"), "SQ.aKF498dAxcJAqme6QYQ7EZ07-fiw8Kw2");
const events = new Set(Array.from({ length: 303 }, (_, i) => model.etqAddressForOffset(i).event_index));
assert.equal(events.size, 303);

const result = await model.buildReport(
  profile.fasta,
  profile.vcf,
  profile.window_size,
  profile.stride,
  profile.frame_origin_1based,
);
const reportBytes = model.utf8(model.canonicalJson(result.report));
const actual = {
  report_canonical_sha256: hash(reportBytes),
  windows_csv_sha256: hash(result.windowsCsv),
  variants_csv_sha256: hash(result.variantsCsv),
  midi_sha256: hash(result.midi),
};
assert.deepEqual(actual, profile.expected_hashes);
assert.deepEqual(result.report.claims, profile.expected_claims);
assert.ok(Object.values(result.report.claims).every(value => value === false));
assert.equal(result.report.input.refget_accession, profile.expected.refget_accession);
assert.deepEqual(result.report.variants.map(v => v.frame_relative_effect), profile.expected.variant_effects);
assert.deepEqual(result.report.variants.map(v => v.substitution_class), profile.expected.substitution_classes);

assert.throws(() => model.parseFasta(">one\nACGT\n>two\nACGT\n"));
assert.throws(() => model.parseVcf(profile.vcf.replace("\tG\tT\t", "\tG\tTA\t"), "synthetic_chr", model.parseFasta(profile.fasta).sequence));
const tampered = new Uint8Array(result.midi);
tampered[tampered.length - 1] ^= 1;
assert.notEqual(hash(tampered), profile.expected_hashes.midi_sha256);
console.log(JSON.stringify({ contract: model.CONTRACT, hashes: actual, status: "PASS" }, null, 2));
