use rsh_tissue_wasm::{
    rsh_tissue_output_len, rsh_tissue_output_ptr, rsh_tissue_run, ERROR_SCHEMA, PAYLOAD_SCHEMA,
};
use serde_json::Value;

fn read_output() -> Value {
    let pointer = rsh_tissue_output_ptr();
    let length = rsh_tissue_output_len();
    assert!(!pointer.is_null(), "WASM output pointer must be non-null");
    assert!(length > 0, "WASM output buffer must be non-empty");
    let bytes = unsafe { std::slice::from_raw_parts(pointer, length) };
    serde_json::from_slice(bytes).expect("WASM output must be valid JSON")
}

#[test]
fn status_zero_reports_a_passing_execution() {
    let status = rsh_tissue_run(8, 20, 129, 0.05, 0.25, 0.15, 0, 0.0, 1.0e-4, 0.0);
    assert_eq!(status, 0);
    let payload = read_output();
    assert_eq!(payload["schema"], PAYLOAD_SCHEMA);
    assert_eq!(payload["report"]["pass_all"], true);
}

#[test]
fn status_one_reports_an_executed_contract_failure() {
    let status = rsh_tissue_run(8, 2, 129, 0.05, 0.25, 0.15, 0, 0.0, 1.0e-4, 1.0);
    assert_eq!(status, 1);
    let payload = read_output();
    assert_eq!(payload["schema"], PAYLOAD_SCHEMA);
    assert_eq!(payload["report"]["pass_qf_floor"], false);
    assert_eq!(payload["report"]["pass_all"], false);
}

#[test]
fn status_two_reports_invalid_input_without_stale_output() {
    let passing = rsh_tissue_run(8, 1, 129, 0.05, 0.25, 0.15, 0, 0.0, 1.0e-4, 0.0);
    assert_eq!(passing, 0);
    let previous = read_output();
    assert_eq!(previous["schema"], PAYLOAD_SCHEMA);

    let rejected = rsh_tissue_run(8, 1, 129, 0.05, 0.25, 0.15, 99, 0.0, 1.0e-4, 0.0);
    assert_eq!(rejected, 2);
    let error = read_output();
    assert_eq!(error["schema"], ERROR_SCHEMA);
    assert!(error["message"]
        .as_str()
        .is_some_and(|message| message.contains("backend code")));
    assert_ne!(
        error, previous,
        "error output must replace the previous payload"
    );
}

#[test]
fn oversized_work_returns_status_two_and_a_bounded_error_payload() {
    let status = rsh_tissue_run(512, 10_000, 513, 0.05, 0.25, 0.15, 0, 0.0, 1.0e-4, 0.0);
    assert_eq!(status, 2);
    let payload = read_output();
    assert_eq!(payload["schema"], ERROR_SCHEMA);
    assert!(payload["message"]
        .as_str()
        .is_some_and(|message| message.contains("cannot exceed")));
}
