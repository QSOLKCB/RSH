// This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
// SPDX-License-Identifier: MPL-2.0
export const CONTRACT = "RSH-ETQ-GENOMIC-SPECTRAL-V1";
export const REPORT_SCHEMA = "RSH-ETQ-GENOMIC-SPECTRAL-REPORT-V1";
export const MANIFEST_SCHEMA = "RSH-ETQ-GENOMIC-SPECTRAL-MANIFEST-V1";
export const PROFILE_SCHEMA = "RSH-ETQ-GENOMIC-SPECTRAL-CONFORMANCE-V1";
export const CANONICAL_BASES = "ACGT";
export const IUPAC_DNA = "ACGTRYSWKMBDHVN";
export const MAX_FASTA_CHARACTERS = 2_000_000;
export const MAX_SEQUENCE_BASES = 1_000_000;
export const MAX_VCF_CHARACTERS = 2_000_000;
export const MAX_WINDOW_COUNT = 4_096;
export const MAX_VARIANT_COUNT = 4_096;
export const MIDI_PPQ = 480;
export const MIDI_TEMPO_BPM = 120;
const ETQ_SITE_COUNT = 101;
const EVENT_COUNT = 303;
const SCL_STENCIL = [1, -2, 1];
const PERIOD3_RE2_WEIGHTS = [2, -1, -1];
const PERIOD3_IM_WEIGHTS = [0, 1, -1];
const REGISTER_NAMES = ["Low", "Mid", "High"];
const REGISTER_BASES = [36, 60, 84];
const C_MAJOR = [0, 2, 4, 5, 7, 9, 11];
const COMPLEMENT = Object.fromEntries([..."ACGTRYSWKMBDHVN"].map((base, index) => [base, "TGCAYRSWMKVHDBN"[index]]));
const DINUCLEOTIDES = [...CANONICAL_BASES].flatMap(a => [...CANONICAL_BASES].map(b => a + b));
const TRINUCLEOTIDES = [...CANONICAL_BASES].flatMap(a => [...CANONICAL_BASES].flatMap(b => [...CANONICAL_BASES].map(c => a + b + c)));
const TRANSITIONS = new Set(["AG", "GA", "CT", "TC"]);
const STANDARD_CODE = {
  TTT:"F",TTC:"F",TTA:"L",TTG:"L",TCT:"S",TCC:"S",TCA:"S",TCG:"S",
  TAT:"Y",TAC:"Y",TAA:"*",TAG:"*",TGT:"C",TGC:"C",TGA:"*",TGG:"W",
  CTT:"L",CTC:"L",CTA:"L",CTG:"L",CCT:"P",CCC:"P",CCA:"P",CCG:"P",
  CAT:"H",CAC:"H",CAA:"Q",CAG:"Q",CGT:"R",CGC:"R",CGA:"R",CGG:"R",
  ATT:"I",ATC:"I",ATA:"I",ATG:"M",ACT:"T",ACC:"T",ACA:"T",ACG:"T",
  AAT:"N",AAC:"N",AAA:"K",AAG:"K",AGT:"S",AGC:"S",AGA:"R",AGG:"R",
  GTT:"V",GTC:"V",GTA:"V",GTG:"V",GCT:"A",GCC:"A",GCA:"A",GCG:"A",
  GAT:"D",GAC:"D",GAA:"E",GAG:"E",GGT:"G",GGC:"G",GGA:"G",GGG:"G",
};
export const CLAIMS = Object.freeze({
  actual_multi_device_execution: false,
  biological_function_inferred: false,
  clinical_variant_interpretation: false,
  coding_region_annotation_authority: false,
  distributed_execution: false,
  etq_canonical_genomic_mapping: false,
  gene_prediction_demonstrated: false,
  geometry_receipt_authority: false,
  physical_dna_storage_demonstrated: false,
  spectral_feature_is_diagnostic: false,
});
const WINDOW_CSV_FIELDS = [
  "window_index", "start_1based", "end_1based_inclusive", "length", "callable_bases",
  "ambiguous_bases", "a_count", "c_count", "g_count", "t_count", "gc_numerator",
  "gc_denominator", "cpg_count", "period3_scaled_power", "scl_energy", "dominant_base",
  "etq_site", "etq_fibre", "etq_event", "midi_channel", "midi_pitch", "midi_velocity",
  "midi_brightness", "midi_scl_controller",
];
const VARIANT_CSV_FIELDS = [
  "chrom", "position_1based", "id", "ref", "alt", "substitution_class", "context_3mer",
  "etq_site", "etq_fibre", "etq_event", "window_index", "period3_scaled_power_delta",
  "scl_energy_delta", "gc_count_delta", "cpg_count_delta", "reference_codon", "alternate_codon",
  "reference_amino_acid", "alternate_amino_acid", "frame_relative_effect",
];

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
function sortValue(value) {
  if (Array.isArray(value)) return value.map(sortValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, sortValue(value[key])]));
  }
  return value;
}
export function canonicalJson(value) { return JSON.stringify(sortValue(value)); }
export function utf8(text) { return new TextEncoder().encode(text); }
function bytesToHex(bytes) { return [...bytes].map(value => value.toString(16).padStart(2, "0")).join(""); }
export async function sha256Hex(data) {
  const bytes = typeof data === "string" ? utf8(data) : data;
  return bytesToHex(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)));
}
export async function refgetAccession(sequence) {
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-512", utf8(sequence))).slice(0, 24);
  let binary = "";
  for (const byte of digest) binary += String.fromCharCode(byte);
  return "SQ." + btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}
