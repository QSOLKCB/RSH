// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this file,
// You can obtain one at https://mozilla.org/MPL/2.0/.
// SPDX-License-Identifier: MPL-2.0
// Copyright (c) 2026 Trent Slade / QSOL-IMC.

export const CONTRACT = "RSH-ETQ-DNA-MIDI-EXPLORATORY-V1";
export const REPORT_SCHEMA = "RSH-ETQ-DNA-MIDI-REPORT-V1";
export const MANIFEST_SCHEMA = "RSH-ETQ-DNA-MIDI-MANIFEST-V1";
export const MIDI_SCHEMA_TEXT = CONTRACT;

export const BASES = "ACGT";
export const CODONS = Object.freeze(
  [...BASES].flatMap((a) => [...BASES].flatMap((b) => [...BASES].map((c) => a + b + c))),
);
const CODON_TO_INDEX = new Map(CODONS.map((codon, index) => [codon, index]));
const BASE_TO_DIGIT = new Map([...BASES].map((base, index) => [base, index]));

export const ETQ_SITE_COUNT = 101;
export const FIBRE_COUNT = 3;
export const EVENT_COUNT = 303;
export const MAX_SEQUENCE_BASES = 12_000;
export const MAX_INPUT_CHARACTERS = MAX_SEQUENCE_BASES * 4;
export const SCL_STENCIL = Object.freeze([1, -2, 1]);
export const PHASE_GAUSSIAN_EXPONENTS = Object.freeze([3, 2, 3]);
export const REGISTER_NAMES = Object.freeze(["Low", "Mid", "High"]);
const REGISTER_BASES = Object.freeze([36, 60, 84]);
const C_MAJOR = Object.freeze([0, 2, 4, 5, 7, 9, 11]);
const MIDI_METADATA_CONTROLS = Object.freeze([20, 21, 22, 23, 24, 74]);

const SQRT3 = Math.sqrt(3);
const SQRT_TWO_THIRDS = Math.sqrt(2 / 3);
export const TETRAHEDRON_VERTICES = Object.freeze({
  A: Object.freeze([0, 0, 0]),
  C: Object.freeze([1, 0, 0]),
  G: Object.freeze([0.5, SQRT3 / 2, 0]),
  T: Object.freeze([0.5, SQRT3 / 6, SQRT_TWO_THIRDS]),
});
export const TETRAHEDRON_CENTROID = Object.freeze([0, 1, 2].map((axis) => (
  Object.values(TETRAHEDRON_VERTICES)
    .reduce((sum, vertex) => sum + vertex[axis], 0) / 4
)));

export const CLAIMS = Object.freeze({
  physical_dna_storage_demonstrated: false,
  biological_error_correction_demonstrated: false,
  sierpinski_embedding_is_physical_geometry: false,
  etq_canonical_dna_mapping: false,
  actual_multi_device_execution: false,
  distributed_execution: false,
  geometry_receipt_authority: false,
});

export const CSV_FIELDS = Object.freeze([
  "base_index", "codon_index", "codon", "codon_offset", "base", "site_index",
  "fibre_label", "event_index", "register", "midi_channel", "midi_pitch",
  "scl_value", "phase_gaussian_exponent", "x", "y", "z",
]);

export function modulo(value, modulus) {
  if (!Number.isSafeInteger(value) || !Number.isSafeInteger(modulus) || modulus <= 0) {
    throw new RangeError("modulo requires safe integers and a positive modulus");
  }
  return ((value % modulus) + modulus) % modulus;
}

export function eventIndexFromAddress(siteIndex, fibreLabel) {
  if (!Number.isSafeInteger(siteIndex) || siteIndex < 0 || siteIndex >= ETQ_SITE_COUNT) {
    throw new RangeError("siteIndex must be in [0, 100]");
  }
  if (!Number.isSafeInteger(fibreLabel) || fibreLabel < 0 || fibreLabel >= FIBRE_COUNT) {
    throw new RangeError("fibreLabel must be in [0, 2]");
  }
  const k = modulo(2 * (fibreLabel - modulo(siteIndex, FIBRE_COUNT)), FIBRE_COUNT);
  const eventIndex = siteIndex + ETQ_SITE_COUNT * k;
  if (eventIndex >= EVENT_COUNT) throw new Error("CRT inverse escaped ETQ-303 domain");
  return eventIndex;
}

export function eventAddress(eventIndex) {
  if (!Number.isSafeInteger(eventIndex) || eventIndex < 0 || eventIndex >= EVENT_COUNT) {
    throw new RangeError("eventIndex must be in [0, 302]");
  }
  return { siteIndex: eventIndex % ETQ_SITE_COUNT, fibreLabel: eventIndex % FIBRE_COUNT };
}

