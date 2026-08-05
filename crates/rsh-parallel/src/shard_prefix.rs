use crate::{
    build_parallel_path, ParallelPoint, CENTRE_TOLERANCE_F64, FRAME_TOLERANCE_F64, INTERVAL_POLICY,
    MAX_PARALLEL_SAMPLES, PARALLEL_CONTRACT, SCAN_EQUIVALENCE_TOLERANCE_F64,
};
use rsh_core::{
    kappa_max, kappa_schedule, tau_schedule, ModelConfig, MODEL_NAME, MODEL_VERSION,
    TAU_MAX_EXCLUSIVE, TAU_MIN_EXCLUSIVE,
};
use serde::Serialize;

pub const SHARD_PREFIX_CONTRACT: &str = "RSH-FRENET-SHARD-PREFIX-V1";
pub const SHARD_PREFIX_SCHEMA: &str = "RSH-FRENET-SHARD-PREFIX-RECONSTRUCTION-V1";
pub const SHARD_WORK_SCHEMA: &str = "RSH-FRENET-SHARD-WORK-V1";
pub const SHARD_BUNDLE_SCHEMA: &str = "RSH-FRENET-SHARD-BUNDLE-V1";
pub const LOCAL_PREFIX_POLICY: &str = "sequential-local-inclusive-se3-v1";
pub const SHARD_PREFIX_POLICY: &str = "hillis-steele-exclusive-shard-se3-v1";
pub const SHARD_ASSEMBLY_POLICY: &str = "ordered-base-compose-local-prefix-v1";
pub const SHARD_FINGERPRINT_POLICY: &str = "fnv1a64-domain-separated-evidence-only-v1";
pub const MAX_SHARD_COUNT: usize = 65_536;

