#![no_main]

use libfuzzer_sys::fuzz_target;
use rsh_core::ModelConfig;
use rsh_numerics::build_lie_path;

fn unit(bytes: &[u8]) -> f64 {
    let mut value = [0_u8; 8];
    value.copy_from_slice(&bytes[..8]);
    let integer = u64::from_le_bytes(value) >> 11;
    integer as f64 / (1_u64 << 53) as f64
}

fuzz_target!(|data: &[u8]| {
    if data.len() < 40 {
        return;
    }

    let a = unit(&data[0..8]);
    let b = unit(&data[8..16]);
    let c = unit(&data[16..24]);
    let d = unit(&data[24..32]);
    let e = unit(&data[32..40]);
    let samples = 3 + 2 * ((u16::from_le_bytes([data[0], data[1]]) as usize) % 2048);
    let s0 = -8.0 + 16.0 * a;
    let span = 1.0e-3 + 31.999 * b;
    let tau_floor = 1.0e-6 + 0.949 * c;
    let maximum_amplitude = 0.49 * (1.0 - tau_floor);
    let config = ModelConfig {
        samples,
        s0,
        s1: s0 + span,
        kappa_fraction: 1.0e-8 + (1.0 - 1.0e-8) * d,
        tau_floor,
        tau_amplitude: maximum_amplitude * e,
    };

    let (_, report) = build_lie_path(config).expect("bounded fuzz configuration");
    assert!(report.pass_all, "{report:?}");
    assert!(!report.geometry_receipt_authority);
    assert!(!report.speedup_claim);
});
