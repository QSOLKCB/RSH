// SPDX-License-Identifier: MPL-2.0

export const F32_CELL_CONTRACT = "RSH-F32-SIERPINSKI-CELL-V1";
export const F32_CELL_SCHEMA = "RSH-F32-SIERPINSKI-CELL-RECORD-V1";
export const F32_BUNDLE_SCHEMA = "RSH-F32-SIERPINSKI-CELL-BUNDLE-V1";
export const F32_CELL_DEPTH = 21;
export const F32_WORD_LIMIT = 2n ** 32n;
export const F32_TRIT_CAPACITY = 3n ** BigInt(F32_CELL_DEPTH);
export const MAX_F32_BUNDLE_CELLS = 16_384;
export const MAX_F32_FIELD_CHARACTERS = 128;
export const F32_CELL_CLAIMS = Object.freeze({
  actual_multi_device_execution: false,
  compression_claim: false,
  coordinates_are_identity: false,
  distributed_execution: false,
  geometry_receipt_authority: false,
  physical_storage_demonstrated: false,
});

if (!(3n ** 20n < F32_WORD_LIMIT && F32_WORD_LIMIT < F32_TRIT_CAPACITY)) {
  throw new Error("depth-21 ternary capacity invariant failed");
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

export async function sha256Hex(input) {
  const bytes = typeof input === "string" ? new TextEncoder().encode(input) : input;
  if (!globalThis.crypto?.subtle) throw new Error("Web Crypto SHA-256 is unavailable");
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function validateWord(word) {
  if (!Number.isSafeInteger(word) || word < 0 || word > 0xffffffff) {
    throw new RangeError("binary32 word must be an integer in [0, 2^32)");
  }
  return word >>> 0;
}

export function validateField(field) {
  if (field === null) return null;
  if (typeof field !== "string" || field.length === 0) throw new TypeError("field must be nonempty text");
  if (field.length > MAX_F32_FIELD_CHARACTERS) {
    throw new RangeError(`field exceeds the ${MAX_F32_FIELD_CHARACTERS}-character safety limit`);
  }
  if (!/^[\x20-\x7e]+$/u.test(field)) {
    throw new Error("field must contain printable ASCII only for cross-runtime canonicalization");
  }
  return field;
}

export function wordToTrits(word) {
  let value = BigInt(validateWord(word));
  const digits = Array(F32_CELL_DEPTH).fill("0");
  for (let index = F32_CELL_DEPTH - 1; index >= 0; index -= 1) {
    digits[index] = String(value % 3n);
    value /= 3n;
  }
  if (value !== 0n) throw new Error("binary32 word escaped depth-21 ternary capacity");
  return digits.join("");
}

export function tritsToWord(trits) {
  if (typeof trits !== "string" || trits.length !== F32_CELL_DEPTH || /[^012]/u.test(trits)) {
    throw new Error(`Sierpinski address must contain exactly ${F32_CELL_DEPTH} trits`);
  }
  let value = 0n;
  for (const character of trits) value = value * 3n + BigInt(character);
  if (value >= F32_WORD_LIMIT) throw new Error("Sierpinski address is outside the binary32 word domain");
  return Number(value) >>> 0;
}

export function exactCellVertices(trits) {
  tritsToWord(trits);
  const vertices = [[1, 0, 0], [0, 1, 0], [0, 0, 1]];
  let denominator = 1;
  for (const character of trits) {
    const selected = Number(character);
    for (const vertex of vertices) vertex[selected] += denominator;
    denominator *= 2;
  }
  return { numerators: vertices, denominator };
}

export function exactCellCentroid(trits) {
  const vertices = exactCellVertices(trits);
  return {
    numerators: [0, 1, 2].map((axis) => vertices.numerators.reduce((sum, vertex) => sum + vertex[axis], 0)),
    denominator: 3 * vertices.denominator,
  };
}

export function classifyWord(word) {
  const value = validateWord(word);
  const exponent = (value >>> 23) & 0xff;
  const fraction = value & 0x7fffff;
  if (exponent === 0) return fraction === 0 ? "zero" : "subnormal";
  if (exponent === 0xff) {
    if (fraction === 0) return "infinity";
    return (fraction & (1 << 22)) !== 0 ? "quiet-nan" : "signaling-nan";
  }
  return "normal";
}

export function wordToF32(word) {
  const buffer = new ArrayBuffer(4);
  const view = new DataView(buffer);
  view.setUint32(0, validateWord(word), false);
  return view.getFloat32(0, false);
}

export function f32ToWord(value) {
  if (typeof value !== "number") throw new TypeError("f32 input must be numeric");
  const buffer = new ArrayBuffer(4);
  const view = new DataView(buffer);
  view.setFloat32(0, value, false);
  return view.getUint32(0, false);
}

export function wordToCell(word, { cellIndex = null, field = null } = {}) {
  const value = validateWord(word);
  if (cellIndex !== null && (!Number.isSafeInteger(cellIndex) || cellIndex < 0)) {
    throw new RangeError("cellIndex must be a nonnegative integer");
  }
  field = validateField(field);
  const trits = wordToTrits(value);
  const vertices = exactCellVertices(trits);
  const centroid = exactCellCentroid(trits);
  const record = {
    schema: F32_CELL_SCHEMA,
    contract: F32_CELL_CONTRACT,
    depth: F32_CELL_DEPTH,
    address_radix: 3,
    address_trits: trits,
    word_u32: value,
    word_hex: value.toString(16).padStart(8, "0"),
    sign_bit: value >>> 31,
    exponent_bits: (value >>> 23) & 0xff,
    fraction_bits: value & 0x7fffff,
    classification: classifyWord(value),
    cell_vertex_barycentric_numerators: vertices.numerators,
    cell_vertex_barycentric_denominator: vertices.denominator,
    cell_centroid_barycentric_numerators: centroid.numerators,
    cell_centroid_barycentric_denominator: centroid.denominator,
    identity_policy: "word_u32-and-address_trits-exact;coordinates-derived-not-identity",
    claims: { ...F32_CELL_CLAIMS },
  };
  if (cellIndex !== null) record.cell_index = cellIndex;
  if (field !== null) record.field = field;
  return record;
}

export function validateCell(cell) {
  if (cell === null || typeof cell !== "object" || Array.isArray(cell)) throw new TypeError("cell must be an object");
  if (cell.schema !== F32_CELL_SCHEMA || cell.contract !== F32_CELL_CONTRACT) {
    throw new Error("unexpected Sierpinski cell schema or contract");
  }
  if (canonicalJson(cell.claims) !== canonicalJson(F32_CELL_CLAIMS)) {
    throw new Error("Sierpinski cell claim boundary mismatch");
  }
  const word = tritsToWord(cell.address_trits);
  if (cell.word_u32 !== word || cell.word_hex !== word.toString(16).padStart(8, "0")) {
    throw new Error("Sierpinski address and binary32 word disagree");
  }
  if (cell.depth !== F32_CELL_DEPTH || cell.address_radix !== 3) throw new Error("Sierpinski cell depth or radix mismatch");
  if (cell.sign_bit !== word >>> 31) throw new Error("binary32 sign bit mismatch");
  if (cell.exponent_bits !== ((word >>> 23) & 0xff)) throw new Error("binary32 exponent bits mismatch");
  if (cell.fraction_bits !== (word & 0x7fffff)) throw new Error("binary32 fraction bits mismatch");
  if (cell.classification !== classifyWord(word)) throw new Error("binary32 classification mismatch");
  if (Object.hasOwn(cell, "field")) validateField(cell.field);
  const vertices = exactCellVertices(cell.address_trits);
  const centroid = exactCellCentroid(cell.address_trits);
  if (canonicalJson(cell.cell_vertex_barycentric_numerators) !== canonicalJson(vertices.numerators)
      || cell.cell_vertex_barycentric_denominator !== vertices.denominator) {
    throw new Error("Sierpinski cell vertex evidence mismatch");
  }
  if (canonicalJson(cell.cell_centroid_barycentric_numerators) !== canonicalJson(centroid.numerators)
      || cell.cell_centroid_barycentric_denominator !== centroid.denominator) {
    throw new Error("Sierpinski cell centroid evidence mismatch");
  }
  return word;
}

export async function buildCellBundle(words, fields = null) {
  if (!Array.isArray(words)) throw new TypeError("words must be an array");
  if (words.length > MAX_F32_BUNDLE_CELLS) {
    throw new RangeError(`word count exceeds the ${MAX_F32_BUNDLE_CELLS}-cell bundle limit`);
  }
  if (fields !== null && (!Array.isArray(fields) || fields.length !== words.length)) {
    throw new Error("field count must equal word count");
  }
  const cells = words.map((word, index) => wordToCell(word, {
    cellIndex: index,
    field: fields === null ? null : fields[index],
  }));
  for (const cell of cells) validateCell(cell);
  const bundle = {
    schema: F32_BUNDLE_SCHEMA,
    contract: F32_CELL_CONTRACT,
    depth: F32_CELL_DEPTH,
    cell_count: cells.length,
    capacity_words: 2 ** 32,
    ternary_address_capacity: Number(F32_TRIT_CAPACITY),
    cells,
    round_trip_verified: true,
    claims: { ...F32_CELL_CLAIMS },
  };
  bundle.canonical_sha256 = await sha256Hex(canonicalJson(bundle));
  return bundle;
}

export async function verifyCellBundle(bundle) {
  if (bundle.schema !== F32_BUNDLE_SCHEMA || bundle.contract !== F32_CELL_CONTRACT) {
    throw new Error("unexpected Sierpinski bundle schema or contract");
  }
  if (canonicalJson(bundle.claims) !== canonicalJson(F32_CELL_CLAIMS)) {
    throw new Error("Sierpinski bundle claim boundary mismatch");
  }
  if (!Array.isArray(bundle.cells)
      || !Number.isSafeInteger(bundle.cell_count)
      || bundle.cell_count !== bundle.cells.length
      || bundle.cell_count > MAX_F32_BUNDLE_CELLS) {
    throw new Error("Sierpinski bundle cell count mismatch");
  }
  const words = bundle.cells.map(validateCell);
  const unsigned = { ...bundle };
  delete unsigned.canonical_sha256;
  if (bundle.canonical_sha256 !== await sha256Hex(canonicalJson(unsigned))) {
    throw new Error("Sierpinski bundle canonical hash mismatch");
  }
  if (bundle.round_trip_verified !== true) throw new Error("Sierpinski bundle must declare verified round trip");
  return words;
}