export function normalizeSequence(sequence) {
  if (typeof sequence !== "string") throw new TypeError("DNA sequence must be text");
  if (sequence.length > MAX_INPUT_CHARACTERS) {
    throw new Error(`DNA input text exceeds the ${MAX_INPUT_CHARACTERS}-character safety limit`);
  }
  const compact = sequence.toUpperCase().replace(/\s/g, "");
  if (compact.length > MAX_SEQUENCE_BASES) {
    throw new Error(`DNA sequence exceeds the ${MAX_SEQUENCE_BASES}-base safety limit`);
  }
  const invalid = [...new Set([...compact].filter((base) => !BASES.includes(base)))].sort();
  if (invalid.length > 0) throw new Error(`DNA sequence contains invalid symbols: ${invalid.join("")}`);
  if (compact.length === 0) throw new Error("DNA sequence must contain at least one codon");
  if (compact.length % 3 !== 0) {
    throw new Error("DNA sequence length must be a multiple of 3; incomplete codons are rejected");
  }
  return compact;
}

function codonSiteIndex(codon) {
  const index = CODON_TO_INDEX.get(codon);
  if (index === undefined) throw new Error(`invalid codon: ${codon}`);
  return index;
}

export function midiPitch(siteIndex, fibreLabel) {
  const pitch = REGISTER_BASES[fibreLabel]
    + C_MAJOR[siteIndex % C_MAJOR.length]
    + 12 * (Math.floor(siteIndex / 7) % 2);
  return Math.max(0, Math.min(127, pitch));
}

function decimal12(value) {
  return value.toFixed(12);
}

export function tetrahedralPath(sequence) {
  const point = [...TETRAHEDRON_CENTROID];
  const points = [];
  for (const base of sequence) {
    const vertex = TETRAHEDRON_VERTICES[base];
    for (let axis = 0; axis < 3; axis += 1) point[axis] = (point[axis] + vertex[axis]) / 2;
    points.push(point.map(decimal12));
  }
  return points;
}

export function encodeRecords(input) {
  const sequence = normalizeSequence(input);
  const coordinates = tetrahedralPath(sequence);
  return [...sequence].map((base, baseIndex) => {
    const codonStart = Math.floor(baseIndex / 3) * 3;
    const codon = sequence.slice(codonStart, codonStart + 3);
    const siteIndex = codonSiteIndex(codon);
    const fibreLabel = baseIndex % 3;
    const [x, y, z] = coordinates[baseIndex];
    return {
      base_index: baseIndex,
      codon_index: Math.floor(baseIndex / 3),
      codon,
      codon_offset: fibreLabel,
      base,
      site_index: siteIndex,
      fibre_label: fibreLabel,
      event_index: eventIndexFromAddress(siteIndex, fibreLabel),
      register: REGISTER_NAMES[fibreLabel],
      midi_channel: fibreLabel,
      midi_pitch: midiPitch(siteIndex, fibreLabel),
      scl_value: SCL_STENCIL[fibreLabel],
      phase_gaussian_exponent: PHASE_GAUSSIAN_EXPONENTS[fibreLabel],
      x,
      y,
      z,
    };
  });
}

export function decodeRecords(records) {
  if (!Array.isArray(records) || records.length === 0 || records.length % 3 !== 0) {
    throw new Error("record count must contain complete codons");
  }
  let codonSite = null;
  return records.map((record, expectedIndex) => {
    const base = String(record.base);
    if (!BASES.includes(base)) throw new Error("record contains an invalid base");
    if (Number(record.base_index) !== expectedIndex) throw new Error("record ordering is not canonical");
    const expectedCodonIndex = Math.floor(expectedIndex / 3);
    if (Number(record.codon_index) !== expectedCodonIndex) {
      throw new Error("record codon index is not canonical");
    }
    const siteIndex = Number(record.site_index);
    const fibreLabel = Number(record.fibre_label);
    const eventIndex = Number(record.event_index);
    if (Number(record.codon_offset) !== fibreLabel) {
      throw new Error("record codon offset disagrees with fibre label");
    }
    if (fibreLabel !== expectedIndex % 3) throw new Error("record fibre label does not match codon offset");
    if (!Number.isSafeInteger(siteIndex) || siteIndex < 0 || siteIndex >= CODONS.length) {
      throw new Error("record codon site is out of range");
    }
    if (fibreLabel === 0) codonSite = siteIndex;
    else if (siteIndex !== codonSite) throw new Error("records within a codon must use one site index");
    if (String(record.codon) !== CODONS[siteIndex]) {
      throw new Error("record codon text disagrees with site index");
    }
    if (eventIndexFromAddress(siteIndex, fibreLabel) !== eventIndex) {
      throw new Error("record ETQ event index is inconsistent");
    }
    if (CODONS[siteIndex][fibreLabel] !== base) {
      throw new Error("record base does not match codon site and fibre");
    }
    return base;
  }).join("");
}

