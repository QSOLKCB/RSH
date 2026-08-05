//! Raw WebAssembly ABI for `RSH-FRENET-PARALLEL-V1`.
//!
//! The bridge exposes the shared f64 Rust prefix-scan reference. It is a
//! correctness surface for future WGSL acceleration and does not become the
//! canonical geometry oracle or make a hardware speedup claim.

use rsh_core::{ModelConfig, MODEL_NAME, MODEL_VERSION};
use rsh_parallel::{
    build_parallel_path, ParallelPathReport, ParallelPoint, INTERVAL_POLICY,
    MAX_PARALLEL_SAMPLES, PARALLEL_CONTRACT, PARALLEL_SCHEMA, SCAN_POLICY,
};
use serde::Serialize;
use std::cell::RefCell;

pub const ABI_VERSION: u32 = 1;
pub const ERROR_SCHEMA: &str = "RSH-FRENET-PARALLEL-ERROR-V1";
pub const MAX_WASM_PARALLEL_SAMPLES: u32 = 65_537;

thread_local! {
    static OUTPUT: RefCell<Vec<u8>> = const { RefCell::new(Vec::new()) };
}

#[derive(Debug, Serialize)]
struct ParallelPayload<'a> {
    schema: &'static str,
    abi_version: u32,
    runtime: &'static str,
    implementation: &'static str,
    implementation_version: &'static str,
    parallel_contract: &'static str,
    interval_policy: &'static str,
    scan_policy: &'static str,
    model: &'static str,
    model_version: &'static str,
    report: &'a ParallelPathReport,
    points: &'a [ParallelPoint],
    actual_parallel_hardware_execution: bool,
    distributed_execution: bool,
    speedup_claim: bool,
    geometry_receipt_authority: bool,
    evidence_note: &'static str,
}

#[derive(Debug, Serialize)]
struct ParallelError<'a> {
    schema: &'static str,
    abi_version: u32,
    runtime: &'static str,
    message: &'a str,
}

fn set_output(bytes: Vec<u8>) {
    OUTPUT.with(|output| {
        *output.borrow_mut() = bytes;
    });
}

fn serialization_failure_error() -> Vec<u8> {
    format!(
        "{{\"schema\":\"{ERROR_SCHEMA}\",\"abi_version\":{ABI_VERSION},\"runtime\":\"wasm32-unknown-unknown\",\"message\":\"serialization failure\"}}"
    )
    .into_bytes()
}

fn encode_error(message: &str) -> Vec<u8> {
    serde_json::to_vec(&ParallelError {
        schema: ERROR_SCHEMA,
        abi_version: ABI_VERSION,
        runtime: "wasm32-unknown-unknown",
        message,
    })
    .unwrap_or_else(|_| serialization_failure_error())
}

fn encode_path(config: ModelConfig) -> Result<(Vec<u8>, bool), String> {
    if config.samples > MAX_WASM_PARALLEL_SAMPLES as usize {
        return Err(format!(
            "WASM parallel samples cannot exceed {MAX_WASM_PARALLEL_SAMPLES}"
        ));
    }
    if config.samples > MAX_PARALLEL_SAMPLES {
        return Err(format!(
            "parallel research samples cannot exceed {MAX_PARALLEL_SAMPLES}"
        ));
    }

    let (points, report) = build_parallel_path(config)?;
    let payload = ParallelPayload {
        schema: PARALLEL_SCHEMA,
        abi_version: ABI_VERSION,
        runtime: "wasm32-unknown-unknown",
        implementation: "rust-f64-wasm",
        implementation_version: env!("CARGO_PKG_VERSION"),
        parallel_contract: PARALLEL_CONTRACT,
        interval_policy: INTERVAL_POLICY,
        scan_policy: SCAN_POLICY,
        model: MODEL_NAME,
        model_version: MODEL_VERSION,
        report: &report,
        points: &points,
        actual_parallel_hardware_execution: false,
        distributed_execution: false,
        speedup_claim: false,
        geometry_receipt_authority: false,
        evidence_note: "This f64 WASM payload defines the parallel-prefix correctness reference. Hardware speedup requires an actual adapter benchmark sidecar.",
    };
    let bytes = serde_json::to_vec(&payload).map_err(|error| error.to_string())?;
    Ok((bytes, report.pass_all))
}

#[no_mangle]
pub extern "C" fn rsh_parallel_abi_version() -> u32 {
    ABI_VERSION
}

#[no_mangle]
pub extern "C" fn rsh_parallel_run(
    samples: u32,
    s0: f64,
    s1: f64,
    kappa_fraction: f64,
    tau_floor: f64,
    tau_amplitude: f64,
) -> i32 {
    let config = ModelConfig {
        samples: samples as usize,
        s0,
        s1,
        kappa_fraction,
        tau_floor,
        tau_amplitude,
    };
    match encode_path(config) {
        Ok((bytes, pass_all)) => {
            set_output(bytes);
            if pass_all {
                0
            } else {
                1
            }
        }
        Err(error) => {
            set_output(encode_error(&error));
            2
        }
    }
}

#[no_mangle]
pub extern "C" fn rsh_parallel_output_ptr() -> *const u8 {
    OUTPUT.with(|output| output.borrow().as_ptr())
}

#[no_mangle]
pub extern "C" fn rsh_parallel_output_len() -> usize {
    OUTPUT.with(|output| output.borrow().len())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    fn read_output() -> Value {
        let pointer = rsh_parallel_output_ptr();
        let length = rsh_parallel_output_len();
        let bytes = unsafe { std::slice::from_raw_parts(pointer, length) };
        serde_json::from_slice(bytes).expect("valid parallel ABI JSON")
    }

    #[test]
    fn payload_executes_the_shared_parallel_reference() {
        let status = rsh_parallel_run(1025, 0.0, 4.0, 0.85, 0.22, 0.13);
        assert_eq!(status, 0);
        let payload = read_output();
        assert_eq!(payload["schema"], PARALLEL_SCHEMA);
        assert_eq!(payload["abi_version"], ABI_VERSION);
        assert_eq!(payload["parallel_contract"], PARALLEL_CONTRACT);
        assert_eq!(payload["scan_policy"], SCAN_POLICY);
        assert_eq!(payload["report"]["pass_all"], true);
        assert_eq!(payload["points"].as_array().map(Vec::len), Some(1025));
        assert_eq!(payload["points"][512]["p"], 0.5);
        assert_eq!(payload["actual_parallel_hardware_execution"], false);
        assert_eq!(payload["speedup_claim"], false);
        assert_eq!(payload["geometry_receipt_authority"], false);
    }

    #[test]
    fn invalid_even_grid_returns_structured_error() {
        let status = rsh_parallel_run(1024, 0.0, 4.0, 0.85, 0.22, 0.13);
        assert_eq!(status, 2);
        let payload = read_output();
        assert_eq!(payload["schema"], ERROR_SCHEMA);
        assert_eq!(payload["abi_version"], ABI_VERSION);
        assert!(payload["message"]
            .as_str()
            .is_some_and(|message| message.contains("samples must be odd")));
    }

    #[test]
    fn serialization_fallback_preserves_the_error_shape() {
        let payload: Value = serde_json::from_slice(&serialization_failure_error())
            .expect("valid serialization fallback JSON");
        assert_eq!(payload["schema"], ERROR_SCHEMA);
        assert_eq!(payload["abi_version"], ABI_VERSION);
        assert_eq!(payload["runtime"], "wasm32-unknown-unknown");
        assert_eq!(payload["message"], "serialization failure");
    }
}
