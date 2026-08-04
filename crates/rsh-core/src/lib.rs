//! Native reference-compatible geometry and evidence for the Robitaille–Slade Helix.
//!
//! The Python implementation remains the readable scientific oracle. This crate
//! reproduces its declared construction, validation rules, report schema, and
//! cross-runtime conformance coordinates.

use serde::Serialize;
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;

pub const MODEL_NAME: &str = "Robitaille-Slade-Helix";
pub const MODEL_VERSION: &str = "2.0.0";
pub const IMPLEMENTATION: &str = "rust";
pub const CANONICAL_FLOAT_PRECISION: usize = 12;
pub const RECEIPT_DOMAIN: &[u8] = b"RSH-GEOMETRY-EVIDENCE-V2\0";
pub const TAU_MIN_EXCLUSIVE: f64 = 0.0;
pub const TAU_MAX_EXCLUSIVE: f64 = 1.0;
pub const GOLDEN_RECEIPT_129: &str =
    "f33042335100b7a2bca8c5c97724782ecb820cd8f6704f8e7eb074c1ed9e9a00";
pub const GOLDEN_ENTRY_129: [f64; 3] = [
    -1.8484919565721223,
    -0.6353766408175766,
    -0.16593646474199972,
];
pub const GOLDEN_EXIT_129: [f64; 3] = [
    1.2097010814305758,
    1.2168907843927106,
    0.9663511535281694,
];
pub const GOLDEN_COORDINATE_TOLERANCE: f64 = 1.0e-12;

#[inline]
pub fn psi() -> f64 {
    (2.0 + 5.0_f64.sqrt()).sqrt()
}

#[inline]
pub fn kappa_max() -> f64 {
    2.0_f64.sqrt() - 1.0
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Serialize)]
pub struct Vec3 {
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

impl Vec3 {
    pub const fn new(x: f64, y: f64, z: f64) -> Self {
        Self { x, y, z }
    }

    pub fn dot(self, other: Self) -> f64 {
        self.x * other.x + self.y * other.y + self.z * other.z
    }

    pub fn cross(self, other: Self) -> Self {
        Self::new(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )
    }

    pub fn norm(self) -> f64 {
        self.x.hypot(self.y).hypot(self.z)
    }

    pub fn add(self, other: Self) -> Self {
        Self::new(self.x + other.x, self.y + other.y, self.z + other.z)
    }

    pub fn sub(self, other: Self) -> Self {
        Self::new(self.x - other.x, self.y - other.y, self.z - other.z)
    }

    pub fn scale(self, amount: f64) -> Self {
        Self::new(self.x * amount, self.y * amount, self.z * amount)
    }

    pub fn is_finite(self) -> bool {
        self.x.is_finite() && self.y.is_finite() && self.z.is_finite()
    }

    pub fn normalize(self) -> Result<Self, String> {
        let magnitude = self.norm();
        if !magnitude.is_finite() {
            return Err("cannot normalize a non-finite vector".into());
        }
        if magnitude <= 1.0e-15 {
            return Err("cannot normalize a near-zero vector".into());
        }
        Ok(self.scale(1.0 / magnitude))
    }