function vlq(value) {
  if (!Number.isSafeInteger(value) || value < 0) throw new RangeError("VLQ value must be nonnegative");
  const output = [value & 0x7f];
  let remaining = value >> 7;
  while (remaining > 0) {
    output.unshift((remaining & 0x7f) | 0x80);
    remaining >>= 7;
  }
  return output;
}

function readVlq(data, initialOffset) {
  let offset = initialOffset;
  let value = 0;
  for (let count = 0; count < 4; count += 1) {
    if (offset >= data.length) throw new Error("truncated MIDI VLQ");
    const byte = data[offset];
    offset += 1;
    value = (value << 7) | (byte & 0x7f);
    if ((byte & 0x80) === 0) return { value, offset };
  }
  throw new Error("MIDI VLQ exceeds four bytes");
}

function asciiBytes(text) {
  return Uint8Array.from([...text].map((character) => character.charCodeAt(0)));
}

function concatBytes(parts) {
  const size = parts.reduce((sum, part) => sum + part.length, 0);
  const output = new Uint8Array(size);
  let offset = 0;
  for (const part of parts) {
    output.set(part, offset);
    offset += part.length;
  }
  return output;
}

function uint16be(value) {
  return Uint8Array.of((value >> 8) & 0xff, value & 0xff);
}

function uint32be(value) {
  return Uint8Array.of((value >>> 24) & 0xff, (value >>> 16) & 0xff, (value >>> 8) & 0xff, value & 0xff);
}

export function createMidi(records) {
  const events = [];
  const schemaBytes = asciiBytes(MIDI_SCHEMA_TEXT);
  events.push({ tick: 0, priority: 0, payload: Uint8Array.of(0xff, 0x03, ...vlq(schemaBytes.length), ...schemaBytes) });
  events.push({ tick: 0, priority: 0, payload: Uint8Array.of(0xff, 0x51, 0x03, 0x07, 0xa1, 0x20) });

  for (const record of records) {
    const startTick = Number(record.base_index) * 120;
    const channel = Number(record.midi_channel);
    const siteIndex = Number(record.site_index);
    const baseDigit = BASE_TO_DIGIT.get(String(record.base));
    if (baseDigit === undefined) throw new Error("record contains an invalid base");
    const eventIndex = Number(record.event_index);
    const phase = Number(record.phase_gaussian_exponent);
    const pitch = Number(record.midi_pitch);
    const scl = Number(record.scl_value);
    const velocity = scl < 0 ? 104 : 82;
    const duration = scl < 0 ? 240 : 180;
    const controls = [
      [20, siteIndex], [21, baseDigit], [22, Math.floor(eventIndex / 128)],
      [23, eventIndex % 128], [24, phase], [74, phase === 2 ? 64 : 96],
    ];
    for (const [control, value] of controls) {
      events.push({ tick: startTick, priority: 2, payload: Uint8Array.of(0xb0 | channel, control, value) });
    }
    events.push({ tick: startTick, priority: 3, payload: Uint8Array.of(0x90 | channel, pitch, velocity) });
    events.push({ tick: startTick + duration, priority: 1, payload: Uint8Array.of(0x80 | channel, pitch, 0) });
  }

  events.sort((left, right) => left.tick - right.tick
    || left.priority - right.priority
    || compareBytes(left.payload, right.payload));
  const trackParts = [];
  let previousTick = 0;
  for (const event of events) {
    trackParts.push(Uint8Array.from(vlq(event.tick - previousTick)), event.payload);
    previousTick = event.tick;
  }
  trackParts.push(Uint8Array.of(0x00, 0xff, 0x2f, 0x00));
  const track = concatBytes(trackParts);
  return concatBytes([
    asciiBytes("MThd"), uint32be(6), uint16be(0), uint16be(1), uint16be(480),
    asciiBytes("MTrk"), uint32be(track.length), track,
  ]);
}

function compareBytes(left, right) {
  const length = Math.min(left.length, right.length);
  for (let index = 0; index < length; index += 1) {
    if (left[index] !== right[index]) return left[index] - right[index];
  }
  return left.length - right.length;
}

