use rsh_core::{
    ModelConfig, GOLDEN_COORDINATE_TOLERANCE, GOLDEN_ENTRY_129, GOLDEN_EXIT_129,
    GOLDEN_RECEIPT_129, MODEL_NAME, MODEL_VERSION,
};
use serde_json::Value;

const GOLDEN_RECORD: &str = include_str!("../../../conformance/python_v2_129.json");

fn vector3(value: &Value, field: &str) -> [f64; 3] {
    let values = value[field]
        .as_array()
        .unwrap_or_else(|| panic!("{field} must be a JSON array"));
    assert_eq!(values.len(), 3, "{field} must contain three coordinates");
    [
        values[0].as_f64().expect("finite x coordinate"),
        values[1].as_f64().expect("finite y coordinate"),
        values[2].as_f64().expect("finite z coordinate"),
    ]
}

#[test]
fn embedded_conformance_constants_match_checked_in_record() {
    let record: Value = serde_json::from_str(GOLDEN_RECORD).expect("valid conformance JSON");
    let configuration = &record["configuration"];
    let default = ModelConfig::default();

    assert_eq!(record["schema"], "RSH-CONFORMANCE-V1");
    assert_eq!(record["model"], MODEL_NAME);
    assert_eq!(record["model_version"], MODEL_VERSION);
    assert_eq!(configuration["samples"].as_u64(), Some(129));
    assert_eq!(configuration["s0"].as_f64(), Some(default.s0));
    assert_eq!(configuration["s1"].as_f64(), Some(default.s1));
    assert_eq!(
        configuration["kappa_fraction"].as_f64(),
        Some(default.kappa_fraction)
    );
    assert_eq!(configuration["tau_floor"].as_f64(), Some(default.tau_floor));
    assert_eq!(
        configuration["tau_amplitude"].as_f64(),
        Some(default.tau_amplitude)
    );
    assert_eq!(
        record["coordinate_tolerance"].as_f64(),
        Some(GOLDEN_COORDINATE_TOLERANCE)
    );
    assert_eq!(vector3(&record, "entry"), GOLDEN_ENTRY_129);
    assert_eq!(vector3(&record, "exit"), GOLDEN_EXIT_129);
    assert_eq!(
        record["canonical_receipt"].as_str(),
        Some(GOLDEN_RECEIPT_129)
    );
}