const FNV_OFFSET_BASIS: u64 = 0xcbf29ce484222325;
const FNV_PRIME: u64 = 0x100000001b3;

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

    fn snapshot(self) -> ShardTransform {
        ShardTransform {
            tangent: self.tangent.as_array(),
            normal: self.normal.as_array(),
            binormal: self.binormal.as_array(),
            translation: self.translation.as_array(),
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct ShardTransform {
    pub tangent: [f64; 3],
    pub normal: [f64; 3],
    pub binormal: [f64; 3],
    pub translation: [f64; 3],
}

impl ShardTransform {
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

    fn is_finite(self) -> bool {
        self.transform().is_finite()
    }
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct ShardWorkUnit {
    pub schema: &'static str,
    pub shard_index: usize,
    pub start_interval: usize,
    pub end_interval_exclusive: usize,
    pub interval_count: usize,
    pub local_prefixes: Vec<ShardTransform>,
    pub reduction: ShardTransform,
    pub deterministic_fingerprint: String,
    pub fingerprint_policy: &'static str,
    pub geometry_receipt_authority: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct ShardConfigSnapshot {
    pub samples: usize,
    pub s0: f64,
    pub s1: f64,
    pub kappa_fraction: f64,
    pub tau_floor: f64,
    pub tau_amplitude: f64,
}

impl From<ModelConfig> for ShardConfigSnapshot {
    fn from(config: ModelConfig) -> Self {
        Self {
            samples: config.samples,
            s0: config.s0,
            s1: config.s1,
            kappa_fraction: config.kappa_fraction,
            tau_floor: config.tau_floor,
            tau_amplitude: config.tau_amplitude,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct ShardBundle {
    pub schema: &'static str,
    pub shard_prefix_contract: &'static str,
    pub source_parallel_contract: &'static str,
    pub interval_policy: &'static str,
    pub local_prefix_policy: &'static str,
    pub shard_prefix_policy: &'static str,
    pub assembly_policy: &'static str,
    pub fingerprint_policy: &'static str,
    pub configuration: ShardConfigSnapshot,
    pub expected_intervals: usize,
    pub interval_width: usize,
    pub shard_count: usize,
    pub shards: Vec<ShardWorkUnit>,
    pub manifest_fingerprint: String,
    pub actual_multi_device_execution: bool,
    pub distributed_execution: bool,
    pub geometry_receipt_authority: bool,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct ShardPrefixReport {
    pub schema: &'static str,
    pub shard_prefix_contract: &'static str,
    pub source_parallel_contract: &'static str,
    pub interval_policy: &'static str,
    pub local_prefix_policy: &'static str,
    pub shard_prefix_policy: &'static str,
    pub assembly_policy: &'static str,
    pub fingerprint_policy: &'static str,
    pub implementation: &'static str,
    pub implementation_version: &'static str,
    pub model: &'static str,
    pub model_version: &'static str,
    pub samples: usize,
    pub intervals: usize,
    pub interval_width: usize,
    pub shard_count: usize,
    pub shard_prefix_passes: usize,
    pub reconstructed_prefix_count: usize,
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
    pub max_frame_norm_error: f64,
    pub max_frame_orthogonality_error: f64,
    pub max_local_tail_vs_reduction_component_error: f64,
    pub max_reconstruction_vs_parallel_component_error: f64,
    pub manifest_fingerprint: String,
    pub pass_finite: bool,
    pub pass_coverage: bool,
    pub pass_fingerprints: bool,
    pub pass_local_prefix_integrity: bool,
    pub pass_reference_equivalence: bool,
    pub pass_centre: bool,
    pub pass_frame: bool,
    pub pass_schedule_bounds: bool,
    pub pass_all: bool,
    pub actual_local_shard_execution: bool,
    pub actual_multi_device_execution: bool,
    pub distributed_execution: bool,
    pub speedup_claim: bool,
    pub geometry_receipt_authority: bool,
    pub evidence_note: &'static str,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct ShardPrefixReconstruction {
    pub report: ShardPrefixReport,
    pub bundle: ShardBundle,
    pub points: Vec<ParallelPoint>,
}

fn validate_config(config: ModelConfig) -> Result<ModelConfig, String> {
    let config = config.validate()?;
    if config.samples > MAX_PARALLEL_SAMPLES {
        return Err(format!(
            "shard-prefix samples cannot exceed {MAX_PARALLEL_SAMPLES}"
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
        return Err("non-finite shard interval rotation input".into());
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
    let transform = Se3 {
        tangent: rotate_body(V3::new(1.0, 0.0, 0.0), omega, ds)?,
        normal: rotate_body(V3::new(0.0, 1.0, 0.0), omega, ds)?,
        binormal: rotate_body(V3::new(0.0, 0.0, 1.0), omega, ds)?,
        translation: rotate_body(V3::new(1.0, 0.0, 0.0), omega, 0.5 * ds)?.scale(ds),
    };
    if !transform.is_finite() {
        return Err("shard interval produced a non-finite transform".into());
    }
    Ok(transform)
}

fn interval_transforms(config: ModelConfig) -> Result<Vec<Se3>, String> {
    let ds = (config.s1 - config.s0) / (config.samples - 1) as f64;
    let mut transforms = Vec::with_capacity(config.samples - 1);
    for interval in 0..config.samples - 1 {
        let midpoint = config.s0 + (interval as f64 + 0.5) * ds;
        transforms.push(local_interval(midpoint, ds, config)?);
    }
    Ok(transforms)
}

fn max_transform_component_error(left: Se3, right: Se3) -> f64 {
    let left = [left.tangent, left.normal, left.binormal, left.translation];
    let right = [
        right.tangent,
        right.normal,
        right.binormal,
        right.translation,
    ];
    left.into_iter()
        .zip(right)
        .flat_map(|(a, b)| [(a.x - b.x).abs(), (a.y - b.y).abs(), (a.z - b.z).abs()])
        .fold(0.0_f64, f64::max)
}

fn fnv_update(mut state: u64, bytes: &[u8]) -> u64 {
    for byte in bytes {
        state ^= u64::from(*byte);
        state = state.wrapping_mul(FNV_PRIME);
    }
    state
}

fn fnv_usize(state: u64, value: usize) -> u64 {
    fnv_update(state, &(value as u64).to_le_bytes())
}

fn fnv_transform(mut state: u64, transform: ShardTransform) -> u64 {
    for value in transform
        .tangent
        .into_iter()
        .chain(transform.normal)
        .chain(transform.binormal)
        .chain(transform.translation)
    {
        state = fnv_update(state, &value.to_bits().to_le_bytes());
    }
    state
}

fn fingerprint_shard(
    shard_index: usize,
    start_interval: usize,
    end_interval_exclusive: usize,
    local_prefixes: &[ShardTransform],
    reduction: ShardTransform,
) -> String {
    let mut state = fnv_update(FNV_OFFSET_BASIS, b"RSH-FRENET-SHARD-WORK-V1\0");
    state = fnv_usize(state, shard_index);
    state = fnv_usize(state, start_interval);
    state = fnv_usize(state, end_interval_exclusive);
    state = fnv_usize(state, local_prefixes.len());
    for transform in local_prefixes {
        state = fnv_transform(state, *transform);
    }
    state = fnv_transform(state, reduction);
    format!("{state:016x}")
}

fn fingerprint_manifest(shards: &[ShardWorkUnit]) -> String {
    let mut state = fnv_update(FNV_OFFSET_BASIS, b"RSH-FRENET-SHARD-MANIFEST-V1\0");
    state = fnv_usize(state, shards.len());
    for shard in shards {
        state = fnv_usize(state, shard.shard_index);
        state = fnv_update(state, shard.deterministic_fingerprint.as_bytes());
    }
    format!("{state:016x}")
}

pub fn build_shard_work_units(
    config: ModelConfig,
    interval_width: usize,
) -> Result<Vec<ShardWorkUnit>, String> {
    let config = validate_config(config)?;
    if interval_width == 0 {
        return Err("shard interval width must be positive".into());
    }
    let intervals = interval_transforms(config)?;
    let shard_count = intervals.len().div_ceil(interval_width);
    if shard_count == 0 || shard_count > MAX_SHARD_COUNT {
        return Err(format!("shard count must be in [1, {MAX_SHARD_COUNT}]"));
    }

    let mut shards = Vec::with_capacity(shard_count);
    for (shard_index, chunk) in intervals.chunks(interval_width).enumerate() {
        let start_interval = shard_index * interval_width;
        let end_interval_exclusive = start_interval + chunk.len();
        let mut current = Se3::identity();
        let mut local_prefixes = Vec::with_capacity(chunk.len());
        for transform in chunk.iter().copied() {
            current = current.compose(transform);
            local_prefixes.push(current.snapshot());
        }
        let reduction = current.snapshot();
        let deterministic_fingerprint = fingerprint_shard(
            shard_index,
            start_interval,
            end_interval_exclusive,
            &local_prefixes,
            reduction,
        );
        shards.push(ShardWorkUnit {
            schema: SHARD_WORK_SCHEMA,
            shard_index,
            start_interval,
            end_interval_exclusive,
            interval_count: chunk.len(),
            local_prefixes,
            reduction,
            deterministic_fingerprint,
            fingerprint_policy: SHARD_FINGERPRINT_POLICY,
            geometry_receipt_authority: false,
        });
    }
    Ok(shards)
}

fn validate_shard_work_units(
    shards: &[ShardWorkUnit],
    expected_intervals: usize,
) -> Result<(bool, bool, f64), String> {
    if expected_intervals == 0 {
        return Err("expected shard interval count must be positive".into());
    }
    if shards.is_empty() || shards.len() > MAX_SHARD_COUNT {
        return Err(format!(
            "shard work unit count must be in [1, {MAX_SHARD_COUNT}]"
        ));
    }

    let mut expected_start = 0usize;
    let mut max_tail_error = 0.0_f64;
    for (expected_index, shard) in shards.iter().enumerate() {
        if shard.schema != SHARD_WORK_SCHEMA {
            return Err("unexpected shard work schema".into());
        }
        if shard.shard_index != expected_index {
            return Err("shard work units are unordered".into());
        }
        if shard.geometry_receipt_authority {
            return Err("shard work unit cannot claim geometry authority".into());
        }
        if shard.fingerprint_policy != SHARD_FINGERPRINT_POLICY {
            return Err("unexpected shard fingerprint policy".into());
        }
        let declared_end = shard
            .start_interval
            .checked_add(shard.interval_count)
            .ok_or_else(|| "shard interval range overflow".to_string())?;
        if shard.interval_count == 0
            || shard.start_interval != expected_start
            || shard.end_interval_exclusive != declared_end
            || shard.local_prefixes.len() != shard.interval_count
        {
            return Err(
                "shard work units are missing, overlapping, malformed, or unordered".into(),
            );
        }
        if !shard.reduction.is_finite()
            || !shard
                .local_prefixes
                .iter()
                .all(|transform| transform.is_finite())
        {
            return Err("shard work unit contains a non-finite transform".into());
        }
        let expected_fingerprint = fingerprint_shard(
            shard.shard_index,
            shard.start_interval,
            shard.end_interval_exclusive,
            &shard.local_prefixes,
            shard.reduction,
        );
        if shard.deterministic_fingerprint != expected_fingerprint {
            return Err(format!(
                "shard {} deterministic fingerprint mismatch",
                shard.shard_index
            ));
        }
        let tail = shard
            .local_prefixes
            .last()
            .copied()
            .ok_or_else(|| "shard work unit has no local prefix tail".to_string())?;
        max_tail_error = max_tail_error.max(max_transform_component_error(
            tail.transform(),
            shard.reduction.transform(),
        ));
        expected_start = shard.end_interval_exclusive;
    }
    if expected_start != expected_intervals {
        return Err("shard work units do not cover the expected interval range".into());
    }
    Ok((true, true, max_tail_error))
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

pub fn reconstruct_shard_prefixes(
    shards: &[ShardWorkUnit],
    expected_intervals: usize,
) -> Result<(Vec<ShardTransform>, usize, f64), String> {
    let (_coverage, _fingerprints, max_tail_error) =
        validate_shard_work_units(shards, expected_intervals)?;
    let reductions = shards
        .iter()
        .map(|shard| shard.reduction.transform())
        .collect::<Vec<_>>();
    let (inclusive, passes) = inclusive_doubling_scan(&reductions);

    let mut bases = Vec::with_capacity(shards.len());
    bases.push(Se3::identity());
    bases.extend(
        inclusive
            .iter()
            .copied()
            .take(shards.len().saturating_sub(1)),
    );

    let mut prefixes = Vec::with_capacity(expected_intervals + 1);
    prefixes.push(Se3::identity().snapshot());
    for (shard, base) in shards.iter().zip(bases.iter().copied()) {
        for local_prefix in &shard.local_prefixes {
            prefixes.push(base.compose(local_prefix.transform()).snapshot());
        }
    }
    if prefixes.len() != expected_intervals + 1 {
        return Err("reconstructed shard prefix count does not match expected intervals".into());
    }
    Ok((prefixes, passes, max_tail_error))
}

fn points_from_prefixes(
    prefixes: &[ShardTransform],
    config: ModelConfig,
) -> Result<Vec<ParallelPoint>, String> {
    if prefixes.len() != config.samples {
        return Err("reconstructed prefix count does not match sample count".into());
    }
    let denominator = (config.samples - 1) as f64;
    let ds = (config.s1 - config.s0) / denominator;
    let mut points = Vec::with_capacity(config.samples);
    for (index, snapshot) in prefixes.iter().copied().enumerate() {
        let transform = snapshot.transform();
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
    let centre = V3::new(
        points[points.len() / 2].x,
        points[points.len() / 2].y,
        points[points.len() / 2].z,
    );
    for point in &mut points {
        point.x -= centre.x;
        point.y -= centre.y;
        point.z -= centre.z;
    }
    Ok(points)
}

fn point_position(point: &ParallelPoint) -> V3 {
    V3::new(point.x, point.y, point.z)
}

fn point_frame(point: &ParallelPoint) -> [V3; 3] {
    [
        V3::new(point.tx, point.ty, point.tz),
        V3::new(point.nx, point.ny, point.nz),
        V3::new(point.bx, point.by, point.bz),
    ]
}

fn frame_errors(points: &[ParallelPoint]) -> Result<(f64, f64), String> {
    let mut max_norm_error = 0.0_f64;
    let mut max_orthogonality_error = 0.0_f64;
    for point in points {
        let position = point_position(point);
        let frame = point_frame(point);
        if !position.is_finite()
            || !frame.iter().all(|vector| vector.is_finite())
            || !point.kappa.is_finite()
            || !point.tau.is_finite()
        {
            return Err(format!(
                "reconstructed point {} contains a non-finite value",
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

fn max_point_component_error(
    left: &[ParallelPoint],
    right: &[ParallelPoint],
) -> Result<f64, String> {
    if left.len() != right.len() {
        return Err("reconstructed and reference paths have different lengths".into());
    }
    let mut maximum = 0.0_f64;
    for (actual, expected) in left.iter().zip(right) {
        if actual.index != expected.index {
            return Err("reconstructed and reference point indices differ".into());
        }
        let actual_values = [
            actual.p,
            actual.s,
            actual.x,
            actual.y,
            actual.z,
            actual.kappa,
            actual.tau,
            actual.tx,
            actual.ty,
            actual.tz,
            actual.nx,
            actual.ny,
            actual.nz,
            actual.bx,
            actual.by,
            actual.bz,
        ];
        let expected_values = [
            expected.p,
            expected.s,
            expected.x,
            expected.y,
            expected.z,
            expected.kappa,
            expected.tau,
            expected.tx,
            expected.ty,
            expected.tz,
            expected.nx,
            expected.ny,
            expected.nz,
            expected.bx,
            expected.by,
            expected.bz,
        ];
        for (actual_value, expected_value) in actual_values.into_iter().zip(expected_values) {
            maximum = maximum.max((actual_value - expected_value).abs());
        }
    }
    Ok(maximum)
}

pub fn build_shard_prefix_path(
    config: ModelConfig,
    interval_width: usize,
) -> Result<ShardPrefixReconstruction, String> {
    let config = validate_config(config)?;
    let shards = build_shard_work_units(config, interval_width)?;
    let manifest_fingerprint = fingerprint_manifest(&shards);
    let (prefixes, shard_prefix_passes, max_local_tail_vs_reduction_component_error) =
        reconstruct_shard_prefixes(&shards, config.samples - 1)?;
    let points = points_from_prefixes(&prefixes, config)?;
    let (reference_points, reference_report) = build_parallel_path(config)?;
    if !reference_report.pass_all {
        return Err("source parallel reference did not pass its own contract".into());
    }
    let max_reconstruction_vs_parallel_component_error =
        max_point_component_error(&points, &reference_points)?;
    let (max_frame_norm_error, max_frame_orthogonality_error) = frame_errors(&points)?;

    let centre = &points[points.len() / 2];
    let mut path_length = 0.0_f64;
    for pair in points.windows(2) {
        path_length += point_position(&pair[1])
            .minus(point_position(&pair[0]))
            .norm();
    }

    let pass_finite = points.iter().all(|point| {
        point_position(point).is_finite()
            && point_frame(point).iter().all(|vector| vector.is_finite())
            && point.kappa.is_finite()
            && point.tau.is_finite()
    });
    let pass_coverage = shards
        .last()
        .is_some_and(|shard| shard.end_interval_exclusive == config.samples - 1)
        && shards
            .windows(2)
            .all(|pair| pair[0].end_interval_exclusive == pair[1].start_interval);
    let pass_fingerprints = manifest_fingerprint == fingerprint_manifest(&shards)
        && shards.iter().all(|shard| {
            shard.deterministic_fingerprint
                == fingerprint_shard(
                    shard.shard_index,
                    shard.start_interval,
                    shard.end_interval_exclusive,
                    &shard.local_prefixes,
                    shard.reduction,
                )
        });
    let pass_local_prefix_integrity =
        max_local_tail_vs_reduction_component_error <= SCAN_EQUIVALENCE_TOLERANCE_F64;
    let pass_reference_equivalence =
        max_reconstruction_vs_parallel_component_error <= SCAN_EQUIVALENCE_TOLERANCE_F64;
    let centre_position = point_position(centre);
    let pass_centre = centre.p == 0.5 && centre_position.norm() <= CENTRE_TOLERANCE_F64;
    let pass_frame = max_frame_norm_error <= FRAME_TOLERANCE_F64
        && max_frame_orthogonality_error <= FRAME_TOLERANCE_F64;
    let pass_schedule_bounds = points.iter().all(|point| {
        0.0 <= point.kappa
            && point.kappa <= kappa_max() + 1.0e-12
            && TAU_MIN_EXCLUSIVE < point.tau
            && point.tau < TAU_MAX_EXCLUSIVE
    });
    let pass_all = pass_finite
        && pass_coverage
        && pass_fingerprints
        && pass_local_prefix_integrity
        && pass_reference_equivalence
        && pass_centre
        && pass_frame
        && pass_schedule_bounds;

    let bundle = ShardBundle {
        schema: SHARD_BUNDLE_SCHEMA,
        shard_prefix_contract: SHARD_PREFIX_CONTRACT,
        source_parallel_contract: PARALLEL_CONTRACT,
        interval_policy: INTERVAL_POLICY,
        local_prefix_policy: LOCAL_PREFIX_POLICY,
        shard_prefix_policy: SHARD_PREFIX_POLICY,
        assembly_policy: SHARD_ASSEMBLY_POLICY,
        fingerprint_policy: SHARD_FINGERPRINT_POLICY,
        configuration: config.into(),
        expected_intervals: config.samples - 1,
        interval_width,
        shard_count: shards.len(),
        shards,
        manifest_fingerprint: manifest_fingerprint.clone(),
        actual_multi_device_execution: false,
        distributed_execution: false,
        geometry_receipt_authority: false,
    };

    let report = ShardPrefixReport {
        schema: SHARD_PREFIX_SCHEMA,
        shard_prefix_contract: SHARD_PREFIX_CONTRACT,
        source_parallel_contract: PARALLEL_CONTRACT,
        interval_policy: INTERVAL_POLICY,
        local_prefix_policy: LOCAL_PREFIX_POLICY,
        shard_prefix_policy: SHARD_PREFIX_POLICY,
        assembly_policy: SHARD_ASSEMBLY_POLICY,
        fingerprint_policy: SHARD_FINGERPRINT_POLICY,
        implementation: "rust-f64-local-shard-reconstruction",
        implementation_version: env!("CARGO_PKG_VERSION"),
        model: MODEL_NAME,
        model_version: MODEL_VERSION,
        samples: points.len(),
        intervals: points.len() - 1,
        interval_width,
        shard_count: bundle.shard_count,
        shard_prefix_passes,
        reconstructed_prefix_count: prefixes.len(),
        s0: config.s0,
        s1: config.s1,
        kappa_fraction: config.kappa_fraction,
        tau_floor: config.tau_floor,
        tau_amplitude: config.tau_amplitude,
        centering_mode: "discrete-midpoint-to-origin",
        path_length,
        entry: point_position(&points[0]).as_array(),
        centre: centre_position.as_array(),
        exit: point_position(&points[points.len() - 1]).as_array(),
        max_frame_norm_error,
        max_frame_orthogonality_error,
        max_local_tail_vs_reduction_component_error,
        max_reconstruction_vs_parallel_component_error,
        manifest_fingerprint,
        pass_finite,
        pass_coverage,
        pass_fingerprints,
        pass_local_prefix_integrity,
        pass_reference_equivalence,
        pass_centre,
        pass_frame,
        pass_schedule_bounds,
        pass_all,
        actual_local_shard_execution: true,
        actual_multi_device_execution: false,
        distributed_execution: false,
        speedup_claim: false,
        geometry_receipt_authority: false,
        evidence_note: "This report proves deterministic local shard-prefix reconstruction and complete ordered path assembly against RSH-FRENET-PARALLEL-V1. It does not claim multi-device, networked, or distributed execution and does not replace geometry authority.",
    };

    Ok(ShardPrefixReconstruction {
        report,
        bundle,
        points,
    })
}

pub fn shard_report_json(report: &ShardPrefixReport) -> Result<String, String> {
    serde_json::to_string_pretty(report).map_err(|error| error.to_string())
}

pub fn shard_bundle_json(bundle: &ShardBundle) -> Result<String, String> {
    serde_json::to_string_pretty(bundle).map_err(|error| error.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sealed_config(samples: usize) -> ModelConfig {
        ModelConfig {
            samples,
            ..ModelConfig::default()
        }
    }

    #[test]
    fn sealed_irregular_shards_reconstruct_the_complete_path() {
        let result = build_shard_prefix_path(sealed_config(4097), 257).expect("reconstruction");
        assert_eq!(result.report.shard_count, 16);
        assert_eq!(result.report.shard_prefix_passes, 4);
        assert_eq!(result.points.len(), 4097);
        assert!(result.report.pass_all, "{:?}", result.report);
        assert!(result.report.max_reconstruction_vs_parallel_component_error <= 1.0e-11);
        assert!(!result.report.actual_multi_device_execution);
        assert!(!result.report.distributed_execution);
        assert!(!result.report.speedup_claim);
        assert!(!result.report.geometry_receipt_authority);
    }

    #[test]
    fn reconstruction_replays_deterministically() {
        let first = build_shard_prefix_path(sealed_config(1025), 128).expect("first");
        let second = build_shard_prefix_path(sealed_config(1025), 128).expect("second");
        assert_eq!(first, second);
    }

    #[test]
    fn uneven_and_single_shard_widths_pass() {
        for width in [1usize, 31, 128, 257, 4096] {
            let result = build_shard_prefix_path(sealed_config(4097), width).expect("width");
            assert!(result.report.pass_all, "width {width}: {:?}", result.report);
        }
    }

    #[test]
    fn reordered_shards_are_rejected() {
        let mut shards = build_shard_work_units(sealed_config(513), 64).expect("shards");
        shards.swap(0, 1);
        assert!(reconstruct_shard_prefixes(&shards, 512)
            .expect_err("reordered shards must fail")
            .contains("unordered"));
    }

    #[test]
    fn missing_tail_is_rejected() {
        let mut shards = build_shard_work_units(sealed_config(513), 64).expect("shards");
        shards.pop();
        assert!(reconstruct_shard_prefixes(&shards, 512)
            .expect_err("missing tail must fail")
            .contains("do not cover"));
    }

    #[test]
    fn tampered_prefix_is_rejected_by_fingerprint() {
        let mut shards = build_shard_work_units(sealed_config(513), 64).expect("shards");
        shards[0].local_prefixes[0].translation[0] += 1.0e-6;
        assert!(reconstruct_shard_prefixes(&shards, 512)
            .expect_err("tampered shard must fail")
            .contains("fingerprint mismatch"));
    }

    #[test]
    fn geometry_authority_claim_is_rejected() {
        let mut shards = build_shard_work_units(sealed_config(513), 64).expect("shards");
        shards[0].geometry_receipt_authority = true;
        assert!(reconstruct_shard_prefixes(&shards, 512)
            .expect_err("authority claim must fail")
            .contains("cannot claim geometry authority"));
    }

    #[test]
    fn zero_interval_width_is_rejected() {
        assert!(build_shard_prefix_path(sealed_config(513), 0)
            .expect_err("zero width must fail")
            .contains("must be positive"));
    }
}
