import {
  F32_CELL_CONTRACT,
  canonicalJson as canonicalCellJson,
  sha256Hex,
  validateWord,
  wordToCell,
  wordToTrits,
} from "../genomic-spectrum/f32-cell.js";

export const CONTRACT = "RSH-F32-SIERPINSKI-INVERSIVE-WITNESS-V1";
export const WITNESS_SCHEMA = "RSH-F32-SIERPINSKI-INVERSIVE-WITNESS-RECORD-V1";
export const BUNDLE_SCHEMA = "RSH-F32-SIERPINSKI-INVERSIVE-WITNESS-BUNDLE-V1";
export const AXIS_NAMES = Object.freeze(["median-through-left", "median-through-right", "median-through-apex"]);
export const REFLECTION_PERMUTATIONS = Object.freeze([[0, 2, 1], [2, 1, 0], [1, 0, 2]]);
export const MAX_WITNESS_COUNT = 4_096;
export const CLAIMS = Object.freeze({
  actual_multi_device_execution: false,
  clawson_quadrilateral_constructed: false,
  compression_claim: false,
  coordinates_are_identity: false,
  distributed_execution: false,
  geometry_receipt_authority: false,
  physical_storage_demonstrated: false,
});

function stableObject(value) {
  if (Array.isArray(value)) return value.map(stableObject);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, stableObject(value[key])]));
  }
  return value;
}

export function canonicalJson(value) {
  return JSON.stringify(stableObject(value));
}

function abs(value) {
  return value < 0n ? -value : value;
}

function gcd(left, right) {
  let a = abs(left);
  let b = abs(right);
  while (b !== 0n) [a, b] = [b, a % b];
  return a;
}

export function validateFibreLabel(value) {
  if (!Number.isSafeInteger(value) || value < 0 || value > 2) {
    throw new RangeError("fibre_label must be an integer in [0, 2]");
  }
  return value;
}

function normalizeVector(numerators, denominator) {
  if (
    !Array.isArray(numerators)
    || numerators.length !== 3
    || typeof denominator !== "bigint"
    || denominator <= 0n
    || numerators.some(value => typeof value !== "bigint")
  ) {
    throw new Error("barycentric evidence requires three integer numerators and a positive denominator");
  }
  if (numerators.reduce((sum, value) => sum + value, 0n) !== denominator) {
    throw new Error("barycentric numerators must sum to their denominator");
  }
  let common = denominator;
  for (const value of numerators) common = gcd(common, value);
  return {
    numerators: numerators.map(value => value / common),
    denominator: denominator / common,
  };
}

function normalizeRational(numerator, denominator) {
  if (typeof numerator !== "bigint" || typeof denominator !== "bigint" || denominator === 0n) {
    throw new Error("invalid rational");
  }
  if (denominator < 0n) {
    numerator = -numerator;
    denominator = -denominator;
  }
  const common = gcd(numerator, denominator);
  return { numerator: numerator / common, denominator: denominator / common };
}

function rationalJson(numerator, denominator) {
  const value = normalizeRational(numerator, denominator);
  return { numerator: String(value.numerator), denominator: String(value.denominator) };
}

function barycentricJson(numerators, denominator) {
  const value = normalizeVector(numerators, denominator);
  return {
    numerators: value.numerators.map(String),
    denominator: String(value.denominator),
  };
}

export function transformBarycentric(numerators, denominator, fibreLabel) {
  fibreLabel = validateFibreLabel(fibreLabel);
  const source = normalizeVector(numerators.map(BigInt), BigInt(denominator));
  const centred = source.numerators.map(value => 3n * value - source.denominator);
  const squaredSum = centred.reduce((sum, value) => sum + value * value, 0n);
  if (squaredSum === 0n) throw new Error("the inversion centre has no finite conjugate");
  const permutation = REFLECTION_PERMUTATIONS[fibreLabel];
  const reflected = permutation.map(index => centred[index]);
  return normalizeVector(
    reflected.map(value => squaredSum + 6n * source.denominator * value),
    3n * squaredSum,
  );
}

export function radiusSquared(numerators, denominator) {
  const source = normalizeVector(numerators.map(BigInt), BigInt(denominator));
  const centred = source.numerators.map(value => 3n * value - source.denominator);
  const squaredSum = centred.reduce((sum, value) => sum + value * value, 0n);
  return normalizeRational(squaredSum, 18n * source.denominator * source.denominator);
}

function multiplyRationals(left, right) {
  return normalizeRational(
    left.numerator * right.numerator,
    left.denominator * right.denominator,
  );
}

