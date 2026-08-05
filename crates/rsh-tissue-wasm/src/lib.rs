//! Raw WebAssembly ABI for the deterministic RSH tissue contract.
//!
//! This bridge calls `rsh-tissue`; it is not a second tissue implementation.
//! Receipts remain runtime evidence and never replace the canonical geometry
//! receipt or imply subjective awareness.

use rsh_tissue::{simulate_tissue, SidecarBackend, TissueConfig, TissueReport};
use serde::Serialize;
use std::cell::RefCell;

pub const ABI_VERSION: u32 = 1;
pub const PAYLOAD_SCHEMA: &str = "RSH-TISSUE-WASM-PAYLOAD-V1";
pub const ERROR_SCHEMA: &str = "RSH-TISSUE-WASM-ERROR-V1";
pub const MAX_WASM_CELLS: u32 = 512;
pub const MAX_WASM_TICKS: u32 = 10_000;
pub const MAX_WASM_WORK: u64 = 500_000;

thread_local! {
    static OUTPUT: RefCell<Vec<u8>> = const { RefCell::new(Vec::new()) };
}

#[derive(Debug, Serialize)]
struct TissuePayload<'a> {
    schema: &'static str,
    abi_version: u32,
    runtime: &'static str,
    implementation: &'static str,
    implementation_version: &'static str,
    report: &'a TissueReport,
    python_reference_authority: bool,
    geometry_receipt_authority: bool,
    subjective_awareness_claim: bool,
    autonomous_source_modification: bool,
}

#[derive(Debug, Serialize)]
struct TissueError<'a> {
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
    serde_json::to_vec(&TissueError {
        schema: ERROR_SCHEMA,
        abi_version: ABI_VERSION,
        runtime: "wasm32-unknown-unknown",
        message,
    })
    .unwrap_or_else(|_| {
        format!(
            "{{\"schema\":\"{ERROR_SCHEMA}\",\"abi_version\":{ABI_VERSION},\"runtime\":\"wasm32-unknown-unknown\",\"message\":\"serialization failure\"}}"
        )
        .into_bytes()
    })
}

fn encode_report(config: TissueConfig) -> Result<(Vec<u8>, bool), String> {
    if config.cells > MAX_WASM_CELLS as usize {
        return Err(format!("WASM cells cannot exceed {MAX_WASM_CELLS}"));
    }
    if config.ticks > MAX_WASM_TICKS as usize {
        return Err(format!("WASM ticks cannot exceed {MAX_WASM_TICKS}"));
    }
    let work = (config.cells as u64)
        .checked_mul(config.ticks as u64)
        .ok_or_else(|| "WASM tissue work overflowed".to_string())?;
    if work > MAX_WASM_WORK {
        return Err(format!("WASM cells × ticks cannot exceed {MAX_WASM_WORK}"));
    }

    let report = simulate_tissue(config)?;
    let pass_all = report.pass_all;
    let payload = TissuePayload {
        schema: PAYLOAD_SCHEMA,
        abi_version: ABI_VERSION,
        runtime: "wasm32-unknown-unknown",
        implementation: "rust-f64-wasm",
        implementation_version: env!("CARGO_PKG_VERSION"),
        report: &report,
        python_reference_authority: true,
        geometry_receipt_authority: false,
        subjective_awareness_claim: false,
        autonomous_source_modification: false,
    };
    let bytes = serde_json::to_vec(&payload).map_err(|error| error.to_string())?;
    Ok((bytes, pass_all))
}

#[no_mangle]
pub extern "C" fn rsh_tissue_abi_version() -> u32 {
    ABI_VERSION
}

#[no_mangle]
pub extern "C" fn rsh_tissue_run(
    cells: u32,
    ticks: u32,
    geometry_samples: u32,
    ds: f64,
    phase_coupling: f64,
    binding_diffusion: f64,
    sidecar_backend: u32,
    sidecar_residual: f64,
    residual_gate: f64,
    qf_floor: f64,
) -> i32 {
    let backend = match SidecarBackend::from_code(sidecar_backend) {
        Ok(backend) => backend,
        Err(error) => {
            set_output(encode_error(&error));
            return 2;
        }
    };
    let config = TissueConfig {
        cells: cells as usize,
        ticks: ticks as usize,
        geometry_samples: geometry_samples as usize,
        ds,
        phase_coupling,
        binding_diffusion,
        sidecar_backend: backend,
        sidecar_residual,
        residual_gate,
        qf_floor,
    };

    match encode_report(config) {
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
pub extern "C" fn rsh_tissue_output_ptr() -> *const u8 {
    OUTPUT.with(|output| output.borrow().as_ptr())
}

#[no_mangle]
pub extern "C" fn rsh_tissue_output_len() -> usize {
    OUTPUT.with(|output| output.borrow().len())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    fn read_output() -> Value {
        let pointer = rsh_tissue_output_ptr();
        let length = rsh_tissue_output_len();
        let bytes = unsafe { std::slice::from_raw_parts(pointer, length) };
        serde_json::from_slice(bytes).expect("valid tissue ABI JSON")
    }

    #[test]
    fn default_payload_executes_the_shared_rust_runtime() {
        let status = rsh_tissue_run(8, 20, 129, 0.05, 0.25, 0.15, 0, 0.0, 1.0e-4, 0.0);
        assert_eq!(status, 0);
        let payload = read_output();
        assert_eq!(payload["schema"], PAYLOAD_SCHEMA);
        assert_eq!(payload["abi_version"], ABI_VERSION);
        assert_eq!(payload["report"]["tissue_contract"], "1.0.0");
        assert_eq!(
            payload["report"]["ticks"].as_array().map(Vec::len),
            Some(20)
        );
        assert_eq!(payload["report"]["pass_all"], true);
        assert_eq!(payload["geometry_receipt_authority"], false);
        assert_eq!(payload["subjective_awareness_claim"], false);
    }

    #[test]
    fn invalid_backend_returns_structured_error() {
        let status = rsh_tissue_run(8, 20, 129, 0.05, 0.25, 0.15, 99, 0.0, 1.0e-4, 0.0);
        assert_eq!(status, 2);
        let payload = read_output();
        assert_eq!(payload["schema"], ERROR_SCHEMA);
        assert_eq!(payload["abi_version"], ABI_VERSION);
        assert!(payload["message"]
            .as_str()
            .is_some_and(|message| message.contains("backend code")));
    }
}