function readUint16be(data, offset) {
  return (data[offset] << 8) | data[offset + 1];
}

function readUint32be(data, offset) {
  return ((data[offset] * 0x1000000) + (data[offset + 1] << 16)
    + (data[offset + 2] << 8) + data[offset + 3]) >>> 0;
}

function asciiString(data) {
  return String.fromCharCode(...data);
}

export function decodeMidi(input) {
  const midi = input instanceof Uint8Array ? input : new Uint8Array(input);
  if (midi.length < 22 || asciiString(midi.slice(0, 4)) !== "MThd") throw new Error("not a MIDI file");
  const headerLength = readUint32be(midi, 4);
  if (headerLength !== 6) throw new Error("unsupported MIDI header length");
  if (readUint16be(midi, 8) !== 0) throw new Error("only format-0 MIDI is supported");
  if (readUint16be(midi, 10) !== 1) throw new Error("MIDI must contain exactly one track");
  if (readUint16be(midi, 12) !== 480) throw new Error("MIDI division must be 480 PPQ");
  const trackOffset = 8 + headerLength;
  if (trackOffset + 8 > midi.length || asciiString(midi.slice(trackOffset, trackOffset + 4)) !== "MTrk") {
    throw new Error("MIDI track chunk is missing");
  }
  const trackLength = readUint32be(midi, trackOffset + 4);
  const track = midi.slice(trackOffset + 8, trackOffset + 8 + trackLength);
  if (track.length !== trackLength) throw new Error("truncated MIDI track");

  let offset = 0;
  let absoluteTick = 0;
  let runningStatus = null;
  const controls = Array.from({ length: 16 }, () => ({ order: [], values: new Map() }));
  const decoded = [];
  let schemaSeen = false;

  while (offset < track.length) {
    const delta = readVlq(track, offset);
    absoluteTick += delta.value;
    offset = delta.offset;
    if (offset >= track.length) throw new Error("truncated MIDI event");
    let status = track[offset];
    if (status < 0x80) {
      if (runningStatus === null) throw new Error("MIDI running status has no predecessor");
      status = runningStatus;
    } else {
      offset += 1;
      if (status < 0xf0) runningStatus = status;
    }

    if (status === 0xff) {
      if (offset >= track.length) throw new Error("truncated MIDI meta event");
      const metaType = track[offset];
      offset += 1;
      const length = readVlq(track, offset);
      offset = length.offset;
      const payload = track.slice(offset, offset + length.value);
      offset += length.value;
      if (payload.length !== length.value) throw new Error("truncated MIDI meta payload");
      if (metaType === 0x03 && asciiString(payload) === MIDI_SCHEMA_TEXT) schemaSeen = true;
      if (metaType === 0x2f) break;
      continue;
    }

    const messageType = status & 0xf0;
    const channel = status & 0x0f;
    const dataLength = messageType === 0xc0 || messageType === 0xd0 ? 1 : 2;
    if (offset + dataLength > track.length) throw new Error("truncated MIDI channel event");
    const data1 = track[offset];
    const data2 = dataLength === 2 ? track[offset + 1] : 0;
    offset += dataLength;
    if (messageType === 0xb0) {
      const state = controls[channel];
      const expectedControl = MIDI_METADATA_CONTROLS[state.order.length];
      if (expectedControl === undefined) throw new Error("MIDI note has excess metadata controls");
      if (data1 !== expectedControl) throw new Error("MIDI metadata controls are missing or reordered");
      state.order.push(data1);
      state.values.set(data1, data2);
    }
    if (messageType === 0x90 && data2 > 0) {
      const state = controls[channel];
      if (state.order.length !== MIDI_METADATA_CONTROLS.length
          || state.order.some((control, index) => control !== MIDI_METADATA_CONTROLS[index])) {
        throw new Error("MIDI note is missing fresh DNA metadata controls");
      }
      decoded.push({
        tick: absoluteTick,
        fibreLabel: channel,
        siteIndex: state.values.get(20),
        baseDigit: state.values.get(21),
        eventIndex: state.values.get(22) * 128 + state.values.get(23),
      });
      controls[channel] = { order: [], values: new Map() };
    }
  }

  if (!schemaSeen) throw new Error("MIDI schema marker is missing");
  if (decoded.length === 0 || decoded.length % 3 !== 0) throw new Error("MIDI note count does not contain complete codons");
  let previousTick = -1;
  let codonSite = null;
  return decoded.map((record, recordIndex) => {
    if (record.tick <= previousTick) throw new Error("MIDI DNA note ordering is not strictly increasing");
    previousTick = record.tick;
    if (record.fibreLabel !== recordIndex % 3) throw new Error("MIDI channel does not match codon offset");
    if (!Number.isSafeInteger(record.siteIndex) || record.siteIndex < 0 || record.siteIndex >= CODONS.length) {
      throw new Error("MIDI codon index is out of range");
    }
    if (!Number.isSafeInteger(record.baseDigit) || record.baseDigit < 0 || record.baseDigit >= BASES.length) {
      throw new Error("MIDI base digit is out of range");
    }
    if (record.fibreLabel === 0) codonSite = record.siteIndex;
    else if (record.siteIndex !== codonSite) {
      throw new Error("MIDI notes within a codon must use one site index");
    }
    if (eventIndexFromAddress(record.siteIndex, record.fibreLabel) !== record.eventIndex) {
      throw new Error("MIDI ETQ event index is inconsistent");
    }
    const base = BASES[record.baseDigit];
    if (CODONS[record.siteIndex][record.fibreLabel] !== base) {
      throw new Error("MIDI base metadata disagrees with codon site");
    }
    return base;
  }).join("");
}

