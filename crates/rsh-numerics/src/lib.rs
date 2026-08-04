//! Separately versioned numerical research for full Frenet–Serret path integration.
//!
//! This crate does not replace the canonical geometry oracle in `rsh-core`.
//! It provides a path-level f64 reference for accelerator research, using a
//! midpoint Lie-group update on SO(3), midpoint position quadrature, and an
//! explicit modified Gram–Schmidt projection after each frame step.

use rsh_core::{
    kappa_max, kappa_schedule, tau_schedule, ModelConfig, Sample, Vec3, MODEL_NAME, MODEL_VERSION,
    TAU_MAX_EXCLUSIVE, TAU_MIN_EXCLUSIVE,
};
use serde::Serialize;

pub const NUMERICAL_CONTRACT: &str = "RSH-FRENET-NUMERICS-V1";
pub const PATH_SCHEMA: &str = "RSH-FRENET-PATH-RUN-V1";
pub const INTEGRATOR: &str = "lie-midpoint-so3-projected-v1";
pub const MAX_PATH_SAMPLES: usize = 262_145;
pub const FRAME_TOLERANCE_F64: f64 = 1.0e-12;
pub const CENTRE_TOLERANCE_F64: f64 = 1.0e-12;

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct FrenetPathReport {
    pub schema: &'static str,
    pub numerical_contract: &'static str,
    pub integrator: &'static str,
    pub implementation: &'static str,
    pub implementation_version: &'static str,
    pub model: &'static str,
    pub model_version: &'static str,
    pub samples: usize,
    pub s0: f64,
    pub s1: f64,
    pub kappa_fraction: f64,
    pub tau_floor: f64,
    pub tau_amplitude: f64,
    pub centering_mode: &'static str,
    pub projection_policy: &'static str,
    pub path_length: f64,
    pub entry: [f64; 3],
    pub centre: [f64; 3],
    pub exit: [f64; 3],
    pub entry_tangent: [f64; 3],
    pub centre_tangent: [f64; 3],
    pub exit_tangent: [f64; 3],
    pub centre_normal: [f64; 3],
    pub centre_binormal: [f64; 3],
    pub max_frame_norm_error: f64,
    pub max_frame_orthogonality_error: f64,
    pub kappa_violations: usize,
    pub tau_violations: usize,
    pub pass_finite: bool,
    pub pass_centre: bool,
    pub pass_frame: bool,
    pub pass_kappa: bool,
    pub pass_tau: bool,
    pub pass_all: bool,
    pub geometry_receipt_authority: bool,
    pub speedup_claim: bool,
    pub evidence_note: &'static str,
}

fn validate_research_config(config: ModelConfig) -> Result<ModelConfig, String> {
    let config = config.validate()?;
    if config.samples > MAX_PATH_SAMPLES {
        return Err(format!(
            "research path samples cannot exceed {MAX_PATH_SAMPLES}"
        ));
    }
    Ok(config)
}

