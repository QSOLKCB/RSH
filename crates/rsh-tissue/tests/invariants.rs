use rsh_core::kappa_max;
use rsh_tissue::{simulate_tissue, SidecarBackend, TissueConfig, OBSERVABLE_TOLERANCE};
use std::f64::consts::TAU;

fn short_report() -> rsh_tissue::TissueReport {
    simulate_tissue(TissueConfig {
        ticks: 3,
        ..TissueConfig::default()
    })
    .expect("short tissue report")
}

#[test]
fn bound_projection_keeps_every_final_cell_admissible() {
    let report = short_report();
    assert!(report.pass_bounds);
    assert!(report
        .final_cells
        .iter()
        .all(|cell| 0.0 <= cell.kappa && cell.kappa <= kappa_max()));
    assert!(report
        .final_cells
        .iter()
        .all(|cell| 0.0 < cell.tau && cell.tau < 1.0));
}

#[test]
fn phase_updates_remain_wrapped_to_one_turn() {
    let report = short_report();
    assert!(report
        .final_cells
        .iter()
        .all(|cell| 0.0 <= cell.phase && cell.phase < TAU));
}

#[test]
fn shared_centroid_is_normalized_to_the_origin() {
    let report = short_report();
    let count = report.final_cells.len() as f64;
    let centre = report
        .final_cells
        .iter()
        .fold([0.0_f64; 3], |mut sum, cell| {
            sum[0] += cell.x;
            sum[1] += cell.y;
            sum[2] += cell.z;
            sum
        });
    let error = (centre[0] / count)
        .hypot(centre[1] / count)
        .hypot(centre[2] / count);
    assert!(error <= OBSERVABLE_TOLERANCE, "centroid error {error}");
    assert!(report.pass_centre);
}

#[test]
fn functional_cohesion_factors_are_clamped_to_unit_interval() {
    let report = short_report();
    for tick in report.ticks {
        let metrics = tick.metrics;
        for (name, value) in [
            ("phase_coherence", metrics.phase_coherence),
            ("binding_cohesion", metrics.binding_cohesion),
            ("predictive_stability", metrics.predictive_stability),
            ("edge_continuity", metrics.edge_continuity),
            ("role_coverage", metrics.role_coverage),
            ("dissociation", metrics.dissociation),
            ("q_f", metrics.q_f),
        ] {
            assert!(
                (0.0..=1.0).contains(&value),
                "{name} escaped [0, 1]: {value}"
            );
        }
    }
}

#[test]
fn rejected_sidecar_pressure_cannot_push_qf_out_of_range() {
    let report = simulate_tissue(TissueConfig {
        ticks: 1,
        sidecar_backend: SidecarBackend::Npu,
        sidecar_residual: 1.0,
        residual_gate: 1.0e-12,
        ..TissueConfig::default()
    })
    .expect("bounded sidecar-pressure report");

    assert!(report.fallback_used);
    assert!(!report.sidecar_accepted);
    assert!((0.0..=1.0).contains(&report.final_q_f));
    assert!((0.0..=1.0).contains(&report.ticks[0].metrics.dissociation));
}