function trimBlankEdges(lines) {
  while (lines.length && !lines[0].trim()) lines.shift();
  while (lines.length && !lines.at(-1).trim()) lines.pop();
  return lines;
}
export function parseFasta(text) {
  assert(typeof text === "string", "FASTA input must be text");
  assert(text.length <= MAX_FASTA_CHARACTERS, `FASTA input exceeds the ${MAX_FASTA_CHARACTERS}-character safety limit`);
  const lines = trimBlankEdges(text.split(/\r?\n/));
  const headers = lines.map((line, index) => line.startsWith(">") ? index : -1).filter(index => index >= 0);
  assert(headers.length <= 1, "exactly one FASTA record is supported");
  let recordId;
  let description;
  let sequenceLines;
  if (headers.length === 1) {
    assert(headers[0] === 0, "FASTA definition line must be the first nonempty content");
    description = lines[0].slice(1).trim();
    assert(description.length > 0, "FASTA definition line must contain an identifier");
    recordId = description.split(/\s+/)[0];
    sequenceLines = lines.slice(1);
  } else {
    recordId = "sequence";
    description = "sequence";
    sequenceLines = lines;
  }
  const sequence = sequenceLines.join("").toUpperCase().replace(/\s/g, "");
  assert(sequence.length > 0, "sequence must not be empty");
  assert(sequence.length <= MAX_SEQUENCE_BASES, `sequence exceeds the ${MAX_SEQUENCE_BASES}-base safety limit`);
  const invalid = [...new Set([...sequence].filter(base => !IUPAC_DNA.includes(base)))].sort();
  assert(invalid.length === 0, `sequence contains invalid IUPAC DNA symbols: ${invalid.join("")}`);
  return { recordId, description, sequence };
}
export function strandComplement(sequence) {
  return [...sequence].reduceRight((output, base) => output + COMPLEMENT[base], "");
}
export function eventIndexFromAddress(siteIndex, fibreLabel) {
  const fibreCount = 3;
  assert(Number.isInteger(siteIndex) && siteIndex >= 0 && siteIndex < ETQ_SITE_COUNT, `site_index must be in [0, ${ETQ_SITE_COUNT - 1}]`);
  assert(Number.isInteger(fibreLabel) && fibreLabel >= 0 && fibreLabel < fibreCount, `fibre_label must be in [0, ${fibreCount - 1}]`);
  return siteIndex + ETQ_SITE_COUNT * (((2 * (fibreLabel - (siteIndex % fibreCount))) % fibreCount + fibreCount) % fibreCount);
}
export function etqAddressForOffset(offset0) {
  assert(Number.isInteger(offset0) && offset0 >= 0, "offset must be nonnegative");
  const eventIndex = offset0 % EVENT_COUNT;
  const siteIndex = eventIndex % ETQ_SITE_COUNT;
  const fibreLabel = eventIndex % 3;
  assert(eventIndexFromAddress(siteIndex, fibreLabel) === eventIndex, "ETQ CRT address invariant failed");
  return { site_index: siteIndex, fibre_label: fibreLabel, event_index: eventIndex };
}
function countKmers(sequence, k, vocabulary) {
  const counts = Object.fromEntries(vocabulary.map(word => [word, 0]));
  let valid = 0;
  for (let index = 0; index <= sequence.length - k; index += 1) {
    const word = sequence.slice(index, index + k);
    if ([...word].every(base => CANONICAL_BASES.includes(base))) {
      counts[word] += 1;
      valid += 1;
    }
  }
  return [counts, valid];
}
function period3Channel(sequence, base) {
  let re2 = 0;
  let im = 0;
  [...sequence].forEach((symbol, index) => {
    if (symbol === base) {
      re2 += PERIOD3_RE2_WEIGHTS[index % 3];
      im += PERIOD3_IM_WEIGHTS[index % 3];
    }
  });
  return { re2, im_sqrt3_coefficient: im, scaled_power: re2 * re2 + 3 * im * im };
}
function sclChannelEnergy(sequence, base) {
  const values = [...sequence].map(symbol => symbol === base ? 1 : 0);
  let energy = 0;
  for (let index = 0; index <= values.length - 3; index += 1) {
    const value = values[index] - 2 * values[index + 1] + values[index + 2];
    energy += value * value;
  }
  return energy;
}
function integerSqrt(value) {
  assert(Number.isSafeInteger(value) && value >= 0, "integer square root requires a nonnegative safe integer");
  return Math.floor(Math.sqrt(value));
}
function midiPitch(siteIndex, fibreLabel) {
  const pitch = REGISTER_BASES[fibreLabel] + C_MAJOR[siteIndex % 7] + 12 * (Math.floor(siteIndex / 7) % 2);
  return Math.min(127, Math.max(0, pitch));
}
function fraction(numerator, denominator) { return { numerator, denominator }; }
export async function analyzeWindow(sequence, windowIndex, start0, end0) {
  const window = sequence.slice(start0, end0);
  const counts = Object.fromEntries([...CANONICAL_BASES].map(base => [base, [...window].filter(symbol => symbol === base).length]));
  const callableCount = Object.values(counts).reduce((total, value) => total + value, 0);
  const ambiguousCount = window.length - callableCount;
  const [dinucleotides, validDinucleotides] = countKmers(window, 2, DINUCLEOTIDES);
  const [trinucleotides, validTrinucleotides] = countKmers(window, 3, TRINUCLEOTIDES);
  const period3 = Object.fromEntries([...CANONICAL_BASES].map(base => [base, period3Channel(window, base)]));
  const scl = Object.fromEntries([...CANONICAL_BASES].map(base => [base, sclChannelEnergy(window, base)]));
  const period3Total = Object.values(period3).reduce((total, channel) => total + channel.scaled_power, 0);
  const sclTotal = Object.values(scl).reduce((total, value) => total + value, 0);
  const maxCount = callableCount ? Math.max(...Object.values(counts)) : 0;
  const dominant = callableCount ? ([...CANONICAL_BASES].find(base => counts[base] === maxCount) ?? null) : null;
  const address = etqAddressForOffset(start0);
  const gcCount = counts.G + counts.C;
  const gcDenominator = callableCount;
  const receiver = {
    register: REGISTER_NAMES[address.fibre_label],
    midi_channel: address.fibre_label,
    midi_pitch: midiPitch(address.site_index, address.fibre_label),
    midi_velocity: Math.min(127, 32 + integerSqrt(period3Total)),
    midi_brightness_cc74: gcDenominator === 0 ? 0 : Math.floor((127 * gcCount) / gcDenominator),
    midi_scl_cc71: Math.min(127, integerSqrt(sclTotal * 16)),
    duration_ticks: 120 + Math.min(840, dinucleotides.CG * 30 + ambiguousCount * 10),
  };
  return {
    window_index: windowIndex,
    start_1based: start0 + 1,
    end_1based_inclusive: end0,
    length: window.length,
    sequence_sha256: await sha256Hex(window),
    counts: { ...counts, ambiguous: ambiguousCount, callable: callableCount },
    gc_fraction: fraction(gcCount, gcDenominator),
    gc_skew: fraction(counts.G - counts.C, counts.G + counts.C),
    at_skew: fraction(counts.A - counts.T, counts.A + counts.T),
    cpg_count: dinucleotides.CG,
    dinucleotide_valid_count: validDinucleotides,
    dinucleotide_counts: dinucleotides,
    trinucleotide_valid_count: validTrinucleotides,
    trinucleotide_counts: trinucleotides,
    period3_exact: {
      definition: "four-times-unnormalized-voss-dft-power-at-frequency-one-third",
      channels: period3,
      total_scaled_power: period3Total,
    },
    scl_exact: { stencil: [...SCL_STENCIL], channel_energy: scl, total_energy: sclTotal },
    dominant_base: dominant,
    etq_address: address,
    spectral_receiver: receiver,
  };
}
function windowCount(sequenceLength, windowSize, stride) {
  if (sequenceLength <= windowSize) return 1;
  return 1 + Math.ceil((sequenceLength - windowSize) / stride);
}
export async function buildWindows(sequence, windowSize = 303, stride = windowSize) {
  assert(Number.isInteger(windowSize) && windowSize >= 3 && windowSize <= 4095, "window_size must be an integer in [3, 4095]");
  assert(Number.isInteger(stride) && stride >= 1 && stride <= windowSize, "stride must be an integer in [1, window_size]");
  const count = windowCount(sequence.length, windowSize, stride);
  assert(count <= MAX_WINDOW_COUNT, `analysis would create ${count} windows; limit is ${MAX_WINDOW_COUNT}`);
  const windows = [];
  for (let start0 = 0, windowIndex = 0; start0 < sequence.length; start0 += stride, windowIndex += 1) {
    const end0 = Math.min(sequence.length, start0 + windowSize);
    windows.push(await analyzeWindow(sequence, windowIndex, start0, end0));
    if (end0 === sequence.length) break;
  }
  return windows;
}
export function parseVcf(text, recordId, sequence) {
  if (!text) return [];
  assert(typeof text === "string", "VCF input must be text");
  assert(text.length <= MAX_VCF_CHARACTERS, `VCF input exceeds the ${MAX_VCF_CHARACTERS}-character safety limit`);
  const variants = [];
  const seenLoci = new Set();
  let formatSeen = false;
  let headerSeen = false;
  const lines = text.split(/\r?\n/);
  lines.forEach((raw, zeroIndex) => {
    const lineNumber = zeroIndex + 1;
    const line = raw.trim();
    if (!line) return;
    if (line.startsWith("##")) {
      if (line.startsWith("##fileformat=")) {
        assert(!formatSeen, "VCF fileformat declaration is duplicated");
        assert(line === "##fileformat=VCFv4.5", "VCF fileformat must be exactly VCFv4.5");
        formatSeen = true;
      }
      return;
    }
    if (line.startsWith("#CHROM")) {
      assert(!headerSeen, "VCF #CHROM header is duplicated");
      const columns = line.split("\t");
      assert(JSON.stringify(columns) === JSON.stringify(["#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO"]), "VCF header must contain exactly the canonical eight columns");
      assert(formatSeen, "VCF 4.5 fileformat declaration must precede the #CHROM header");
      headerSeen = true;
      return;
    }
    assert(!line.startsWith("#"), `unsupported VCF header at line ${lineNumber}`);
    assert(headerSeen, "VCF data requires a #CHROM header");
    const columns = line.split("\t");
    assert(columns.length === 8, `VCF record at line ${lineNumber} must contain exactly eight columns`);
    const [chrom, posText, id, ref, alt, qual, filter, info] = columns;
    assert(chrom === recordId, `VCF CHROM ${JSON.stringify(chrom)} does not match FASTA record ${JSON.stringify(recordId)}`);
    assert(!alt.includes(",") && ref.length === 1 && alt.length === 1 && CANONICAL_BASES.includes(ref) && CANONICAL_BASES.includes(alt), "only biallelic A/C/G/T SNVs are supported");
    assert(ref !== alt, "VCF REF and ALT must differ");
    const position = Number(posText);
    assert(Number.isInteger(position), "VCF POS must be an integer");
    assert(position >= 1 && position <= sequence.length, "VCF POS is outside the supplied sequence");
    assert(!seenLoci.has(position), `duplicate VCF position is not supported: ${position}`);
    assert(sequence[position - 1] === ref, `VCF REF mismatch at position ${position}: expected ${sequence[position - 1]}, received ${ref}`);
    variants.push({ chrom, position_1based: position, id, ref, alt, qual, filter, info });
    seenLoci.add(position);
    assert(variants.length <= MAX_VARIANT_COUNT, `VCF contains more than the ${MAX_VARIANT_COUNT}-variant safety limit`);
  });
  assert(formatSeen && headerSeen, "VCF must contain VCFv4.5 fileformat and #CHROM headers");
  return variants;
}
function cpgCount(sequence) {
  let count = 0;
  for (let index = 0; index <= sequence.length - 2; index += 1) if (sequence.slice(index, index + 2) === "CG") count += 1;
  return count;
}
function validateFrameOrigin(frameOrigin1based, sequenceLength) {
  if (frameOrigin1based === null || frameOrigin1based === undefined) return;
  assert(Number.isInteger(frameOrigin1based), "frame origin must be an integer");
  assert(frameOrigin1based >= 1 && frameOrigin1based <= sequenceLength, "frame origin must fall within the supplied sequence");
}
function frameEffect(sequence, position0, alt, frameOrigin1based) {
  const empty = {
    reference_codon: null,
    alternate_codon: null,
    reference_amino_acid: null,
    alternate_amino_acid: null,
    frame_relative_effect: "not-evaluated",
  };
  if (frameOrigin1based === null || frameOrigin1based === undefined) return empty;
  const origin0 = frameOrigin1based - 1;
  if (position0 < origin0) return empty;
  const codonStart = position0 - ((position0 - origin0) % 3);
  const codon = sequence.slice(codonStart, codonStart + 3);
  if (codon.length !== 3 || [...codon].some(base => !CANONICAL_BASES.includes(base))) {
    return { ...empty, frame_relative_effect: "unresolved-ambiguous-or-incomplete-codon" };
  }
  const alternate = [...codon];
  alternate[position0 - codonStart] = alt;
  const alternateCodon = alternate.join("");
  const refAa = STANDARD_CODE[codon];
  const altAa = STANDARD_CODE[alternateCodon];
  let effect;
  if (codonStart === origin0 && refAa === "M" && altAa !== "M") effect = "start-lost";
  else if (refAa === altAa) effect = "synonymous";
  else if (refAa !== "*" && altAa === "*") effect = "stop-gained";
  else if (refAa === "*" && altAa !== "*") effect = "stop-lost";
  else effect = "missense";
  return {
    reference_codon: codon,
    alternate_codon: alternateCodon,
    reference_amino_acid: refAa,
    alternate_amino_acid: altAa,
    frame_relative_effect: effect,
  };
}
export async function analyzeVariants(sequence, variants, windows, frameOrigin1based = null) {
  const output = [];
  for (const variant of variants) {
    const position0 = variant.position_1based - 1;
    const containing = windows.filter(window => window.start_1based - 1 <= position0 && position0 < window.end_1based_inclusive);
    assert(containing.length === 1, "variant evidence requires exactly one containing analysis window");
    const window = containing[0];
    const start0 = window.start_1based - 1;
    const end0 = window.end_1based_inclusive;
    const referenceWindow = sequence.slice(start0, end0);
    const alternateWindow = [...referenceWindow];
    alternateWindow[position0 - start0] = variant.alt;
    const alternateWindowText = alternateWindow.join("");
    const alternateMetrics = await analyzeWindow(alternateWindowText, window.window_index, 0, alternateWindowText.length);
    const context = [position0 - 1, position0, position0 + 1].map(index => index >= 0 && index < sequence.length ? sequence[index] : "N").join("");
    output.push({
      ...variant,
      substitution_class: TRANSITIONS.has(variant.ref + variant.alt) ? "transition" : "transversion",
      context_3mer: context,
      etq_address: etqAddressForOffset(position0),
      window_index: window.window_index,
      window_membership_count: 1,
      period3_scaled_power_delta: alternateMetrics.period3_exact.total_scaled_power - window.period3_exact.total_scaled_power,
      scl_energy_delta: alternateMetrics.scl_exact.total_energy - window.scl_exact.total_energy,
      gc_count_delta: Number("GC".includes(variant.alt)) - Number("GC".includes(variant.ref)),
      cpg_count_delta: cpgCount(alternateWindowText) - cpgCount(referenceWindow),
      ...frameEffect(sequence, position0, variant.alt, frameOrigin1based),
    });
  }
  return output;
}
function vlq(value) {
  assert(Number.isInteger(value) && value >= 0, "VLQ value must be nonnegative");
  const output = [value & 0x7f];
  value >>>= 7;
  while (value > 0) {
    output.unshift((value & 0x7f) | 0x80);
    value >>>= 7;
  }
  return output;
}
function u16be(value) { return [(value >>> 8) & 255, value & 255]; }
function u32be(value) { return [(value >>> 24) & 255, (value >>> 16) & 255, (value >>> 8) & 255, value & 255]; }
export function createMidi(windows) {
  const schemaBytes = [...utf8(CONTRACT)];
  const events = [
    [0, 0, [0xff, 0x03, ...vlq(schemaBytes.length), ...schemaBytes]],
    [0, 0, [0xff, 0x51, 0x03, 0x07, 0xa1, 0x20]],
  ];
  for (const window of windows) {
    const receiver = window.spectral_receiver;
    const tick = window.window_index * MIDI_PPQ;
    const channel = receiver.midi_channel;
    const controls = [
      [20, window.etq_address.site_index], [21, window.etq_address.fibre_label],
      [22, Math.floor(window.etq_address.event_index / 128)], [23, window.etq_address.event_index % 128],
      [71, receiver.midi_scl_cc71], [74, receiver.midi_brightness_cc74],
    ];
    for (const [control, value] of controls) events.push([tick, 1, [0xb0 | channel, control, value]]);
    events.push([tick, 2, [0x90 | channel, receiver.midi_pitch, receiver.midi_velocity]]);
    events.push([tick + receiver.duration_ticks, 0, [0x80 | channel, receiver.midi_pitch, 0]]);
  }
  events.sort((a, b) => a[0] - b[0] || a[1] - b[1] || compareByteArrays(a[2], b[2]));
  const track = [];
  let previous = 0;
  for (const [tick, _priority, payload] of events) {
    track.push(...vlq(tick - previous), ...payload);
    previous = tick;
  }
  track.push(0, 0xff, 0x2f, 0);
  return new Uint8Array([
    ...utf8("MThd"), ...u32be(6), ...u16be(0), ...u16be(1), ...u16be(MIDI_PPQ),
    ...utf8("MTrk"), ...u32be(track.length), ...track,
  ]);
}
function compareByteArrays(left, right) {
  const length = Math.min(left.length, right.length);
  for (let index = 0; index < length; index += 1) if (left[index] !== right[index]) return left[index] - right[index];
  return left.length - right.length;
}
function csvEscape(value) {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}
function rowsToCsv(fields, rows) {
  const lines = [fields.join(",")];
  for (const row of rows) lines.push(fields.map(field => csvEscape(row[field])).join(","));
  return utf8(lines.join("\n") + "\n");
}
export function windowCsvBytes(windows) {
  return rowsToCsv(WINDOW_CSV_FIELDS, windows.map(window => ({
    window_index: window.window_index, start_1based: window.start_1based,
    end_1based_inclusive: window.end_1based_inclusive, length: window.length,
    callable_bases: window.counts.callable, ambiguous_bases: window.counts.ambiguous,
    a_count: window.counts.A, c_count: window.counts.C, g_count: window.counts.G, t_count: window.counts.T,
    gc_numerator: window.gc_fraction.numerator, gc_denominator: window.gc_fraction.denominator,
    cpg_count: window.cpg_count, period3_scaled_power: window.period3_exact.total_scaled_power,
    scl_energy: window.scl_exact.total_energy, dominant_base: window.dominant_base,
    etq_site: window.etq_address.site_index, etq_fibre: window.etq_address.fibre_label,
    etq_event: window.etq_address.event_index, midi_channel: window.spectral_receiver.midi_channel,
    midi_pitch: window.spectral_receiver.midi_pitch, midi_velocity: window.spectral_receiver.midi_velocity,
    midi_brightness: window.spectral_receiver.midi_brightness_cc74,
    midi_scl_controller: window.spectral_receiver.midi_scl_cc71,
  })));
}
export function variantCsvBytes(variants) {
  return rowsToCsv(VARIANT_CSV_FIELDS, variants.map(variant => ({
    chrom: variant.chrom, position_1based: variant.position_1based, id: variant.id,
    ref: variant.ref, alt: variant.alt, substitution_class: variant.substitution_class,
    context_3mer: variant.context_3mer, etq_site: variant.etq_address.site_index,
    etq_fibre: variant.etq_address.fibre_label, etq_event: variant.etq_address.event_index,
    window_index: variant.window_index, period3_scaled_power_delta: variant.period3_scaled_power_delta,
    scl_energy_delta: variant.scl_energy_delta, gc_count_delta: variant.gc_count_delta,
    cpg_count_delta: variant.cpg_count_delta, reference_codon: variant.reference_codon,
    alternate_codon: variant.alternate_codon, reference_amino_acid: variant.reference_amino_acid,
    alternate_amino_acid: variant.alternate_amino_acid, frame_relative_effect: variant.frame_relative_effect,
  })));
}
export async function buildReport(fastaText, vcfText = null, windowSize = 303, stride = windowSize, frameOrigin1based = null) {
  const { recordId, description, sequence } = parseFasta(fastaText);
  validateFrameOrigin(frameOrigin1based, sequence.length);
  const windows = await buildWindows(sequence, windowSize, stride);
  const parsedVariants = parseVcf(vcfText, recordId, sequence);
  assert(parsedVariants.length === 0 || stride === windowSize, "variant evidence requires non-overlapping windows (stride equals window_size)");
  const variants = await analyzeVariants(sequence, parsedVariants, windows, frameOrigin1based);
  const partner = strandComplement(sequence);
  const report = {
    schema: REPORT_SCHEMA,
    contract: CONTRACT,
    input: {
      record_id: recordId,
      description,
      sequence_length: sequence.length,
      iupac_alphabet: IUPAC_DNA,
      canonical_bases: CANONICAL_BASES,
      sequence_sha256: await sha256Hex(sequence),
      refget_accession: await refgetAccession(sequence),
      ["re" + "verse_complement_sha256"]: await sha256Hex(partner),
      canonical_strand_sha256: await sha256Hex(sequence < partner ? sequence : partner),
      window_size: windowSize,
      stride,
      tail_policy: "include-unpadded-partial-window",
      frame_origin_1based: frameOrigin1based,
      variant_profile: "vcf-4.5-text-biallelic-snv-subset",
    },
    method: {
      position_address: "event=offset0-mod-303;site=event-mod-101;fibre=event-mod-3",
      period3: "four-times-unnormalized-voss-dft-power-at-frequency-one-third",
      period3_re2_weights: [...PERIOD3_RE2_WEIGHTS],
      period3_im_sqrt3_weights: [...PERIOD3_IM_WEIGHTS],
      scl_stencil: [...SCL_STENCIL],
      frequency_surface: "exact-dinucleotide-and-trinucleotide-counts;no-pseudocounts",
      midi_role: "deterministic-derived-spectral-receiver-not-sequence-identity",
      genetic_code: "NCBI-translation-table-1-standard-code",
    },
    window_count: windows.length,
    variant_count: variants.length,
    windows,
    variants,
    claims: { ...CLAIMS },
  };
  return { report, windowsCsv: windowCsvBytes(windows), variantsCsv: variantCsvBytes(variants), midi: createMidi(windows) };
}
export async function manifestFor(reportBytes, windowsCsv, variantsCsv, midi) {
  return {
    schema: MANIFEST_SCHEMA,
    contract: CONTRACT,
    files: {
      "report.json": { sha256: await sha256Hex(reportBytes), bytes: reportBytes.length },
      "windows.csv": { sha256: await sha256Hex(windowsCsv), bytes: windowsCsv.length },
      "variants.csv": { sha256: await sha256Hex(variantsCsv), bytes: variantsCsv.length },
      "spectrum.mid": { sha256: await sha256Hex(midi), bytes: midi.length },
    },
    claims: { ...CLAIMS },
  };
}