    pub fn as_array(self) -> [f64; 3] {
        [self.x, self.y, self.z]
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct ModelConfig {
    pub samples: usize,
    pub s0: f64,
    pub s1: f64,
    pub kappa_fraction: f64,
    pub tau_floor: f64,
    pub tau_amplitude: f64,
}

impl Default for ModelConfig {
    fn default() -> Self {
        Self {
            samples: 513,
            s0: 0.0,
            s1: 4.0,
            kappa_fraction: 0.85,
            tau_floor: 0.22,
            tau_amplitude: 0.13,
        }
    }
}

impl ModelConfig {
    pub fn validate(self) -> Result<Self, String> {
        if self.samples < 3 {
            return Err("samples must be at least 3".into());
        }
        if self.samples % 2 == 0 {
            return Err("samples must be odd so p=0.5 is represented exactly".into());
        }
        if !self.s0.is_finite() || !self.s1.is_finite() || self.s1 <= self.s0 {
            return Err("s1 must be finite and greater than s0".into());
        }
        if !self.kappa_fraction.is_finite()
            || !(0.0 < self.kappa_fraction && self.kappa_fraction <= 1.0)
        {
            return Err("kappa_fraction must be finite and in (0, 1]".into());
        }
        if !self.tau_floor.is_finite() || !self.tau_amplitude.is_finite() {
            return Err("torsion schedule parameters must be finite".into());
        }
        if self.tau_amplitude < 0.0 {
            return Err("tau_amplitude must be non-negative".into());
        }
        let tau_min = self.tau_floor;
        let tau_max = self.tau_floor + 2.0 * self.tau_amplitude;
        if !(TAU_MIN_EXCLUSIVE < tau_min
            && tau_min < TAU_MAX_EXCLUSIVE
            && TAU_MIN_EXCLUSIVE < tau_max
            && tau_max < TAU_MAX_EXCLUSIVE)
        {
            return Err("the torsion schedule must remain strictly inside (0, 1)".into());
        }
        Ok(self)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct Sample {
    pub s: f64,
    pub p: f64,
    pub x: f64,
    pub y: f64,
    pub z: f64,
    pub kappa: f64,
    pub tau: f64,
    pub tx: f64,
    pub ty: f64,
    pub tz: f64,
    pub nx: f64,
    pub ny: f64,
    pub nz: f64,
    pub bx: f64,
    pub by: f64,
    pub bz: f64,
}

impl Sample {
    pub fn position(self) -> Vec3 {
        Vec3::new(self.x, self.y, self.z)
    }

    pub fn tangent(self) -> Vec3 {
        Vec3::new(self.tx, self.ty, self.tz)
    }

    pub fn normal(self) -> Vec3 {
        Vec3::new(self.nx, self.ny, self.nz)
    }

    pub fn binormal(self) -> Vec3 {
        Vec3::new(self.bx, self.by, self.bz)
    }

    pub fn radius(self) -> f64 {
        self.position().norm()
    }
}

pub fn kappa_schedule(s: f64, config: ModelConfig) -> f64 {
    let base = config.kappa_fraction * kappa_max();
    base * (0.92 + 0.08 * (0.35 * s * psi()).cos())
}

pub fn tau_schedule(s: f64, config: ModelConfig) -> f64 {
    config.tau_floor + config.tau_amplitude * (1.0 + (0.25 * s * psi()).sin())
}

fn orthonormalize(tangent: Vec3, normal: Vec3, _binormal: Vec3) -> Result<(Vec3, Vec3, Vec3), String> {
    let tangent = tangent.normalize()?;
    let normal = normal.sub(tangent.scale(normal.dot(tangent))).normalize()?;
    let binormal = tangent.cross(normal).normalize()?;
    Ok((tangent, normal, binormal))
}

fn frame_derivative(
    tangent: Vec3,
    normal: Vec3,
    binormal: Vec3,
    kappa: f64,
    tau: f64,
) -> (Vec3, Vec3, Vec3) {
    let tangent_prime = normal.scale(kappa);
    let normal_prime = tangent.scale(-kappa).add(binormal.scale(tau));
    let binormal_prime = normal.scale(-tau);
    (tangent_prime, normal_prime, binormal_prime)
}

fn checked_values(s: f64, config: ModelConfig) -> Result<(f64, f64), String> {
    let kappa = kappa_schedule(s, config);
    let tau = tau_schedule(s, config);
    if !kappa.is_finite() || !(0.0 <= kappa && kappa <= kappa_max() + 1.0e-12) {
        return Err(format!("curvature schedule violates its bound at s={s:?}"));
    }
    if !tau.is_finite() || !(TAU_MIN_EXCLUSIVE < tau && tau < TAU_MAX_EXCLUSIVE) {
        return Err(format!("torsion schedule leaves (0, 1) at s={s:?}"));
    }
    Ok((kappa, tau))
}

pub fn integrate_path(config: ModelConfig) -> Result<Vec<Sample>, String> {
    let config = config.validate()?;
    let ds = (config.s1 - config.s0) / (config.samples - 1) as f64;
    let mut tangent = Vec3::new(1.0, 0.0, 0.0);
    let mut normal = Vec3::new(0.0, 1.0, 0.0);
    let mut binormal = Vec3::new(0.0, 0.0, 1.0);
    let mut position = Vec3::default();
    let mut rows = Vec::with_capacity(config.samples);

    for index in 0..config.samples {
        let s = config.s0 + index as f64 * ds;
        let p = index as f64 / (config.samples - 1) as f64;
        let (kappa, tau) = checked_values(s, config)?;
        rows.push(Sample {
            s,
            p,
            x: position.x,
            y: position.y,
            z: position.z,
            kappa,
            tau,
            tx: tangent.x,
            ty: tangent.y,
            tz: tangent.z,
            nx: normal.x,
            ny: normal.y,
            nz: normal.z,
            bx: binormal.x,
            by: binormal.y,
            bz: binormal.z,
        });

        if index == config.samples - 1 {
            break;
        }

        let (tangent_prime, normal_prime, binormal_prime) =
            frame_derivative(tangent, normal, binormal, kappa, tau);
        let tangent_mid = tangent.add(tangent_prime.scale(0.5 * ds));
        let normal_mid = normal.add(normal_prime.scale(0.5 * ds));
        let binormal_mid = binormal.add(binormal_prime.scale(0.5 * ds));
        let (tangent_mid, normal_mid, binormal_mid) =
            orthonormalize(tangent_mid, normal_mid, binormal_mid)?;

        let (kappa_mid, tau_mid) = checked_values(s + 0.5 * ds, config)?;
        let (tangent_prime, normal_prime, binormal_prime) =
            frame_derivative(tangent_mid, normal_mid, binormal_mid, kappa_mid, tau_mid);

        position = position.add(tangent_mid.scale(ds));
        tangent = tangent.add(tangent_prime.scale(ds));
        normal = normal.add(normal_prime.scale(ds));
        binormal = binormal.add(binormal_prime.scale(ds));
        (tangent, normal, binormal) = orthonormalize(tangent, normal, binormal)?;
    }

    Ok(rows)
}

pub fn centre_path(rows: &mut [Sample]) -> Result<(), String> {
    if rows.len() < 3 || rows.len() % 2 == 0 {
        return Err("centre_path requires an odd number of at least 3 samples".into());
    }
    let centre = rows[rows.len() / 2].position();
    for row in rows {
        row.x -= centre.x;
        row.y -= centre.y;
        row.z -= centre.z;
    }
    Ok(())
}

pub fn build_path(config: ModelConfig) -> Result<Vec<Sample>, String> {
    let mut rows = integrate_path(config)?;
    centre_path(&mut rows)?;
    Ok(rows)
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct VerifyReport {
    pub model: String,
    pub version: String,
    pub samples: usize,
    pub s0: f64,
    pub s1: f64,
    pub kappa_fraction: f64,
    pub tau_floor: f64,
    pub tau_amplitude: f64,
    pub psi: f64,
    pub kappa_bound: f64,
    pub centering_mode: String,
    pub centre_parameter: f64,
    pub centre_error: f64,
    pub min_kappa: f64,
    pub max_kappa: f64,
    pub min_tau: f64,
    pub max_tau: f64,
    pub kappa_violations: usize,
    pub tau_violations: usize,
    pub max_sampling_gap_error: f64,
    pub max_frame_norm_error: f64,
    pub max_frame_orthogonality_error: f64,
    pub min_radius: f64,
    pub max_radius: f64,
    pub path_length: f64,
    pub entry: [f64; 3],
    pub centre: [f64; 3],
    pub exit: [f64; 3],
    pub endpoint_separation: f64,
    pub pass_centre: bool,
    pub pass_kappa: bool,
    pub pass_tau: bool,
    pub pass_sampling: bool,
    pub pass_frame: bool,
    pub pass_all: bool,
    pub receipt: String,
}

fn min_max(values: impl Iterator<Item = f64>) -> Result<(f64, f64), String> {
    let mut iterator = values;
    let first = iterator.next().ok_or_else(|| "cannot summarize an empty sequence".to_string())?;
    let mut minimum = first;
    let mut maximum = first;
    for value in iterator {
        minimum = minimum.min(value);
        maximum = maximum.max(value);
    }
    Ok((minimum, maximum))
}

pub fn verify(rows: &[Sample], config: ModelConfig) -> Result<VerifyReport, String> {
    let config = config.validate()?;
    if rows.len() != config.samples {
        return Err("row count does not match the validated model configuration".into());
    }

    let centre = rows[rows.len() / 2];
    let ideal_gap = 1.0 / (rows.len() - 1) as f64;
    let mut gap_error: f64 = 0.0;
    let mut path_length = 0.0;
    for pair in rows.windows(2) {
        let gap = pair[1].p - pair[0].p;
        gap_error = gap_error.max(((gap - ideal_gap).abs()) / ideal_gap);
        path_length += pair[1].position().sub(pair[0].position()).norm();
    }

    let mut frame_norm_error: f64 = 0.0;
    let mut frame_orthogonality_error: f64 = 0.0;
    for (index, row) in rows.iter().copied().enumerate() {
        let frame = [row.tangent(), row.normal(), row.binormal()];
        if !frame.iter().all(|vector| vector.is_finite()) {
            return Err(format!("sample {index} contains a non-finite frame component"));
        }
        for vector in frame {
            frame_norm_error = frame_norm_error.max((vector.norm() - 1.0).abs());
        }
        frame_orthogonality_error = frame_orthogonality_error
            .max(frame[0].dot(frame[1]).abs())
            .max(frame[0].dot(frame[2]).abs())
            .max(frame[1].dot(frame[2]).abs());
    }

    let (min_kappa, max_kappa) = min_max(rows.iter().map(|row| row.kappa))?;
    let (min_tau, max_tau) = min_max(rows.iter().map(|row| row.tau))?;
    let (min_radius, max_radius) = min_max(rows.iter().map(|row| row.radius()))?;
    let centre_error = centre.position().norm();
    let kappa_violations = rows
        .iter()
        .filter(|row| !(0.0 <= row.kappa && row.kappa <= kappa_max() + 1.0e-12))
        .count();
    let tau_violations = rows
        .iter()
        .filter(|row| !(TAU_MIN_EXCLUSIVE < row.tau && row.tau < TAU_MAX_EXCLUSIVE))
        .count();
    let pass_centre = centre_error <= 1.0e-12 && centre.p == 0.5;
    let pass_kappa = kappa_violations == 0;
    let pass_tau = tau_violations == 0;
    let pass_sampling = gap_error <= 1.0e-12;
    let pass_frame = frame_norm_error <= 1.0e-12 && frame_orthogonality_error <= 1.0e-12;
    let pass_all = pass_centre && pass_kappa && pass_tau && pass_sampling && pass_frame;

    let mut report = VerifyReport {
        model: MODEL_NAME.into(),
        version: MODEL_VERSION.into(),
        samples: rows.len(),
        s0: config.s0,
        s1: config.s1,
        kappa_fraction: config.kappa_fraction,
        tau_floor: config.tau_floor,
        tau_amplitude: config.tau_amplitude,
        psi: psi(),
        kappa_bound: kappa_max(),
        centering_mode: "midpoint-coordinate-normalisation".into(),
        centre_parameter: centre.p,
        centre_error,
        min_kappa,
        max_kappa,
        min_tau,
        max_tau,
        kappa_violations,
        tau_violations,
        max_sampling_gap_error: gap_error,
        max_frame_norm_error: frame_norm_error,
        max_frame_orthogonality_error: frame_orthogonality_error,
        min_radius,
        max_radius,
        path_length,
        entry: rows[0].position().as_array(),
        centre: centre.position().as_array(),
        exit: rows[rows.len() - 1].position().as_array(),
        endpoint_separation: rows[rows.len() - 1]
            .position()
            .sub(rows[0].position())
            .norm(),
        pass_centre,
        pass_kappa,
        pass_tau,
        pass_sampling,
        pass_frame,
        pass_all,
        receipt: String::new(),
    };
    report.receipt = make_receipt(&report)?;
    Ok(report)
}

pub fn build_and_verify(config: ModelConfig) -> Result<(Vec<Sample>, VerifyReport), String> {
    let config = config.validate()?;
    let rows = build_path(config)?;
    let report = verify(&rows, config)?;
    Ok((rows, report))
}

fn python_scientific(value: f64) -> Result<String, String> {
    if !value.is_finite() {
        return Err("non-finite values cannot be receipted".into());
    }
    let raw = format!("{:.*e}", CANONICAL_FLOAT_PRECISION, value);
    let (mantissa, exponent) = raw
        .split_once('e')
        .ok_or_else(|| "failed to encode canonical float".to_string())?;
    let exponent: i32 = exponent
        .parse()
        .map_err(|_| "failed to parse canonical exponent".to_string())?;
    Ok(format!("{mantissa}e{exponent:+03}"))
}

fn canonical_float(value: f64) -> Result<Value, String> {
    Ok(Value::String(python_scientific(value)?))
}

fn canonical_vec3(value: [f64; 3]) -> Result<Value, String> {
    Ok(Value::Array(
        value
            .into_iter()
            .map(canonical_float)
            .collect::<Result<Vec<_>, _>>()?,
    ))
}

pub fn canonical_report_bytes(report: &VerifyReport) -> Result<Vec<u8>, String> {
    let mut payload: BTreeMap<String, Value> = BTreeMap::new();
    payload.insert("centering_mode".into(), Value::String(report.centering_mode.clone()));
    payload.insert("centre".into(), canonical_vec3(report.centre)?);
    payload.insert("centre_error".into(), canonical_float(report.centre_error)?);
    payload.insert("centre_parameter".into(), canonical_float(report.centre_parameter)?);
    payload.insert("endpoint_separation".into(), canonical_float(report.endpoint_separation)?);
    payload.insert("entry".into(), canonical_vec3(report.entry)?);
    payload.insert("exit".into(), canonical_vec3(report.exit)?);
    payload.insert("kappa_bound".into(), canonical_float(report.kappa_bound)?);
    payload.insert("kappa_fraction".into(), canonical_float(report.kappa_fraction)?);
    payload.insert("kappa_violations".into(), Value::from(report.kappa_violations));
    payload.insert("max_frame_norm_error".into(), canonical_float(report.max_frame_norm_error)?);
    payload.insert(
        "max_frame_orthogonality_error".into(),
        canonical_float(report.max_frame_orthogonality_error)?,
    );
    payload.insert("max_kappa".into(), canonical_float(report.max_kappa)?);
    payload.insert("max_radius".into(), canonical_float(report.max_radius)?);
    payload.insert("max_sampling_gap_error".into(), canonical_float(report.max_sampling_gap_error)?);
    payload.insert("max_tau".into(), canonical_float(report.max_tau)?);
    payload.insert("min_kappa".into(), canonical_float(report.min_kappa)?);
    payload.insert("min_radius".into(), canonical_float(report.min_radius)?);
    payload.insert("min_tau".into(), canonical_float(report.min_tau)?);
    payload.insert("model".into(), Value::String(report.model.clone()));
    payload.insert("pass_all".into(), Value::Bool(report.pass_all));
    payload.insert("pass_centre".into(), Value::Bool(report.pass_centre));
    payload.insert("pass_frame".into(), Value::Bool(report.pass_frame));
    payload.insert("pass_kappa".into(), Value::Bool(report.pass_kappa));
    payload.insert("pass_sampling".into(), Value::Bool(report.pass_sampling));
    payload.insert("pass_tau".into(), Value::Bool(report.pass_tau));
    payload.insert("path_length".into(), canonical_float(report.path_length)?);
    payload.insert("psi".into(), canonical_float(report.psi)?);
    payload.insert("s0".into(), canonical_float(report.s0)?);
    payload.insert("s1".into(), canonical_float(report.s1)?);
    payload.insert("samples".into(), Value::from(report.samples));
    payload.insert("tau_amplitude".into(), canonical_float(report.tau_amplitude)?);
    payload.insert("tau_floor".into(), canonical_float(report.tau_floor)?);
    payload.insert("tau_violations".into(), Value::from(report.tau_violations));
    payload.insert("version".into(), Value::String(report.version.clone()));
    serde_json::to_vec(&payload).map_err(|error| error.to_string())
}

pub fn make_receipt(report: &VerifyReport) -> Result<String, String> {
    let mut hasher = Sha256::new();
    hasher.update(RECEIPT_DOMAIN);
    hasher.update(canonical_report_bytes(report)?);
    Ok(format!("{:x}", hasher.finalize()))
}

#[derive(Clone, Debug, Serialize)]
pub struct ConformanceResult {
    pub pass: bool,
    pub coordinate_tolerance: f64,
    pub entry_max_abs_error: f64,
    pub exit_max_abs_error: f64,
    pub python_golden_receipt: String,
    pub rust_receipt: String,
    pub receipt_identical: bool,
}

fn max_abs_error(actual: [f64; 3], expected: [f64; 3]) -> f64 {
    actual
        .into_iter()
        .zip(expected)
        .map(|(actual, expected)| (actual - expected).abs())
        .fold(0.0_f64, f64::max)
}

pub fn check_python_conformance() -> Result<ConformanceResult, String> {
    let config = ModelConfig {
        samples: 129,
        ..ModelConfig::default()
    };
    let (_, report) = build_and_verify(config)?;
    let entry_max_abs_error = max_abs_error(report.entry, GOLDEN_ENTRY_129);
    let exit_max_abs_error = max_abs_error(report.exit, GOLDEN_EXIT_129);
    let receipt_identical = report.receipt == GOLDEN_RECEIPT_129;
    Ok(ConformanceResult {
        pass: report.pass_all
            && entry_max_abs_error <= GOLDEN_COORDINATE_TOLERANCE
            && exit_max_abs_error <= GOLDEN_COORDINATE_TOLERANCE,
        coordinate_tolerance: GOLDEN_COORDINATE_TOLERANCE,
        entry_max_abs_error,
        exit_max_abs_error,
        python_golden_receipt: GOLDEN_RECEIPT_129.into(),
        rust_receipt: report.receipt,
        receipt_identical,
    })
}

pub fn logical_sample_indices(logical_count: u64, rendered_count: u64) -> Result<Vec<u64>, String> {
    if logical_count < 1 {
        return Err("logical_count must be positive".into());
    }
    if rendered_count < 1 {
        return Err("rendered_count must be positive".into());
    }
    if rendered_count > logical_count {
        return Err("rendered_count cannot exceed logical_count".into());
    }
    Ok((0..rendered_count)
        .map(|index| {
            ((index as u128 * logical_count as u128) / rendered_count as u128) as u64
        })
        .collect())
}

pub fn report_json(report: &VerifyReport) -> Result<String, String> {
    serde_json::to_string_pretty(report).map_err(|error| error.to_string())
}

pub fn conformance_json(result: &ConformanceResult) -> Result<String, String> {
    serde_json::to_string_pretty(result).map_err(|error| error.to_string())
}

pub fn trace_csv(rows: &[Sample]) -> String {
    let mut output = String::from(
        "p,s,x,y,z,kappa,tau,tx,ty,tz,nx,ny,nz,bx,by,bz,radius\n",
    );
    for row in rows {
        let values = [
            row.p,
            row.s,
            row.x,
            row.y,
            row.z,
            row.kappa,
            row.tau,
            row.tx,
            row.ty,
            row.tz,
            row.nx,
            row.ny,
            row.nz,
            row.bx,
            row.by,
            row.bz,
            row.radius(),
        ];
        output.push_str(
            &values
                .into_iter()
                .map(|value| format!("{value:.17e}"))
                .collect::<Vec<_>>()
                .join(","),
        );
        output.push('\n');
    }
    output
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_path_satisfies_contracts() {
        let config = ModelConfig {
            samples: 129,
            ..ModelConfig::default()
        };
        let (rows, report) = build_and_verify(config).expect("reference path");
        assert_eq!(rows.len(), 129);
        assert!(report.pass_all);
        assert_eq!(rows[64].p, 0.5);
        assert!(rows[64].position().norm() <= 1.0e-12);
    }

    #[test]
    fn matches_python_golden_coordinates() {
        let result = check_python_conformance().expect("conformance result");
        assert!(result.pass, "{result:?}");
    }

    #[test]
    fn logical_sampling_is_exact() {
        let indices = logical_sample_indices(1_048_576, 8).expect("indices");
        assert_eq!(indices[0], 0);
        assert_eq!(indices.len(), 8);
        assert!(indices.windows(2).all(|pair| pair[0] < pair[1]));
    }

    #[test]
    fn invalid_even_sample_count_is_rejected() {
        let config = ModelConfig {
            samples: 128,
            ..ModelConfig::default()
        };
        assert!(config.validate().is_err());
    }
}