export async function wordToWitness(word, fibreLabel) {
  word = validateWord(word);
  fibreLabel = validateFibreLabel(fibreLabel);
  const cell = wordToCell(word);
  const sourceNumerators = cell.cell_centroid_barycentric_numerators.map(BigInt);
  const sourceDenominator = BigInt(cell.cell_centroid_barycentric_denominator);
  const conjugate = transformBarycentric(sourceNumerators, sourceDenominator, fibreLabel);
  const recovered = transformBarycentric(
    conjugate.numerators,
    conjugate.denominator,
    fibreLabel,
  );
  const source = normalizeVector(sourceNumerators, sourceDenominator);
  const sourceRadius = radiusSquared(sourceNumerators, sourceDenominator);
  const conjugateRadius = radiusSquared(conjugate.numerators, conjugate.denominator);
  const product = multiplyRationals(sourceRadius, conjugateRadius);
  const recoveredJson = canonicalJson(barycentricJson(recovered.numerators, recovered.denominator));
  const sourceJson = canonicalJson(barycentricJson(source.numerators, source.denominator));
  if (product.numerator !== 1n || product.denominator !== 9n || recoveredJson !== sourceJson) {
    throw new Error("inversive witness invariant failed");
  }
  return {
    schema: WITNESS_SCHEMA,
    contract: CONTRACT,
    cell_contract: F32_CELL_CONTRACT,
    word_u32: word,
    word_hex: word.toString(16).padStart(8, "0"),
    address_trits: wordToTrits(word),
    source_cell_canonical_sha256: await sha256Hex(canonicalCellJson(cell)),
    fibre_label: fibreLabel,
    reflection_axis: AXIS_NAMES[fibreLabel],
    reflection_permutation: [...REFLECTION_PERMUTATIONS[fibreLabel]],
    inversion_center: "equilateral-triangle-centroid",
    inversion_constant_squared: rationalJson(1n, 3n),
    source_centroid_barycentric: barycentricJson(sourceNumerators, sourceDenominator),
    conjugate_barycentric: barycentricJson(conjugate.numerators, conjugate.denominator),
    double_application_barycentric: barycentricJson(
      recovered.numerators,
      recovered.denominator,
    ),
    source_radius_squared: rationalJson(sourceRadius.numerator, sourceRadius.denominator),
    conjugate_radius_squared: rationalJson(
      conjugateRadius.numerator,
      conjugateRadius.denominator,
    ),
    squared_radius_product: rationalJson(product.numerator, product.denominator),
    product_invariant_verified: true,
    double_conjugation_verified: true,
    identity_policy: "word-and-trits-identify-cell;exact-rational-witness-is-independent-sidecar;rendered-coordinates-are-not-identity",
    claims: { ...CLAIMS },
  };
}

export async function validateWitness(witness) {
  if (witness === null || typeof witness !== "object" || Array.isArray(witness)) {
    throw new TypeError("witness must be an object");
  }
  if (witness.schema !== WITNESS_SCHEMA || witness.contract !== CONTRACT) {
    throw new Error("unexpected inversive witness schema or contract");
  }
  if (canonicalJson(witness.claims) !== canonicalJson(CLAIMS)) {
    throw new Error("inversive witness claim boundary mismatch");
  }
  const expected = await wordToWitness(witness.word_u32, witness.fibre_label);
  if (canonicalJson(witness) !== canonicalJson(expected)) {
    throw new Error("inversive witness evidence mismatch");
  }
  return witness.word_u32;
}

export async function buildBundle(words, fibreLabels) {
  if (!Array.isArray(words) || !Array.isArray(fibreLabels) || words.length !== fibreLabels.length) {
    throw new Error("fibre count must equal word count");
  }
  if (words.length > MAX_WITNESS_COUNT) {
    throw new RangeError(`word count exceeds the ${MAX_WITNESS_COUNT}-witness limit`);
  }
  const witnesses = [];
  for (let index = 0; index < words.length; index += 1) {
    witnesses.push(await wordToWitness(words[index], fibreLabels[index]));
  }
  for (const witness of witnesses) await validateWitness(witness);
  const bundle = {
    schema: BUNDLE_SCHEMA,
    contract: CONTRACT,
    cell_contract: F32_CELL_CONTRACT,
    witness_count: witnesses.length,
    inversion_constant_squared: rationalJson(1n, 3n),
    witnesses,
    round_trip_verified: true,
    product_invariant_verified: true,
    claims: { ...CLAIMS },
  };
  bundle.canonical_sha256 = await sha256Hex(canonicalJson(bundle));
  return bundle;
}

export async function verifyBundle(bundle) {
  if (
    bundle.schema !== BUNDLE_SCHEMA
    || bundle.contract !== CONTRACT
    || bundle.cell_contract !== F32_CELL_CONTRACT
  ) {
    throw new Error("unexpected inversive witness bundle");
  }
  if (canonicalJson(bundle.claims) !== canonicalJson(CLAIMS)) {
    throw new Error("inversive witness bundle claim boundary mismatch");
  }
  if (
    !Array.isArray(bundle.witnesses)
    || !Number.isSafeInteger(bundle.witness_count)
    || bundle.witness_count !== bundle.witnesses.length
    || bundle.witness_count > MAX_WITNESS_COUNT
  ) {
    throw new Error("inversive witness bundle count mismatch");
  }
  const words = [];
  for (const witness of bundle.witnesses) words.push(await validateWitness(witness));
  const unsigned = { ...bundle };
  delete unsigned.canonical_sha256;
  if (bundle.canonical_sha256 !== await sha256Hex(canonicalJson(unsigned))) {
    throw new Error("inversive witness bundle canonical hash mismatch");
  }
  if (bundle.round_trip_verified !== true || bundle.product_invariant_verified !== true) {
    throw new Error("inversive witness bundle invariant declaration mismatch");
  }
  return words;
}
