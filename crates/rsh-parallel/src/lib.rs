//! Deterministic parallel-prefix research for full Frenet path construction.
//!
//! This crate defines `RSH-FRENET-PARALLEL-V1`, a separate numerical contract
//! for accelerator research. It expresses each path interval as a local SE(3)
//! transform and evaluates all prefixes with a deterministic inclusive doubling
//! scan. It does not replace the canonical geometry oracle or the existing
//! projected sequential numerical contract.

use rsh_core::{
    kappa_max, kappa_schedule, tau_schedule, ModelConfig, MODEL_NAME, MODEL_VERSION,
    TAU_MAX_EXCLUSIVE, TAU_MIN_EXCLUSIVE,
};
use serde::Serialize;

pub const PARALLEL_CONTRACT: &str = "RSH-FRENET-PARALLEL-V1";
pub const PARALLEL_SCHEMA: &str = "RSH-FRENET-PARALLEL-RUN-V1";
pub const SCAN_POLICY: &str = "hillis-steele-inclusive-se3-v1";
pub const INTERVAL_POLICY: &str = "midpoint-rodrigues-se3-v1";
pub const MAX_PARALLEL_SAMPLES: usize = 262_145;
pub const FRAME_TOLERANCE_F64: f64 = 1.0e-11;
pub const CENTRE_TOLERANCE_F64: f64 = 1.0e-12;
pub const SCAN_EQUIVALENCE_TOLERANCE_F64: f64 = 1.0e-11;

#[derive(Clone, Copy, Debug, Default, PartialEq)]
struct V3 {
    x: f64,
    y: f64,
    z: f64,
}

impl V3 {
    const fn new(x: f64, y: f64, z: f64) -> Self {
        Self { x, y, z }
    }

    fn plus(self, other: Self) -> Self {
        Self::new(self.x + other.x, self.y + other.y, self.z + other.z)
    }

    fn minus(self, other: Self) -> Self {
        Self::new(self.x - other.x, self.y - other.y, self.z - other.z)
    }

    fn scale(self, factor: f64) -> Self {
        Self::new(self.x * factor, self.y * factor, self.z * factor)
    }

    fn dot(self, other: Self) -> f64 {
        self.x * other.x + self.y * other.y + self.z * other.z
    }

    fn cross(self, other: Self) -> Self {
        Self::new(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )
    }

    fn norm(self) -> f64 {
        self.dot(self).sqrt()
    }

    fn is_finite(self) -> bool {
        self.x.is_finite() && self.y.is_finite() && self.z.is_finite()
    }

    const fn as_array(self) -> [f64; 3] {
        [self.x, self.y, self.z]
    }
}

#[derive(Clone, Copy, Debug, PartialEq)]
struct Se3 {
    tangent: V3,
    normal: V3,
    binormal: V3,
    translation: V3,
}

impl Se3 {
    const fn identity() -> Self {
        Self {
            tangent: V3::new(1.0, 0.0, 0.0),
            normal: V3::new(0.0, 1.0, 0.0),
            binormal: V3::new(0.0, 0.0, 1.0),
            translation: V3::new(0.0, 0.0, 0.0),
        }
    }

    fn rotate(self, vector: V3) -> V3 {
        self.tangent
            .scale(vector.x)
            .plus(self.normal.scale(vector.y))
            .plus(self.binormal.scale(vector.z))
    }

    /// Compose `self` followed by `right` while preserving interval order.
    fn compose(self, right: Self) -> Self {
        Self {
            tangent: self.rotate(right.tangent),
            normal: self.rotate(right.normal),
            binormal: self.rotate(right.binormal),
            translation: self.translation.plus(self.rotate(right.translation)),
        }
    }

    fn is_finite(self) -> bool {
        self.tangent.is_finite()
            && self.normal.is_finite()
            && self.binormal.is_finite()
            && self.translation.is_finite()
    }

