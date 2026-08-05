//! RSH parallel Frenet research surfaces.
//!
//! The accepted `RSH-FRENET-PARALLEL-V1` implementation remains in `lib.rs`.
//! This wrapper preserves that public API and adds the separately named local
//! shard-prefix reconstruction contract used before any multi-device work.

#[path = "lib.rs"]
mod parallel_v1;

pub use parallel_v1::*;

mod shard_prefix;

pub use shard_prefix::{
    build_shard_work_units, reconstruct_shard_prefixes, shard_bundle_json, shard_report_json,
    ShardBundle, ShardConfigSnapshot, ShardPrefixReconstruction, ShardPrefixReport, ShardTransform,
    ShardWorkUnit, LOCAL_PREFIX_POLICY, MAX_SHARD_COUNT, SHARD_ASSEMBLY_POLICY,
    SHARD_BUNDLE_SCHEMA, SHARD_FINGERPRINT_POLICY, SHARD_PREFIX_CONTRACT, SHARD_PREFIX_POLICY,
    SHARD_PREFIX_SCHEMA, SHARD_WORK_SCHEMA,
};

fn overflow_safe_path_length(points: &[ParallelPoint]) -> f64 {
    points.windows(2).fold(0.0_f64, |total, pair| {
        let dx = pair[1].x - pair[0].x;
        let dy = pair[1].y - pair[0].y;
        let dz = pair[1].z - pair[0].z;
        total + dx.hypot(dy).hypot(dz)
    })
}

fn finite_triplet(values: [f64; 3]) -> bool {
    values.into_iter().all(f64::is_finite)
}

/// Build the accepted local shard-prefix reconstruction and harden the emitted
/// report against non-finite derived metrics.
///
/// The implementation module retains the mathematical construction. This
/// public wrapper recomputes path length with overflow-safe `hypot` operations
/// and makes every reported scalar part of the finiteness gate before the
/// result can claim `pass_all`.
pub fn build_shard_prefix_path(
    config: rsh_core::ModelConfig,
    interval_width: usize,
) -> Result<ShardPrefixReconstruction, String> {
    let mut result = shard_prefix::build_shard_prefix_path(config, interval_width)?;
    let report = &mut result.report;

    report.path_length = overflow_safe_path_length(&result.points);
    let report_scalars_are_finite = report.path_length.is_finite()
        && report.s0.is_finite()
        && report.s1.is_finite()
        && report.kappa_fraction.is_finite()
        && report.tau_floor.is_finite()
        && report.tau_amplitude.is_finite()
        && finite_triplet(report.entry)
        && finite_triplet(report.centre)
        && finite_triplet(report.exit)
        && report.max_frame_norm_error.is_finite()
        && report.max_frame_orthogonality_error.is_finite()
        && report
            .max_local_tail_vs_reduction_component_error
            .is_finite()
        && report
            .max_reconstruction_vs_parallel_component_error
            .is_finite();

    report.pass_finite = report.pass_finite && report_scalars_are_finite;
    report.pass_all = report.pass_finite
        && report.pass_coverage
        && report.pass_fingerprints
        && report.pass_local_prefix_integrity
        && report.pass_reference_equivalence
        && report.pass_centre
        && report.pass_frame
        && report.pass_schedule_bounds;

    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn point(index: usize, x: f64, y: f64, z: f64) -> ParallelPoint {
        ParallelPoint {
            index,
            p: index as f64,
            s: index as f64,
            x,
            y,
            z,
            kappa: 0.1,
            tau: 0.2,
            tx: 1.0,
            ty: 0.0,
            tz: 0.0,
            nx: 0.0,
            ny: 1.0,
            nz: 0.0,
            bx: 0.0,
            by: 0.0,
            bz: 1.0,
        }
    }

    #[test]
    fn path_length_uses_overflow_safe_norms() {
        let points = [point(0, 0.0, 0.0, 0.0), point(1, 1.0e155, 1.0e155, 0.0)];
        let length = overflow_safe_path_length(&points);
        assert!(length.is_finite());
        assert_eq!(length, 1.0e155_f64.hypot(1.0e155));
    }

    #[test]
    fn default_shard_report_keeps_all_derived_metrics_finite() {
        let result = build_shard_prefix_path(rsh_core::ModelConfig::default(), 64)
            .expect("default shard-prefix reconstruction");
        assert!(result.report.pass_all, "{:?}", result.report);
        assert!(result.report.path_length.is_finite());
        assert!(result.report.max_frame_norm_error.is_finite());
        assert!(result.report.max_frame_orthogonality_error.is_finite());
        assert!(result
            .report
            .max_local_tail_vs_reduction_component_error
            .is_finite());
        assert!(result
            .report
            .max_reconstruction_vs_parallel_component_error
            .is_finite());
    }
}
