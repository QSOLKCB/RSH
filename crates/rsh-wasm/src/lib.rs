//! WebAssembly bridge for the verified RSH Rust core.
//!
//! The bridge deliberately exposes a tiny numeric ABI rather than maintaining a
//! second JavaScript implementation of the model. JavaScript supplies validated
//! scalar inputs, reads UTF-8 JSON from linear memory, and handles only interface,
//! projection, animation, WebGPU residual checks, and file export.

use rsh_core::{
    build_and_verify, kappa_max, kappa_schedule, psi, tau_schedule, ModelConfig, Sample,
    VerifyReport, IMPLEMENTATION, MODEL_NAME, MODEL_VERSION, TAU_MAX_EXCLUSIVE,
    TAU_MIN_EXCLUSIVE,
};
use serde::Serialize;
use std::cell::RefCell;

pub const ABI_VERSION: u32 = 1;
pub const BROWSER_SCHEMA: &str = "RSH-BROWSER-RUN-V1";
pub const SCHEDULE_SCHEMA: &str = "RSH-SCHEDULE-RUN-V1";
pub const ERROR_SCHEMA: &str = "RSH-BROWSER-ERROR-V1";
pub const MAX_SCHEDULE_SAMPLES: u32 = 1_048_576;

thread_local! {
    static OUTPUT: RefCell<Vec<u8>> = const { RefCell::new(Vec::new()) };
}

#[derive(Clone, Copy, Debug, Serialize)]
struct BrowserPoint {
    p: f64,
    x: f64,
    y: f64,
    z: f64,
    kappa: f64,
    tau: f64,
}

impl From<&Sample> for BrowserPoint {
    fn from(sample: &Sample) -> Self {
        Self {
            p: sample.p,
            x: sample.x,
            y: sample.y,
            z: sample.z,
            kappa: sample.kappa,
            tau: sample.tau,
        }
    }
}

#[derive(Clone, Copy, Debug, Serialize)]
struct SchedulePoint {
    index: u32,
    p: f64,
    s: f64,
    kappa: f64,
    tau: f64,
}

#[derive(Debug, Serialize)]
struct BrowserPayload<'a> {
    schema: &'static str,
    abi_version: u32,
    implementation: &'static str,
    runtime: &'static str,
    implementation_version: &'static str,
    model: &'static str,
    model_version: &'static str,
    evidence_note: &'static str,
    report: &'a VerifyReport,
    points: Vec<BrowserPoint>,
}

#[derive(Debug, Serialize)]
struct SchedulePayload {
    schema: &'static str,
    abi_version: u32,
    implementation: &'static str,
    runtime: &'static str,
    implementation_version: &'static str,
    model: &'static str,
    model_version: &'static str,
    evidence_note: &'static str,
    samples: u32,
    s0: f64,
    s1: f64,
    kappa_fraction: f64,
    tau_floor: f64,
    tau_amplitude: f64,
    psi: f64,
    kappa_bound: f64,
    points: Vec<SchedulePoint>,
}

#[derive(Debug, Serialize)]
struct BrowserError<'a> {
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

fn encode_run(config: ModelConfig) -> Result<(Vec<u8>, bool), String> {
    let (rows, report) = build_and_verify(config)?;
    let payload = BrowserPayload {
        schema: BROWSER_SCHEMA,
        abi_version: ABI_VERSION,
        implementation: IMPLEMENTATION,
        runtime: "wasm32-unknown-unknown",
        implementation_version: env!("CARGO_PKG_VERSION"),
        model: MODEL_NAME,
        model_version: MODEL_VERSION,
        evidence_note: "The report is produced by rsh-core. Canvas projection is interface output, not additional evidence.",
        report: &report,
        points: rows.iter().map(BrowserPoint::from).collect(),
    };
    let bytes = serde_json::to_vec(&payload).map_err(|error| error.to_string())?;
    Ok((bytes, report.pass_all))
}

fn schedule_config(
    samples: u32,
    s0: f64,
    s1: f64,
    kappa_fraction: f64,
    tau_floor: f64,
    tau_amplitude: f64,
) -> Result<ModelConfig, String> {
    if samples < 2 {
        return Err("schedule samples must be at least 2".into());
    }
    if samples > MAX_SCHEDULE_SAMPLES {
        return Err(format!(
            "schedule samples cannot exceed {MAX_SCHEDULE_SAMPLES}"
        ));
    }

    ModelConfig {
        samples: 3,
        s0,
        s1,
        kappa_fraction,
        tau_floor,
        tau_amplitude,
    }
    .validate()
}

fn encode_schedule(
    samples: u32,
    s0: f64,
    s1: f64,
    kappa_fraction: f64,
    tau_floor: f64,
    tau_amplitude: f64,
) -> Result<Vec<u8>, String> {
    let config = schedule_config(
        samples,
        s0,
        s1,
        kappa_fraction,
        tau_floor,
        tau_amplitude,
    )?;
    let denominator = f64::from(samples - 1);
    let mut points = Vec::with_capacity(samples as usize);

    for index in 0..samples {
        let p = f64::from(index) / denominator;
        let s = config.s0 + p * (config.s1 - config.s0);
        let kappa = kappa_schedule(s, config);
        let tau = tau_schedule(s, config);
        if !kappa.is_finite() || !(0.0 <= kappa && kappa <= kappa_max() + 1.0e-12) {
            return Err(format!("curvature schedule violates its bound at index {index}"));
        }
        if !tau.is_finite() || !(TAU_MIN_EXCLUSIVE < tau && tau < TAU_MAX_EXCLUSIVE) {
            return Err(format!("torsion schedule leaves (0, 1) at index {index}"));
        }
        points.push(SchedulePoint {
            index,
            p,
            s,
            kappa,
            tau,
        });
    }

    let payload = SchedulePayload {
        schema: SCHEDULE_SCHEMA,
        abi_version: ABI_VERSION,
        implementation: IMPLEMENTATION,
        runtime: "wasm32-unknown-unknown",
        implementation_version: env!("CARGO_PKG_VERSION"),
        model: MODEL_NAME,
        model_version: MODEL_VERSION,
        evidence_note: "This f64 schedule is supplied by rsh-core for WGSL residual comparison. It is not a second JavaScript model.",
        samples,
        s0: config.s0,
        s1: config.s1,
        kappa_fraction: config.kappa_fraction,
        tau_floor: config.tau_floor,
        tau_amplitude: config.tau_amplitude,
        psi: psi(),
        kappa_bound: kappa_max(),
        points,
    };
    serde_json::to_vec(&payload).map_err(|error| error.to_string())
}

