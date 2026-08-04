//! Versioned C ABI over the verified RSH Rust core.
//!
//! The ABI is an adapter, not a second geometry implementation. All geometry,
//! verification, schedule evaluation, and receipts remain inside `rsh-core`.

use rsh_core::{
    build_and_verify, kappa_max, kappa_schedule, psi, report_json, tau_schedule, ModelConfig,
    VerifyReport, TAU_MAX_EXCLUSIVE, TAU_MIN_EXCLUSIVE,
};
use std::cell::RefCell;
use std::ffi::{c_char, c_void, CString};
use std::mem::size_of;
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::ptr;

pub const RSH_FFI_ABI_VERSION: u32 = 1;
pub const RSH_FFI_STATUS_PASS: i32 = 0;
pub const RSH_FFI_STATUS_CONTRACT_FAIL: i32 = 1;
pub const RSH_FFI_STATUS_REJECTED: i32 = 2;
pub const RSH_FFI_STATUS_PANIC: i32 = 3;

thread_local! {
    static LAST_ERROR: RefCell<CString> = RefCell::new(CString::new("").expect("empty CString"));
}

#[repr(C)]
#[derive(Clone, Copy, Debug)]
pub struct RshConfigV1 {
    pub struct_size: u32,
    pub abi_version: u32,
    pub samples: u64,
    pub s0: f64,
    pub s1: f64,
    pub kappa_fraction: f64,
    pub tau_floor: f64,
    pub tau_amplitude: f64,
}

impl Default for RshConfigV1 {
    fn default() -> Self {
        Self {
            struct_size: size_of::<Self>() as u32,
            abi_version: RSH_FFI_ABI_VERSION,
            samples: 513,
            s0: 0.0,
            s1: 4.0,
            kappa_fraction: 0.85,
            tau_floor: 0.22,
            tau_amplitude: 0.13,
        }
    }
}

#[repr(C)]
#[derive(Clone, Copy, Debug)]
pub struct RshSummaryV1 {
    pub struct_size: u32,
    pub abi_version: u32,
    pub pass_all: u32,
    pub reserved: u32,
    pub samples: u64,
    pub centre_error: f64,
    pub max_kappa: f64,
    pub kappa_bound: f64,
    pub min_tau: f64,
    pub max_tau: f64,
    pub max_frame_norm_error: f64,
    pub max_frame_orthogonality_error: f64,
    pub path_length: f64,
    pub entry: [f64; 3],
    pub centre: [f64; 3],
    pub exit: [f64; 3],
    pub receipt: [u8; 65],
}

impl Default for RshSummaryV1 {
    fn default() -> Self {
        Self {
            struct_size: size_of::<Self>() as u32,
            abi_version: RSH_FFI_ABI_VERSION,
            pass_all: 0,
            reserved: 0,
            samples: 0,
            centre_error: 0.0,
            max_kappa: 0.0,
            kappa_bound: 0.0,
            min_tau: 0.0,
            max_tau: 0.0,
            max_frame_norm_error: 0.0,
            max_frame_orthogonality_error: 0.0,
            path_length: 0.0,
            entry: [0.0; 3],
            centre: [0.0; 3],
            exit: [0.0; 3],
            receipt: [0; 65],
        }
    }
}

#[repr(C)]
#[derive(Debug)]
pub struct RshOwnedBytesV1 {
    pub ptr: *const u8,
    pub len: usize,
    pub handle: *mut c_void,
}