fn checked_schedule(s: f64, config: ModelConfig) -> Result<(f64, f64), String> {
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

fn orthonormalize(tangent: Vec3, normal: Vec3) -> Result<(Vec3, Vec3, Vec3), String> {
    let tangent = tangent.normalize()?;
    let normal = normal
        .minus(tangent.scale(normal.dot(tangent)))
        .normalize()?;
    let binormal = tangent.cross(normal).normalize()?;
    Ok((tangent, normal, binormal))
}

fn rotate_body(vector: Vec3, omega: Vec3, step: f64) -> Result<Vec3, String> {
    if !vector.is_finite() || !omega.is_finite() || !step.is_finite() {
        return Err("non-finite Lie rotation input".into());
    }
    let magnitude = omega.norm();
    if magnitude <= 1.0e-15 {
        return Ok(vector);
    }
    let axis = omega.scale(1.0 / magnitude);
    let angle = magnitude * step;
    let cosine = angle.cos();
    let sine = angle.sin();
    Ok(vector
        .scale(cosine)
        .plus(axis.cross(vector).scale(sine))
        .plus(axis.scale(axis.dot(vector) * (1.0 - cosine))))
}

fn world_from_body(tangent: Vec3, normal: Vec3, binormal: Vec3, body: Vec3) -> Vec3 {
    tangent
        .scale(body.x)
        .plus(normal.scale(body.y))
        .plus(binormal.scale(body.z))
}

pub fn integrate_lie_midpoint(config: ModelConfig) -> Result<Vec<Sample>, String> {
    let config = validate_research_config(config)?;
    let ds = (config.s1 - config.s0) / (config.samples - 1) as f64;
    let body_tangent = Vec3::new(1.0, 0.0, 0.0);
    let body_normal = Vec3::new(0.0, 1.0, 0.0);
    let body_binormal = Vec3::new(0.0, 0.0, 1.0);

    let mut tangent = body_tangent;
    let mut normal = body_normal;
    let mut binormal = body_binormal;
    let mut position = Vec3::default();
    let mut rows = Vec::with_capacity(config.samples);

    for index in 0..config.samples {
        let s = config.s0 + index as f64 * ds;
        let p = index as f64 / (config.samples - 1) as f64;
        let (kappa, tau) = checked_schedule(s, config)?;
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

        let midpoint = s + 0.5 * ds;
        let (kappa_mid, tau_mid) = checked_schedule(midpoint, config)?;
        let body_omega = Vec3::new(tau_mid, 0.0, kappa_mid);

        let midpoint_body_tangent = rotate_body(body_tangent, body_omega, 0.5 * ds)?;
        let midpoint_world_tangent =
            world_from_body(tangent, normal, binormal, midpoint_body_tangent);
        position = position.plus(midpoint_world_tangent.scale(ds));

        let next_tangent = world_from_body(
            tangent,
            normal,
            binormal,
            rotate_body(body_tangent, body_omega, ds)?,
        );
        let next_normal = world_from_body(
            tangent,
            normal,
            binormal,
            rotate_body(body_normal, body_omega, ds)?,
        );
        let next_binormal = world_from_body(
            tangent,
            normal,
            binormal,
            rotate_body(body_binormal, body_omega, ds)?,
        );
        let (projected_tangent, projected_normal, projected_binormal) =
            orthonormalize(next_tangent, next_normal)?;
        tangent = projected_tangent;
        normal = projected_normal;
        binormal = projected_binormal;

        if !next_binormal.is_finite() {
            return Err("non-finite binormal produced by Lie update".into());
        }
    }

    let centre = rows[rows.len() / 2].position();
    for row in &mut rows {
        row.x -= centre.x;
        row.y -= centre.y;
        row.z -= centre.z;
    }
    Ok(rows)
}

fn max_frame_errors(rows: &[Sample]) -> Result<(f64, f64), String> {
    let mut norm_error = 0.0_f64;
    let mut orthogonality_error = 0.0_f64;
    for (index, row) in rows.iter().copied().enumerate() {
        let frame = [row.tangent(), row.normal(), row.binormal()];
        if !row.position().is_finite() || !frame.iter().all(|vector| vector.is_finite()) {
            return Err(format!("sample {index} contains a non-finite path value"));
        }
        for vector in frame {
            norm_error = norm_error.max((vector.norm() - 1.0).abs());
        }
        orthogonality_error = orthogonality_error
            .max(frame[0].dot(frame[1]).abs())
            .max(frame[0].dot(frame[2]).abs())
            .max(frame[1].dot(frame[2]).abs());
    }
    Ok((norm_error, orthogonality_error))
}

pub fn analyse_lie_path(rows: &[Sample], config: ModelConfig) -> Result<FrenetPathReport, String> {
    let config = validate_research_config(config)?;
    if rows.len() != config.samples {
        return Err("row count does not match the research configuration".into());
    }

    let (max_frame_norm_error, max_frame_orthogonality_error) = max_frame_errors(rows)?;
    let centre = rows[rows.len() / 2];
    let mut path_length = 0.0;
    for pair in rows.windows(2) {
        path_length += pair[1].position().minus(pair[0].position()).norm();
    }

    let kappa_violations = rows
        .iter()
        .filter(|row| !(0.0 <= row.kappa && row.kappa <= kappa_max() + 1.0e-12))
        .count();
    let tau_violations = rows
        .iter()
        .filter(|row| !(TAU_MIN_EXCLUSIVE < row.tau && row.tau < TAU_MAX_EXCLUSIVE))
        .count();
    let pass_finite = rows.iter().all(|row| {
        row.position().is_finite()
            && row.tangent().is_finite()
            && row.normal().is_finite()
            && row.binormal().is_finite()
            && row.kappa.is_finite()
            && row.tau.is_finite()
    });
    let pass_centre = centre.p == 0.5 && centre.position().norm() <= CENTRE_TOLERANCE_F64;
    let pass_frame = max_frame_norm_error <= FRAME_TOLERANCE_F64
        && max_frame_orthogonality_error <= FRAME_TOLERANCE_F64;
    let pass_kappa = kappa_violations == 0;
    let pass_tau = tau_violations == 0;
    let pass_all = pass_finite && pass_centre && pass_frame && pass_kappa && pass_tau;

    Ok(FrenetPathReport {
        schema: PATH_SCHEMA,
        numerical_contract: NUMERICAL_CONTRACT,
        integrator: INTEGRATOR,
        implementation: "rust-f64",
        implementation_version: env!("CARGO_PKG_VERSION"),
        model: MODEL_NAME,
        model_version: MODEL_VERSION,
        samples: rows.len(),
        s0: config.s0,
        s1: config.s1,
        kappa_fraction: config.kappa_fraction,
        tau_floor: config.tau_floor,
        tau_amplitude: config.tau_amplitude,
        centering_mode: "discrete-midpoint-to-origin",
        projection_policy: "modified-gram-schmidt-after-each-step",
        path_length,
        entry: rows[0].position().as_array(),
        centre: centre.position().as_array(),
        exit: rows[rows.len() - 1].position().as_array(),
        entry_tangent: rows[0].tangent().as_array(),
        centre_tangent: centre.tangent().as_array(),
        exit_tangent: rows[rows.len() - 1].tangent().as_array(),
        centre_normal: centre.normal().as_array(),
        centre_binormal: centre.binormal().as_array(),
        max_frame_norm_error,
        max_frame_orthogonality_error,
        kappa_violations,
        tau_violations,
        pass_finite,
        pass_centre,
        pass_frame,
        pass_kappa,
        pass_tau,
        pass_all,
        geometry_receipt_authority: false,
        speedup_claim: false,
        evidence_note: "This separately versioned numerical path is an accelerator-conformance reference. It does not replace the canonical geometry report or receipt.",
    })
}

pub fn build_lie_path(config: ModelConfig) -> Result<(Vec<Sample>, FrenetPathReport), String> {
    let config = validate_research_config(config)?;
    let rows = integrate_lie_midpoint(config)?;
    let report = analyse_lie_path(&rows, config)?;
    Ok((rows, report))
}

pub fn report_json(report: &FrenetPathReport) -> Result<String, String> {
    serde_json::to_string_pretty(report).map_err(|error| error.to_string())
}

pub fn trace_csv(rows: &[Sample]) -> String {
    let mut output = String::from("index,p,s,x,y,z,kappa,tau,tx,ty,tz,nx,ny,nz,bx,by,bz\n");
    for (index, row) in rows.iter().enumerate() {
        let values = [
            row.p, row.s, row.x, row.y, row.z, row.kappa, row.tau, row.tx, row.ty, row.tz, row.nx,
            row.ny, row.nz, row.bx, row.by, row.bz,
        ];
        output.push_str(&index.to_string());
        output.push(',');
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

    fn max_abs(actual: [f64; 3], expected: [f64; 3]) -> f64 {
        actual
            .into_iter()
            .zip(expected)
            .map(|(left, right)| (left - right).abs())
            .fold(0.0_f64, f64::max)
    }

    #[test]
    fn sealed_1025_path_matches_reference_vectors() {
        let config = ModelConfig {
            samples: 1025,
            ..ModelConfig::default()
        };
        let (rows, report) = build_lie_path(config).expect("Lie midpoint path");
        assert_eq!(rows.len(), 1025);
        assert!(report.pass_all, "{report:?}");
        assert!(
            max_abs(
                report.entry,
                [
                    -1.8484923969357088,
                    -0.6353472456353664,
                    -0.16597476619143556
                ]
            ) <= 5.0e-12
        );
        assert!(
            max_abs(
                report.exit,
                [1.209_732_453_902_619, 1.2168604543524748, 0.9663401678690707]
            ) <= 5.0e-12
        );
        assert!(max_abs(report.centre, [0.0, 0.0, 0.0]) <= 1.0e-15);
    }

    #[test]
    fn deterministic_stress_corpus_preserves_the_contract() {
        let mut state = 0x9e37_79b9_7f4a_7c15_u64;
        for _ in 0..96 {
            state = state
                .wrapping_mul(6_364_136_223_846_793_005)
                .wrapping_add(1_442_695_040_888_963_407);
            let samples = 3 + 2 * (state as usize % 513);
            let unit_a = ((state >> 11) as f64) / ((1_u64 << 53) as f64);
            state = state.rotate_left(23) ^ 0xa076_1d64_78bd_642f;
            let unit_b = ((state >> 11) as f64) / ((1_u64 << 53) as f64);
            state = state.rotate_left(17) ^ 0xe703_7ed1_a0b4_28db;
            let unit_c = ((state >> 11) as f64) / ((1_u64 << 53) as f64);

            let tau_floor = 1.0e-4 + 0.80 * unit_b;
            let maximum_amplitude = 0.49 * (1.0 - tau_floor);
            let config = ModelConfig {
                samples,
                s0: -2.0 + 4.0 * unit_c,
                s1: 2.01 + 12.0 * unit_c,
                kappa_fraction: 1.0e-6 + (1.0 - 1.0e-6) * unit_a,
                tau_floor,
                tau_amplitude: maximum_amplitude * unit_c,
            };
            let (_, report) = build_lie_path(config).expect("stress path");
            assert!(report.pass_all, "{report:?}");
        }
    }

    #[test]
    fn even_and_oversized_grids_are_rejected() {
        let even = ModelConfig {
            samples: 1024,
            ..ModelConfig::default()
        };
        assert!(build_lie_path(even).is_err());

        let oversized = ModelConfig {
            samples: MAX_PATH_SAMPLES + 2,
            ..ModelConfig::default()
        };
        assert!(build_lie_path(oversized).is_err());
    }
}
