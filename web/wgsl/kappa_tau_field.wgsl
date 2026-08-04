// RSH Phase 4 — evaluate κ(s), τ(s) on a one-dimensional f32 grid.
// The f64 CPU/WASM schedule remains authoritative. This kernel may contribute
// only a residual sidecar after comparison with the shared oracle grid.

struct Params {
  n: u32,
  _pad0: u32,
  _pad1: u32,
  _pad2: u32,
  s0: f32,
  s1: f32,
  kappa_fraction: f32,
  tau_floor: f32,
  tau_amplitude: f32,
  psi: f32,
  kappa_max: f32,
  _pad3: f32,
};

@group(0) @binding(0) var<uniform> params: Params;
@group(0) @binding(1) var<storage, read_write> output_field: array<vec2<f32>>;

fn kappa_schedule(s: f32) -> f32 {
  let base = params.kappa_fraction * params.kappa_max;
  return base * (0.92 + 0.08 * cos(0.35 * s * params.psi));
}

fn tau_schedule(s: f32) -> f32 {
  return params.tau_floor
    + params.tau_amplitude * (1.0 + sin(0.25 * s * params.psi));
}

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
  let index = gid.x;
  if (index >= params.n) {
    return;
  }

  let p = f32(index) / f32(params.n - 1u);
  let s = params.s0 + p * (params.s1 - params.s0);
  output_field[index] = vec2<f32>(kappa_schedule(s), tau_schedule(s));
}
