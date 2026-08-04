//! Raw WebAssembly ABI for the separately versioned Frenet numerical path.
//!
//! This bridge is intentionally separate from the canonical `rsh-wasm` ABI.
//! Its output is a non-authoritative path-level reference for accelerator
//! conformance research.

use rsh_core::{ModelConfig, Sample, MODEL_NAME, MODEL_VERSION};
use rsh_numerics::{
    build_lie_path, FrenetPathReport, INTEGRATOR, MAX_PATH_SAMPLES, NUMERICAL_CONTRACT, PATH_SCHEMA,
};
use serde::Serialize;
use std::cell::RefCell;

pub const ABI_VERSION: u32 = 1;
pub const ERROR_SCHEMA: &str = "RSH-FRENET-PATH-ERROR-V1";
pub const MAX_WASM_PATH_SAMPLES: u32 = 65_537;

thread_local! {
    static OUTPUT: RefCell<Vec<u8>> = const { RefCell::new(Vec::new()) };
}

#[derive(Debug, Serialize)]
struct PathPayload<'a> {
    schema: &'static str,
    abi_version: u32,
    runtime: &'static str,
    implementation: &'static str,
    implementation_version: &'static str,
    numerical_contract: &'static str,
    integrator: &'static str,
    model: &'static str,
    model_version: &'static str,
    report: &'a FrenetPathReport,
    points: &'a [Sample],
    geometry_receipt_authority: bool,
    speedup_claim: bool,
    evidence_note: &'static str,
}

#[derive(Debug, Serialize)]
struct PathError<'a> {
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

fn encode_error(message: &str) -> Vec<u8> {
    serde_json::to_vec(&PathError {
        schema: ERROR_SCHEMA,
        abi_version: ABI_VERSION,
        runtime: "wasm32-unknown-unknown",
        message,
    })
    .unwrap_or_else(|_| {
        b"{\"schema\":\"RSH-FRENET-PATH-ERROR-V1\",\"message\":\"serialization failure\"}".to_vec()
    })
}

fn encode_path(config: ModelConfig) -> Result<(Vec<u8>, bool), String> {
    if config.samples > MAX_WASM_PATH_SAMPLES as usize {
        return Err(format!(
            "WASM path samples cannot exceed {MAX_WASM_PATH_SAMPLES}"
        ));
    }
    if config.samples > MAX_PATH_SAMPLES {
        return Err(format!(
            "numerical path samples cannot exceed {MAX_PATH_SAMPLES}"
        ));
    }

    let (rows, report) = build_lie_path(config)?;
    let payload = PathPayload {
        schema: PATH_SCHEMA,
        abi_version: ABI_VERSION,
        runtime: "wasm32-unknown-unknown",
        implementation: "rust-f64-wasm",
        implementation_version: env!("CARGO_PKG_VERSION"),
        numerical_contract: NUMERICAL_CONTRACT,
        integrator: INTEGRATOR,
        model: MODEL_NAME,
        model_version: MODEL_VERSION,
        report: &report,
        points: &rows,
        geometry_receipt_authority: false,
        speedup_claim: false,
        evidence_note: "This f64 path is supplied for full-path accelerator conformance. It does not replace the canonical geometry report or receipt.",
    };
    let bytes = serde_json::to_vec(&payload).map_err(|error| error.to_string())?;
    Ok((bytes, report.pass_all))
}

#[no_mangle]
pub extern "C" fn rsh_frenet_abi_version() -> u32 {
    ABI_VERSION
}

#[no_mangle]
pub extern "C" fn rsh_frenet_run(
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
pub extern "C" fn rsh_frenet_output_ptr() -> *const u8 {
    OUTPUT.with(|output| output.borrow().as_ptr())
}

#[no_mangle]
pub extern "C" fn rsh_frenet_output_len() -> usize {
    OUTPUT.with(|output| output.borrow().len())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    fn read_output() -> Value {
        let pointer = rsh_frenet_output_ptr();
        let length = rsh_frenet_output_len();
        let bytes = unsafe { std::slice::from_raw_parts(pointer, length) };
        serde_json::from_slice(bytes).expect("valid path ABI JSON")
    }

    #[test]
    fn path_payload_is_separate_and_non_authoritative() {
        let status = rsh_frenet_run(1025, 0.0, 4.0, 0.85, 0.22, 0.13);
        assert_eq!(status, 0);

        let payload = read_output();
        assert_eq!(payload["schema"], PATH_SCHEMA);
        assert_eq!(payload["abi_version"], ABI_VERSION);
        assert_eq!(payload["numerical_contract"], NUMERICAL_CONTRACT);
        assert_eq!(payload["integrator"], INTEGRATOR);
        assert_eq!(payload["report"]["pass_all"], true);
        assert_eq!(payload["points"].as_array().map(Vec::len), Some(1025));
        assert_eq!(payload["points"][512]["p"], 0.5);
        assert_eq!(payload["geometry_receipt_authority"], false);
        assert_eq!(payload["speedup_claim"], false);
    }

    #[test]
    fn invalid_even_grid_returns_structured_error() {
        let status = rsh_frenet_run(1024, 0.0, 4.0, 0.85, 0.22, 0.13);
        assert_eq!(status, 2);

        let payload = read_output();
        assert_eq!(payload["schema"], ERROR_SCHEMA);
        assert!(payload["message"]
            .as_str()
            .is_some_and(|message| message.contains("samples must be odd")));
    }
}