impl Default for RshOwnedBytesV1 {
    fn default() -> Self {
        Self {
            ptr: ptr::null(),
            len: 0,
            handle: ptr::null_mut(),
        }
    }
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
pub struct RshSchedulePointV1 {
    pub p: f64,
    pub s: f64,
    pub kappa: f64,
    pub tau: f64,
}

#[repr(C)]
#[derive(Debug)]
pub struct RshOwnedScheduleV1 {
    pub ptr: *const RshSchedulePointV1,
    pub len: usize,
    pub handle: *mut c_void,
}

impl Default for RshOwnedScheduleV1 {
    fn default() -> Self {
        Self {
            ptr: ptr::null(),
            len: 0,
            handle: ptr::null_mut(),
        }
    }
}

fn set_last_error(message: impl AsRef<str>) {
    let sanitized = message.as_ref().replace('\0', "\\0");
    let value = CString::new(sanitized).unwrap_or_else(|_| CString::new("RSH FFI error").unwrap());
    LAST_ERROR.with(|slot| *slot.borrow_mut() = value);
}

fn clear_last_error() {
    LAST_ERROR.with(|slot| *slot.borrow_mut() = CString::new("").expect("empty CString"));
}

fn checked_geometry_config(input: &RshConfigV1) -> Result<ModelConfig, String> {
    if input.struct_size < size_of::<RshConfigV1>() as u32 {
        return Err("RshConfigV1.struct_size is too small for ABI v1".into());
    }
    if input.abi_version != RSH_FFI_ABI_VERSION {
        return Err(format!(
            "unsupported RSH FFI ABI {}; expected {}",
            input.abi_version, RSH_FFI_ABI_VERSION
        ));
    }
    let samples = usize::try_from(input.samples)
        .map_err(|_| "sample count does not fit this platform".to_string())?;
    ModelConfig {
        samples,
        s0: input.s0,
        s1: input.s1,
        kappa_fraction: input.kappa_fraction,
        tau_floor: input.tau_floor,
        tau_amplitude: input.tau_amplitude,
    }
    .validate()
}

fn checked_schedule_config(input: &RshConfigV1) -> Result<(usize, ModelConfig), String> {
    if input.struct_size < size_of::<RshConfigV1>() as u32 {
        return Err("RshConfigV1.struct_size is too small for ABI v1".into());
    }
    if input.abi_version != RSH_FFI_ABI_VERSION {
        return Err(format!(
            "unsupported RSH FFI ABI {}; expected {}",
            input.abi_version, RSH_FFI_ABI_VERSION
        ));
    }
    let samples = usize::try_from(input.samples)
        .map_err(|_| "sample count does not fit this platform".to_string())?;
    if samples < 2 {
        return Err("schedule samples must be at least 2".into());
    }
    if samples > 16_777_216 {
        return Err("schedule samples exceed the ABI safety limit".into());
    }
    if !input.s0.is_finite() || !input.s1.is_finite() || input.s1 <= input.s0 {
        return Err("s1 must be finite and greater than s0".into());
    }
    if !input.kappa_fraction.is_finite()
        || !(0.0 < input.kappa_fraction && input.kappa_fraction <= 1.0)
    {
        return Err("kappa_fraction must be finite and in (0, 1]".into());
    }
    if !input.tau_floor.is_finite()
        || !input.tau_amplitude.is_finite()
        || input.tau_amplitude < 0.0
    {
        return Err("torsion schedule parameters are invalid".into());
    }
    let tau_min = input.tau_floor;
    let tau_max = input.tau_floor + 2.0 * input.tau_amplitude;
    if !(TAU_MIN_EXCLUSIVE < tau_min
        && tau_min < TAU_MAX_EXCLUSIVE
        && TAU_MIN_EXCLUSIVE < tau_max
        && tau_max < TAU_MAX_EXCLUSIVE)
    {
        return Err("the torsion schedule must remain strictly inside (0, 1)".into());
    }
    Ok((
        samples,
        ModelConfig {
            samples,
            s0: input.s0,
            s1: input.s1,
            kappa_fraction: input.kappa_fraction,
            tau_floor: input.tau_floor,
            tau_amplitude: input.tau_amplitude,
        },
    ))
}

fn summary_from_report(report: &VerifyReport) -> Result<RshSummaryV1, String> {
    let receipt = report.receipt.as_bytes();
    if receipt.len() != 64 || !receipt.iter().all(u8::is_ascii_hexdigit) {
        return Err("Rust core returned an invalid receipt encoding".into());
    }
    let mut output = RshSummaryV1 {
        pass_all: u32::from(report.pass_all),
        samples: report.samples as u64,
        centre_error: report.centre_error,
        max_kappa: report.max_kappa,
        kappa_bound: report.kappa_bound,
        min_tau: report.min_tau,
        max_tau: report.max_tau,
        max_frame_norm_error: report.max_frame_norm_error,
        max_frame_orthogonality_error: report.max_frame_orthogonality_error,
        path_length: report.path_length,
        entry: report.entry,
        centre: report.centre,
        exit: report.exit,
        ..RshSummaryV1::default()
    };
    output.receipt[..64].copy_from_slice(receipt);
    Ok(output)
}

unsafe fn write_owned_bytes(output: *mut RshOwnedBytesV1, bytes: Vec<u8>) -> Result<(), String> {
    if output.is_null() {
        return Ok(());
    }
    let owner = Box::new(bytes);
    let value = RshOwnedBytesV1 {
        ptr: owner.as_ptr(),
        len: owner.len(),
        handle: Box::into_raw(owner).cast::<c_void>(),
    };
    unsafe { ptr::write(output, value) };
    Ok(())
}

unsafe fn write_owned_schedule(
    output: *mut RshOwnedScheduleV1,
    points: Vec<RshSchedulePointV1>,
) -> Result<(), String> {
    if output.is_null() {
        return Err("schedule output pointer is null".into());
    }
    let owner = Box::new(points);
    let value = RshOwnedScheduleV1 {
        ptr: owner.as_ptr(),
        len: owner.len(),
        handle: Box::into_raw(owner).cast::<c_void>(),
    };
    unsafe { ptr::write(output, value) };
    Ok(())
}

unsafe fn verify_impl(
    config: *const RshConfigV1,
    summary: *mut RshSummaryV1,
    json: *mut RshOwnedBytesV1,
) -> Result<i32, String> {
    if config.is_null() {
        return Err("configuration pointer is null".into());
    }
    if summary.is_null() {
        return Err("summary pointer is null".into());
    }
    unsafe {
        ptr::write(summary, RshSummaryV1::default());
        if !json.is_null() {
            ptr::write(json, RshOwnedBytesV1::default());
        }
    }
    let model = checked_geometry_config(unsafe { &*config })?;
    let (_, report) = build_and_verify(model)?;
    let output = summary_from_report(&report)?;
    let encoded = report_json(&report)?.into_bytes();
    unsafe {
        ptr::write(summary, output);
        write_owned_bytes(json, encoded)?;
    }
    Ok(if report.pass_all {
        RSH_FFI_STATUS_PASS
    } else {
        RSH_FFI_STATUS_CONTRACT_FAIL
    })
}

unsafe fn schedule_impl(
    config: *const RshConfigV1,
    output: *mut RshOwnedScheduleV1,
) -> Result<i32, String> {
    if config.is_null() {
        return Err("configuration pointer is null".into());
    }
    if output.is_null() {
        return Err("schedule output pointer is null".into());
    }
    unsafe { ptr::write(output, RshOwnedScheduleV1::default()) };
    let (samples, model) = checked_schedule_config(unsafe { &*config })?;
    let denominator = (samples - 1) as f64;
    let mut points = Vec::with_capacity(samples);
    for index in 0..samples {
        let p = index as f64 / denominator;
        let s = model.s0 + (model.s1 - model.s0) * p;
        let kappa = kappa_schedule(s, model);
        let tau = tau_schedule(s, model);
        if !kappa.is_finite() || !(0.0 <= kappa && kappa <= kappa_max() + 1.0e-12) {
            return Err(format!("curvature schedule violates its bound at index {index}"));
        }
        if !tau.is_finite() || !(TAU_MIN_EXCLUSIVE < tau && tau < TAU_MAX_EXCLUSIVE) {
            return Err(format!("torsion schedule leaves (0, 1) at index {index}"));
        }
        points.push(RshSchedulePointV1 { p, s, kappa, tau });
    }
    unsafe { write_owned_schedule(output, points)? };
    Ok(RSH_FFI_STATUS_PASS)
}

#[no_mangle]
pub extern "C" fn rsh_ffi_abi_version() -> u32 {
    RSH_FFI_ABI_VERSION
}

#[no_mangle]
pub extern "C" fn rsh_ffi_config_size() -> usize {
    size_of::<RshConfigV1>()
}

#[no_mangle]
pub extern "C" fn rsh_ffi_summary_size() -> usize {
    size_of::<RshSummaryV1>()
}

#[no_mangle]
pub extern "C" fn rsh_ffi_schedule_point_size() -> usize {
    size_of::<RshSchedulePointV1>()
}

#[no_mangle]
pub extern "C" fn rsh_ffi_psi() -> f64 {
    psi()
}

#[no_mangle]
pub extern "C" fn rsh_ffi_kappa_bound() -> f64 {
    kappa_max()
}

#[no_mangle]
pub extern "C" fn rsh_ffi_last_error() -> *const c_char {
    LAST_ERROR.with(|slot| slot.borrow().as_ptr())
}

/// Run the authoritative Rust geometry core and return a fixed-layout summary.
///
/// # Safety
/// `config` and `summary` must point to valid ABI-v1 structures. `json` may be
/// null. Any returned owned buffer must be released with `rsh_ffi_free_bytes`.
#[no_mangle]
pub unsafe extern "C" fn rsh_ffi_verify(
    config: *const RshConfigV1,
    summary: *mut RshSummaryV1,
    json: *mut RshOwnedBytesV1,
) -> i32 {
    clear_last_error();
    match catch_unwind(AssertUnwindSafe(|| unsafe { verify_impl(config, summary, json) })) {
        Ok(Ok(status)) => status,
        Ok(Err(error)) => {
            set_last_error(error);
            RSH_FFI_STATUS_REJECTED
        }
        Err(_) => {
            set_last_error("panic was contained at the RSH FFI boundary");
            RSH_FFI_STATUS_PANIC
        }
    }
}

/// Evaluate an f64 schedule grid through `rsh-core`.
///
/// # Safety
/// `config` and `output` must point to valid ABI-v1 structures. The returned
/// schedule must be released with `rsh_ffi_free_schedule`.
#[no_mangle]
pub unsafe extern "C" fn rsh_ffi_schedule(
    config: *const RshConfigV1,
    output: *mut RshOwnedScheduleV1,
) -> i32 {
    clear_last_error();
    match catch_unwind(AssertUnwindSafe(|| unsafe { schedule_impl(config, output) })) {
        Ok(Ok(status)) => status,
        Ok(Err(error)) => {
            set_last_error(error);
            RSH_FFI_STATUS_REJECTED
        }
        Err(_) => {
            set_last_error("panic was contained at the RSH FFI boundary");
            RSH_FFI_STATUS_PANIC
        }
    }
}

/// Release a JSON byte buffer returned by `rsh_ffi_verify`.
///
/// # Safety
/// `value` must be null or point to a buffer structure returned by this ABI.
#[no_mangle]
pub unsafe extern "C" fn rsh_ffi_free_bytes(value: *mut RshOwnedBytesV1) {
    if value.is_null() {
        return;
    }
    let current = unsafe { &mut *value };
    if !current.handle.is_null() {
        unsafe { drop(Box::from_raw(current.handle.cast::<Vec<u8>>())) };
    }
    *current = RshOwnedBytesV1::default();
}

/// Release a schedule array returned by `rsh_ffi_schedule`.
///
/// # Safety
/// `value` must be null or point to a schedule structure returned by this ABI.
#[no_mangle]
pub unsafe extern "C" fn rsh_ffi_free_schedule(value: *mut RshOwnedScheduleV1) {
    if value.is_null() {
        return;
    }
    let current = unsafe { &mut *value };
    if !current.handle.is_null() {
        unsafe {
            drop(Box::from_raw(
                current.handle.cast::<Vec<RshSchedulePointV1>>(),
            ))
        };
    }
    *current = RshOwnedScheduleV1::default();
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::ffi::CStr;

    #[test]
    fn abi_sizes_are_stable_on_64_bit_targets() {
        assert_eq!(size_of::<RshConfigV1>(), 56);
        assert_eq!(size_of::<RshSummaryV1>(), 232);
        assert_eq!(size_of::<RshSchedulePointV1>(), 32);
    }

    #[test]
    fn verify_returns_rust_core_summary_and_json() {
        let config = RshConfigV1 {
            samples: 129,
            ..RshConfigV1::default()
        };
        let mut summary = RshSummaryV1::default();
        let mut json = RshOwnedBytesV1::default();
        let status = unsafe { rsh_ffi_verify(&config, &mut summary, &mut json) };
        assert_eq!(status, RSH_FFI_STATUS_PASS);
        assert_eq!(summary.pass_all, 1);
        assert_eq!(summary.samples, 129);
        assert!(summary.centre_error <= 1.0e-12);
        assert_eq!(json.len > 0, true);
        let bytes = unsafe { std::slice::from_raw_parts(json.ptr, json.len) };
        let text = std::str::from_utf8(bytes).expect("UTF-8 report");
        assert!(text.contains("Robitaille-Slade-Helix"));
        unsafe { rsh_ffi_free_bytes(&mut json) };
        assert!(json.ptr.is_null());
    }

    #[test]
    fn schedule_accepts_even_cuda_grid() {
        let config = RshConfigV1 {
            samples: 4096,
            ..RshConfigV1::default()
        };
        let mut schedule = RshOwnedScheduleV1::default();
        let status = unsafe { rsh_ffi_schedule(&config, &mut schedule) };
        assert_eq!(status, RSH_FFI_STATUS_PASS);
        assert_eq!(schedule.len, 4096);
        let points = unsafe { std::slice::from_raw_parts(schedule.ptr, schedule.len) };
        assert_eq!(points[0].p, 0.0);
        assert_eq!(points[points.len() - 1].p, 1.0);
        assert!(points
            .iter()
            .all(|point| point.kappa <= kappa_max() + 1.0e-12));
        unsafe { rsh_ffi_free_schedule(&mut schedule) };
    }

    #[test]
    fn invalid_configuration_returns_error_without_unwinding() {
        let config = RshConfigV1 {
            samples: 128,
            ..RshConfigV1::default()
        };
        let mut summary = RshSummaryV1::default();
        let status = unsafe { rsh_ffi_verify(&config, &mut summary, ptr::null_mut()) };
        assert_eq!(status, RSH_FFI_STATUS_REJECTED);
        let message = unsafe { CStr::from_ptr(rsh_ffi_last_error()) }
            .to_str()
            .expect("error UTF-8");
        assert!(message.contains("odd"));
    }
}