export function reportFor(sequence, records) {
  return {
    schema: REPORT_SCHEMA,
    contract: CONTRACT,
    input: {
      dna_sequence: sequence,
      base_count: sequence.length,
      codon_count: sequence.length / 3,
      alphabet: BASES,
      incomplete_codon_policy: "reject",
    },
    etq_mapping: {
      site_domain: "alphabetic-codon-index-0-to-63-within-etq-site-domain-0-to-100",
      fibre_semantics: "codon-offset-0-1-2",
      event_formula: "n=j+101*((2*(a-(j mod 3))) mod 3)",
      event_count: EVENT_COUNT,
      scl_stencil: [...SCL_STENCIL],
      phase_gaussian_exponents: [...PHASE_GAUSSIAN_EXPONENTS],
    },
    tetrahedral_embedding: {
      construction: "global-sierpinski-tetrahedron-ifs",
      recurrence: "p_next=(p_current+vertex(base))/2",
      initial_point: TETRAHEDRON_CENTROID.map(decimal12),
      vertices: Object.fromEntries(Object.entries(TETRAHEDRON_VERTICES)
        .map(([base, vertex]) => [base, vertex.map(decimal12)])),
      coordinate_encoding: "fixed-decimal-12",
    },
    midi: {
      format: 0,
      tracks: 1,
      ppq: 480,
      tempo_bpm: 120,
      metadata_controls: {
        cc20: "codon-site-index",
        cc21: "base-digit-A0-C1-G2-T3",
        cc22: "event-index-msb-base128",
        cc23: "event-index-lsb-base128",
        cc24: "phase-gaussian-exponent",
        cc74: "audible-phase-brightness",
      },
    },
    records,
    claims: { ...CLAIMS },
  };
}

function stableObject(value) {
  if (Array.isArray(value)) return value.map(stableObject);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stableObject(value[key])]));
  }
  return value;
}

export function canonicalJson(value) {
  return JSON.stringify(stableObject(value));
}

function csvEscape(value) {
  const text = String(value);
  return /[",\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

export function csvText(records) {
  const lines = [CSV_FIELDS.join(",")];
  for (const record of records) lines.push(CSV_FIELDS.map((field) => csvEscape(record[field])).join(","));
  return `${lines.join("\n")}\n`;
}

export async function sha256Hex(input) {
  const bytes = typeof input === "string" ? new TextEncoder().encode(input) : input;
  if (!globalThis.crypto?.subtle) throw new Error("Web Crypto SHA-256 is unavailable");
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function buildArtifacts(input) {
  const sequence = normalizeSequence(input);
  const records = encodeRecords(sequence);
  if (decodeRecords(records) !== sequence) throw new Error("record round-trip failed");
  const midi = createMidi(records);
  if (decodeMidi(midi) !== sequence) throw new Error("MIDI round-trip failed");
  const report = reportFor(sequence, records);
  const reportCanonical = canonicalJson(report);
  const csv = csvText(records);
  const manifest = {
    schema: MANIFEST_SCHEMA,
    contract: CONTRACT,
    sequence_sha256: await sha256Hex(sequence),
    report_canonical_sha256: await sha256Hex(reportCanonical),
    csv_sha256: await sha256Hex(csv),
    midi_sha256: await sha256Hex(midi),
    record_count: records.length,
    round_trip_verified: true,
    claims: { ...CLAIMS },
  };
  return { sequence, records, report, reportCanonical, csv, midi, manifest };
}
