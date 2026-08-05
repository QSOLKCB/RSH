use rsh_core::ModelConfig;
use rsh_parallel::{
    merge_segment_summaries, segment_summaries, SegmentSummary, TransformSnapshot,
    SCAN_EQUIVALENCE_TOLERANCE_F64,
};

fn identity_snapshot() -> TransformSnapshot {
    TransformSnapshot {
        tangent: [1.0, 0.0, 0.0],
        normal: [0.0, 1.0, 0.0],
        binormal: [0.0, 0.0, 1.0],
        translation: [0.0, 0.0, 0.0],
    }
}

fn maximum_component_error(left: TransformSnapshot, right: TransformSnapshot) -> f64 {
    left.tangent
        .into_iter()
        .chain(left.normal)
        .chain(left.binormal)
        .chain(left.translation)
        .zip(
            right
                .tangent
                .into_iter()
                .chain(right.normal)
                .chain(right.binormal)
                .chain(right.translation),
        )
        .map(|(left, right)| (left - right).abs())
        .fold(0.0_f64, f64::max)
}

#[test]
fn empty_shard_list_is_rejected() {
    let error = merge_segment_summaries(&[], 8).expect_err("empty summaries must fail");
    assert!(error.contains("do not cover the expected interval range"));
}

#[test]
fn overlapping_shards_are_rejected() {
    let config = ModelConfig::default();
    let mut summaries = segment_summaries(config, 32).expect("segment summaries");
    summaries[1].start_interval -= 1;
    summaries[1].end_interval_exclusive -= 1;

    let error = merge_segment_summaries(&summaries, config.samples - 1)
        .expect_err("overlapping summaries must fail");
    assert!(error.contains("missing, overlapping, or unordered"));
}

#[test]
fn overflowing_shard_range_is_rejected() {
    let summary = SegmentSummary {
        schema: "RSH-FRENET-PARALLEL-SEGMENT-V1",
        start_interval: usize::MAX,
        end_interval_exclusive: usize::MAX,
        interval_count: 1,
        transform: identity_snapshot(),
        geometry_receipt_authority: false,
    };

    let error =
        merge_segment_summaries(&[summary], 1).expect_err("overflowing interval range must fail");
    assert!(error.contains("interval range overflow"));
}

#[test]
fn zero_expected_interval_count_is_rejected() {
    let error =
        merge_segment_summaries(&[], 0).expect_err("zero expected interval count must fail");
    assert!(error.contains("must be positive"));
}

#[test]
fn mutated_final_reduction_exceeds_the_conformance_gate() {
    let config = ModelConfig::default();
    let summaries = segment_summaries(config, 32).expect("segment summaries");
    let expected =
        merge_segment_summaries(&summaries, config.samples - 1).expect("complete reduction");

    let mut altered = summaries.clone();
    altered
        .last_mut()
        .expect("final summary")
        .transform
        .translation[0] += 1.0e-3;
    let observed = merge_segment_summaries(&altered, config.samples - 1)
        .expect("coverage remains structurally valid");

    assert!(maximum_component_error(observed, expected) > SCAN_EQUIVALENCE_TOLERANCE_F64);
}