fn encode_error(message: &str) -> Vec<u8> {
    serde_json::to_vec(&BrowserError {
        schema: ERROR_SCHEMA,
        abi_version: ABI_VERSION,
        runtime: "wasm32-unknown-unknown",
        message,
    })
    .unwrap_or_else(|_| {
        b"{\"schema\":\"RSH-BROWSER-ERROR-V1\",\"message\":\"serialization failure\"}".to_vec()
    })
}

/// Return the raw ABI version expected by the browser loader.
#[no_mangle]
pub extern "C" fn rsh_abi_version() -> u32 {
    ABI_VERSION
}

/// Run the verified Rust geometry core and store a UTF-8 JSON result.
///
/// Return codes:
/// - `0`: all verification contracts passed;
/// - `1`: a report was produced but at least one contract failed;
/// - `2`: configuration, integration, or serialization error.
#[no_mangle]
pub extern "C" fn rsh_run(
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

    match encode_run(config) {
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

/// Evaluate the core curvature/torsion schedules on any one-dimensional grid.
///
/// This additive ABI exists so WebGPU output can be compared with a CPU/WASM f64
/// oracle without copying schedule equations into JavaScript. Return `0` on
/// success and `2` when the configuration or serialization is rejected.
#[no_mangle]
pub extern "C" fn rsh_schedule(
    samples: u32,
    s0: f64,
    s1: f64,
    kappa_fraction: f64,
    tau_floor: f64,
    tau_amplitude: f64,
) -> i32 {
    match encode_schedule(
        samples,
        s0,
        s1,
        kappa_fraction,
        tau_floor,
        tau_amplitude,
    ) {
        Ok(bytes) => {
            set_output(bytes);
            0
        }
        Err(error) => {
            set_output(encode_error(&error));
            2
        }
    }
}

/// Pointer to the current UTF-8 output buffer in WebAssembly linear memory.
#[no_mangle]
pub extern "C" fn rsh_output_ptr() -> *const u8 {
    OUTPUT.with(|output| output.borrow().as_ptr())
}

/// Length of the current UTF-8 output buffer.
#[no_mangle]
pub extern "C" fn rsh_output_len() -> usize {
    OUTPUT.with(|output| output.borrow().len())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    fn read_output() -> Value {
        let pointer = rsh_output_ptr();
        let length = rsh_output_len();
        let bytes = unsafe { std::slice::from_raw_parts(pointer, length) };
        serde_json::from_slice(bytes).expect("valid ABI JSON")
    }

    #[test]
    fn browser_payload_is_supplied_by_rsh_core() {
        let status = rsh_run(129, 0.0, 4.0, 0.85, 0.22, 0.13);
        assert_eq!(status, 0);

        let payload = read_output();
        assert_eq!(payload["schema"], BROWSER_SCHEMA);
        assert_eq!(payload["abi_version"], ABI_VERSION);
        assert_eq!(payload["implementation"], IMPLEMENTATION);
        assert_eq!(payload["model"], MODEL_NAME);
        assert_eq!(payload["model_version"], MODEL_VERSION);
        assert_eq!(payload["report"]["pass_all"], true);
        assert_eq!(payload["points"].as_array().map(Vec::len), Some(129));
        assert_eq!(payload["points"][64]["p"], 0.5);
    }

    #[test]
    fn schedule_payload_supports_even_gpu_grids() {
        let status = rsh_schedule(4096, 0.0, 4.0, 0.85, 0.22, 0.13);
        assert_eq!(status, 0);

        let payload = read_output();
        assert_eq!(payload["schema"], SCHEDULE_SCHEMA);
        assert_eq!(payload["samples"], 4096);
        assert_eq!(payload["points"].as_array().map(Vec::len), Some(4096));
        assert_eq!(payload["points"][0]["p"], 0.0);
        assert_eq!(payload["points"][4095]["p"], 1.0);
        let points = payload["points"].as_array().expect("schedule points");
        for point in points {
            assert!(point["kappa"].as_f64().is_some_and(f64::is_finite));
            assert!(point["tau"].as_f64().is_some_and(f64::is_finite));
        }
    }

    #[test]
    fn invalid_browser_configuration_returns_structured_error() {
        let status = rsh_run(128, 0.0, 4.0, 0.85, 0.22, 0.13);
        assert_eq!(status, 2);

        let payload = read_output();
        assert_eq!(payload["schema"], ERROR_SCHEMA);
        assert!(payload["message"]
            .as_str()
            .is_some_and(|message| message.contains("samples must be odd")));
    }

    #[test]
    fn invalid_schedule_count_returns_structured_error() {
        let status = rsh_schedule(1, 0.0, 4.0, 0.85, 0.22, 0.13);
        assert_eq!(status, 2);

        let payload = read_output();
        assert_eq!(payload["schema"], ERROR_SCHEMA);
        assert!(payload["message"]
            .as_str()
            .is_some_and(|message| message.contains("at least 2")));
    }
}