    fn snapshot(self) -> TransformSnapshot {
        TransformSnapshot {
            tangent: self.tangent.as_array(),
            normal: self.normal.as_array(),
            binormal: self.binormal.as_array(),
            translation: self.translation.as_array(),
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct TransformSnapshot {
    pub tangent: [f64; 3],
    pub normal: [f64; 3],
    pub binormal: [f64; 3],
    pub translation: [f64; 3],
}

impl TransformSnapshot {
    fn transform(self) -> Se3 {
        Se3 {
            tangent: V3::new(self.tangent[0], self.tangent[1], self.tangent[2]),
            normal: V3::new(self.normal[0], self.normal[1], self.normal[2]),
            binormal: V3::new(self.binormal[0], self.binormal[1], self.binormal[2]),
            translation: V3::new(
                self.translation[0],
                self.translation[1],
                self.translation[2],
            ),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct ParallelPoint {
    pub index: usize,
    pub p: f64,
    pub s: f64,
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

impl ParallelPoint {
    fn position(&self) -> V3 {
        V3::new(self.x, self.y, self.z)
    }

    fn frame(&self) -> [V3; 3] {
        [
            V3::new(self.tx, self.ty, self.tz),
            V3::new(self.nx, self.ny, self.nz),
            V3::new(self.bx, self.by, self.bz),
        ]
    }
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct SegmentSummary {
    pub schema: &'static str,
    pub start_interval: usize,
    pub end_interval_exclusive: usize,
    pub interval_count: usize,
    pub transform: TransformSnapshot,
    pub geometry_receipt_authority: bool,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct ParallelPathReport {
    pub schema: &'static str,
    pub parallel_contract: &'static str,
    pub interval_policy: &'static str,
    pub scan_policy: &'static str,
    pub implementation: &'static str,
    pub implementation_version: &'static str,
    pub model: &'static str,
    pub model_version: &'static str,
    pub samples: usize,
    pub intervals: usize,
    pub scan_passes: usize,
    pub s0: f64,
    pub s1: f64,
    pub kappa_fraction: f64,
    pub tau_floor: f64,
    pub tau_amplitude: f64,
    pub centering_mode: &'static str,
    pub path_length: f64,
    pub entry: [f64; 3],
    pub centre: [f64; 3],
    pub exit: [f64; 3],
    pub centre_tangent: [f64; 3],
    pub centre_normal: [f64; 3],
    pub centre_binormal: [f64; 3],
    pub max_frame_norm_error: f64,
    pub max_frame_orthogonality_error: f64,
    pub max_scan_vs_sequential_component_error: f64,
    pub max_shard_merge_component_error: f64,
    pub shard_interval_width: usize,
    pub shard_count: usize,
    pub pass_finite: bool,
    pub pass_centre: bool,
    pub pass_frame: bool,
    pub pass_schedule_bounds: bool,
    pub pass_scan_equivalence: bool,
    pub pass_shard_merge: bool,
    pub pass_all: bool,
    pub actual_parallel_hardware_execution: bool,
    pub distributed_execution: bool,
    pub speedup_claim: bool,
    pub geometry_receipt_authority: bool,
    pub evidence_note: &'static str,
}

fn validate_config(config: ModelConfig) -> Result<ModelConfig, String> {
    let config = config.validate()?;
    if config.samples > MAX_PARALLEL_SAMPLES {
        return Err(format!(
            "parallel research samples cannot exceed {MAX_PARALLEL_SAMPLES}"
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

fn rotate_body(vector: V3, omega: V3, step: f64) -> Result<V3, String> {
    if !vector.is_finite() || !omega.is_finite() || !step.is_finite() {
        return Err("non-finite parallel interval rotation input".into());
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

fn local_interval(midpoint: f64, ds: f64, config: ModelConfig) -> Result<Se3, String> {
    let (kappa, tau) = checked_schedule(midpoint, config)?;
    let omega = V3::new(tau, 0.0, kappa);
    let tangent = rotate_body(V3::new(1.0, 0.0, 0.0), omega, ds)?;
    let normal = rotate_body(V3::new(0.0, 1.0, 0.0), omega, ds)?;
    let binormal = rotate_body(V3::new(0.0, 0.0, 1.0), omega, ds)?;
    let translation = rotate_body(V3::new(1.0, 0.0, 0.0), omega, 0.5 * ds)?.scale(ds);
    let transform = Se3 {
        tangent,
        normal,
        binormal,
        translation,
    };
    if !transform.is_finite() {
        return Err("parallel interval produced a non-finite transform".into());
    }
    Ok(transform)
}

fn interval_transforms(config: ModelConfig) -> Result<Vec<Se3>, String> {
    let ds = (config.s1 - config.s0) / (config.samples - 1) as f64;
    let mut transforms = Vec::with_capacity(config.samples);
    transforms.push(Se3::identity());
    for interval in 0..config.samples - 1 {
        let midpoint = config.s0 + (interval as f64 + 0.5) * ds;
        transforms.push(local_interval(midpoint, ds, config)?);
    }
    Ok(transforms)
}

fn sequential_prefixes(transforms: &[Se3]) -> Vec<Se3> {
    let mut prefixes = Vec::with_capacity(transforms.len());
    let mut current = Se3::identity();
    prefixes.push(current);
    for transform in transforms.iter().copied().skip(1) {
        current = current.compose(transform);
        prefixes.push(current);
    }
    prefixes
}

fn inclusive_doubling_scan(transforms: &[Se3]) -> (Vec<Se3>, usize) {
    let mut current = transforms.to_vec();
    let mut offset = 1usize;
    let mut passes = 0usize;
    while offset < current.len() {
        let previous = current.clone();
        for index in offset..current.len() {
            current[index] = previous[index - offset].compose(previous[index]);
        }
        offset = offset.saturating_mul(2);
        passes += 1;
    }
    (current, passes)
}

fn max_transform_component_error(left: Se3, right: Se3) -> f64 {
    let left = [
        left.tangent,
        left.normal,
        left.binormal,
        left.translation,
    ];
    let right = [
        right.tangent,
        right.normal,
        right.binormal,
        right.translation,
    ];
    left.into_iter()
        .zip(right)
        .flat_map(|(a, b)| {
            [
                (a.x - b.x).abs(),
                (a.y - b.y).abs(),
                (a.z - b.z).abs(),
            ]
        })
        .fold(0.0_f64, f64::max)
}

fn max_prefix_error(left: &[Se3], right: &[Se3]) -> Result<f64, String> {
    if left.len() != right.len() {
        return Err("parallel prefix sequences have different lengths".into());
    }
    Ok(left
        .iter()
        .copied()
        .zip(right.iter().copied())
        .map(|(a, b)| max_transform_component_error(a, b))
        .fold(0.0_f64, f64::max))
}

pub fn segment_summaries(
    config: ModelConfig,
    interval_width: usize,
) -> Result<Vec<SegmentSummary>, String> {
    let config = validate_config(config)?;
    if interval_width == 0 {
        return Err("segment interval width must be positive".into());
    }
    let transforms = interval_transforms(config)?;
    let intervals = &transforms[1..];
    let mut summaries = Vec::with_capacity(intervals.len().div_ceil(interval_width));
    for (segment_index, chunk) in intervals.chunks(interval_width).enumerate() {
        let start_interval = segment_index * interval_width;
        let mut reduction = Se3::identity();
        for transform in chunk.iter().copied() {
            reduction = reduction.compose(transform);
        }
        summaries.push(SegmentSummary {
            schema: "RSH-FRENET-PARALLEL-SEGMENT-V1",
            start_interval,
            end_interval_exclusive: start_interval + chunk.len(),
            interval_count: chunk.len(),
            transform: reduction.snapshot(),
            geometry_receipt_authority: false,
        });
    }
    Ok(summaries)
}

pub fn merge_segment_summaries(summaries: &[SegmentSummary]) -> Result<TransformSnapshot, String> {
    let mut expected_start = 0usize;
    let mut reduction = Se3::identity();
    for summary in summaries {
        if summary.schema != "RSH-FRENET-PARALLEL-SEGMENT-V1" {
            return Err("unexpected parallel segment schema".into());
        }
        if summary.start_interval != expected_start
            || summary.end_interval_exclusive
                != summary.start_interval + summary.interval_count
        {
            return Err("parallel segment summaries are missing, overlapping, or unordered".into());
        }
        let transform = summary.transform.transform();
        if !transform.is_finite() {
            return Err("parallel segment summary contains a non-finite transform".into());
        }
        reduction = reduction.compose(transform);
        expected_start = summary.end_interval_exclusive;
    }
    Ok(reduction.snapshot())
}

fn points_from_prefixes(
    prefixes: &[Se3],
    config: ModelConfig,
) -> Result<Vec<ParallelPoint>, String> {
    let denominator = (config.samples - 1) as f64;
    let ds = (config.s1 - config.s0) / denominator;
    let mut points = Vec::with_capacity(config.samples);
    for (index, transform) in prefixes.iter().copied().enumerate() {
        let p = index as f64 / denominator;
        let s = config.s0 + index as f64 * ds;
        let (kappa, tau) = checked_schedule(s, config)?;
        points.push(ParallelPoint {
            index,
            p,
            s,
            x: transform.translation.x,
            y: transform.translation.y,
            z: transform.translation.z,
            kappa,
            tau,
            tx: transform.tangent.x,
            ty: transform.tangent.y,
            tz: transform.tangent.z,
            nx: transform.normal.x,
            ny: transform.normal.y,
            nz: transform.normal.z,
            bx: transform.binormal.x,
            by: transform.binormal.y,
            bz: transform.binormal.z,
        });
    }

    let centre = points[points.len() / 2].position();
    for point in &mut points {
        point.x -= centre.x;
        point.y -= centre.y;
        point.z -= centre.z;
    }
    Ok(points)
}

fn frame_errors(points: &[ParallelPoint]) -> Result<(f64, f64), String> {
    let mut max_norm_error = 0.0_f64;
    let mut max_orthogonality_error = 0.0_f64;
    for point in points {
        if !point.position().is_finite()
            || !point.kappa.is_finite()
            || !point.tau.is_finite()
        {
            return Err(format!(
                "parallel point {} contains a non-finite value",
                point.index
            ));
        }
        let frame = point.frame();
        if !frame.iter().all(|vector| vector.is_finite()) {
            return Err(format!(
                "parallel point {} contains a non-finite frame",
                point.index
            ));
        }
        for vector in frame {
            max_norm_error = max_norm_error.max((vector.norm() - 1.0).abs());
        }
        max_orthogonality_error = max_orthogonality_error
            .max(frame[0].dot(frame[1]).abs())
            .max(frame[0].dot(frame[2]).abs())
            .max(frame[1].dot(frame[2]).abs());
    }
    Ok((max_norm_error, max_orthogonality_error))
}

pub fn build_parallel_path(
    config: ModelConfig,
) -> Result<(Vec<ParallelPoint>, ParallelPathReport), String> {
    let config = validate_config(config)?;
    let transforms = interval_transforms(config)?;
    let sequential = sequential_prefixes(&transforms);
    let (parallel, scan_passes) = inclusive_doubling_scan(&transforms);
    let max_scan_vs_sequential_component_error = max_prefix_error(&parallel, &sequential)?;
    let points = points_from_prefixes(&parallel, config)?;
    let (max_frame_norm_error, max_frame_orthogonality_error) = frame_errors(&points)?;

    let shard_interval_width = 128usize;
    let summaries = segment_summaries(config, shard_interval_width)?;
    let merged = merge_segment_summaries(&summaries)?.transform();
    let expected_final = sequential
        .last()
        .copied()
        .ok_or_else(|| "parallel path produced no final transform".to_string())?;
    let max_shard_merge_component_error = max_transform_component_error(merged, expected_final);

    let centre = &points[points.len() / 2];
    let mut path_length = 0.0_f64;
    for pair in points.windows(2) {
        path_length += pair[1].position().minus(pair[0].position()).norm();
    }

    let pass_finite = points.iter().all(|point| {
        point.position().is_finite()
            && point.frame().iter().all(|vector| vector.is_finite())
            && point.kappa.is_finite()
            && point.tau.is_finite()
    });
    let pass_centre = centre.p == 0.5 && centre.position().norm() <= CENTRE_TOLERANCE_F64;
    let pass_frame = max_frame_norm_error <= FRAME_TOLERANCE_F64
        && max_frame_orthogonality_error <= FRAME_TOLERANCE_F64;
    let pass_schedule_bounds = points.iter().all(|point| {
        0.0 <= point.kappa
            && point.kappa <= kappa_max() + 1.0e-12
            && TAU_MIN_EXCLUSIVE < point.tau
            && point.tau < TAU_MAX_EXCLUSIVE
    });
    let pass_scan_equivalence =
        max_scan_vs_sequential_component_error <= SCAN_EQUIVALENCE_TOLERANCE_F64;
    let pass_shard_merge =
        max_shard_merge_component_error <= SCAN_EQUIVALENCE_TOLERANCE_F64;
    let pass_all = pass_finite
        && pass_centre
        && pass_frame
        && pass_schedule_bounds
        && pass_scan_equivalence
        && pass_shard_merge;

    let report = ParallelPathReport {
        schema: PARALLEL_SCHEMA,
        parallel_contract: PARALLEL_CONTRACT,
        interval_policy: INTERVAL_POLICY,
        scan_policy: SCAN_POLICY,
        implementation: "rust-f64",
        implementation_version: env!("CARGO_PKG_VERSION"),
        model: MODEL_NAME,
        model_version: MODEL_VERSION,
        samples: points.len(),
        intervals: points.len() - 1,
        scan_passes,
        s0: config.s0,
        s1: config.s1,
        kappa_fraction: config.kappa_fraction,
        tau_floor: config.tau_floor,
        tau_amplitude: config.tau_amplitude,
        centering_mode: "discrete-midpoint-to-origin",
        path_length,
        entry: points[0].position().as_array(),
        centre: centre.position().as_array(),
        exit: points[points.len() - 1].position().as_array(),
        centre_tangent: [centre.tx, centre.ty, centre.tz],
        centre_normal: [centre.nx, centre.ny, centre.nz],
        centre_binormal: [centre.bx, centre.by, centre.bz],
        max_frame_norm_error,
        max_frame_orthogonality_error,
        max_scan_vs_sequential_component_error,
        max_shard_merge_component_error,
        shard_interval_width,
        shard_count: summaries.len(),
        pass_finite,
        pass_centre,
        pass_frame,
        pass_schedule_bounds,
        pass_scan_equivalence,
        pass_shard_merge,
        pass_all,
        actual_parallel_hardware_execution: false,
        distributed_execution: false,
        speedup_claim: false,
        geometry_receipt_authority: false,
        evidence_note: "The f64 scan defines a parallel accelerator correctness surface. Hardware speedup requires a real adapter benchmark sidecar, and no result replaces the canonical geometry report or receipt.",
    };
    Ok((points, report))
}

pub fn report_json(report: &ParallelPathReport) -> Result<String, String> {
    serde_json::to_string_pretty(report).map_err(|error| error.to_string())
}

pub fn trace_csv(points: &[ParallelPoint]) -> String {
    let mut output = String::from("index,p,s,x,y,z,kappa,tau,tx,ty,tz,nx,ny,nz,bx,by,bz\n");
    for point in points {
        output.push_str(&format!(
            "{},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}\n",
            point.index,
            point.p,
            point.s,
            point.x,
            point.y,
            point.z,
            point.kappa,
            point.tau,
            point.tx,
            point.ty,
            point.tz,
            point.nx,
            point.ny,
            point.nz,
            point.bx,
            point.by,
            point.bz,
        ));
    }
    output
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sealed_scan_is_finite_centred_and_equivalent() {
        let config = ModelConfig {
            samples: 1025,
            ..ModelConfig::default()
        };
        let (points, report) = build_parallel_path(config).expect("parallel path");
        assert_eq!(points.len(), 1025);
        assert_eq!(report.scan_passes, 11);
        assert!(report.pass_all, "{report:?}");
        assert!(report.max_scan_vs_sequential_component_error <= 1.0e-11);
        assert!(report.max_shard_merge_component_error <= 1.0e-11);
        assert_eq!(report.centre, [0.0, 0.0, 0.0]);
        assert!(!report.actual_parallel_hardware_execution);
        assert!(!report.speedup_claim);
        assert!(!report.geometry_receipt_authority);
    }

    #[test]
    fn scan_replays_deterministically() {
        let first = build_parallel_path(ModelConfig::default()).expect("first parallel path");
        let second = build_parallel_path(ModelConfig::default()).expect("second parallel path");
        assert_eq!(first, second);
    }

    #[test]
    fn ordered_shard_merge_matches_the_complete_reduction() {
        let config = ModelConfig {
            samples: 4097,
            ..ModelConfig::default()
        };
        let summaries = segment_summaries(config, 257).expect("segment summaries");
        let merged = merge_segment_summaries(&summaries).expect("merged summaries");
        let transforms = interval_transforms(config).expect("interval transforms");
        let sequential = sequential_prefixes(&transforms);
        let expected = sequential.last().copied().expect("final transform");
        assert!(max_transform_component_error(merged.transform(), expected) <= 1.0e-11);
    }

    #[test]
    fn unordered_or_missing_shards_are_rejected() {
        let config = ModelConfig::default();
        let mut summaries = segment_summaries(config, 32).expect("segment summaries");
        summaries.remove(0);
        assert!(merge_segment_summaries(&summaries)
            .expect_err("missing first shard must fail")
            .contains("missing, overlapping, or unordered"));
    }

    #[test]
    fn zero_width_segments_are_rejected() {
        assert!(segment_summaries(ModelConfig::default(), 0)
            .expect_err("zero width must fail")
            .contains("must be positive"));
    }
}
