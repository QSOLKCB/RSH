struct Params {
  samples: u32,
  offset: u32,
  _pad0: vec2<u32>,
  s0: f32,
  s1: f32,
  kappa_fraction: f32,
  tau_floor: f32,
  tau_amplitude: f32,
  psi: f32,
  kappa_bound: f32,
  _pad1: f32,
};

struct Transform {
  tangent: vec4<f32>,
  normal: vec4<f32>,
  binormal: vec4<f32>,
  translation: vec4<f32>,
};

struct PathPoint {
  position_kappa: vec4<f32>,
  tangent_tau: vec4<f32>,
  normal_p: vec4<f32>,
  binormal_s: vec4<f32>,
};

@group(0) @binding(0) var<uniform> params: Params;
@group(0) @binding(1) var<storage, read> source_transforms: array<Transform>;
@group(0) @binding(2) var<storage, read_write> target_transforms: array<Transform>;
@group(0) @binding(3) var<storage, read_write> centre_value: array<vec4<f32>>;
@group(0) @binding(4) var<storage, read_write> output_path: array<PathPoint>;

fn kappa_schedule(s: f32) -> f32 {
  let base = params.kappa_fraction * params.kappa_bound;
  return base * (0.92 + 0.08 * cos(0.35 * s * params.psi));
}

fn tau_schedule(s: f32) -> f32 {
  return params.tau_floor
    + params.tau_amplitude * (1.0 + sin(0.25 * s * params.psi));
}

fn rotate_body(vector: vec3<f32>, omega: vec3<f32>, step: f32) -> vec3<f32> {
  let magnitude = length(omega);
  if (magnitude <= 1.0e-8) {
    return vector;
  }
  let axis = omega / magnitude;
  let angle = magnitude * step;
  let cosine = cos(angle);
  let sine = sin(angle);
  return vector * cosine
    + cross(axis, vector) * sine
    + axis * dot(axis, vector) * (1.0 - cosine);
}

fn identity_transform() -> Transform {
  return Transform(
    vec4<f32>(1.0, 0.0, 0.0, 0.0),
    vec4<f32>(0.0, 1.0, 0.0, 0.0),
    vec4<f32>(0.0, 0.0, 1.0, 0.0),
    vec4<f32>(0.0, 0.0, 0.0, 0.0),
  );
}

fn apply_rotation(transform: Transform, vector: vec3<f32>) -> vec3<f32> {
  return transform.tangent.xyz * vector.x
    + transform.normal.xyz * vector.y
    + transform.binormal.xyz * vector.z;
}

fn compose(left: Transform, right: Transform) -> Transform {
  return Transform(
    vec4<f32>(apply_rotation(left, right.tangent.xyz), 0.0),
    vec4<f32>(apply_rotation(left, right.normal.xyz), 0.0),
    vec4<f32>(apply_rotation(left, right.binormal.xyz), 0.0),
    vec4<f32>(
      left.translation.xyz + apply_rotation(left, right.translation.xyz),
      0.0,
    ),
  );
}

fn local_interval(interval: u32) -> Transform {
  let denominator = f32(params.samples - 1u);
  let ds = (params.s1 - params.s0) / denominator;
  let midpoint = params.s0 + (f32(interval) + 0.5) * ds;
  let omega = vec3<f32>(
    tau_schedule(midpoint),
    0.0,
    kappa_schedule(midpoint),
  );
  return Transform(
    vec4<f32>(rotate_body(vec3<f32>(1.0, 0.0, 0.0), omega, ds), 0.0),
    vec4<f32>(rotate_body(vec3<f32>(0.0, 1.0, 0.0), omega, ds), 0.0),
    vec4<f32>(rotate_body(vec3<f32>(0.0, 0.0, 1.0), omega, ds), 0.0),
    vec4<f32>(
      rotate_body(vec3<f32>(1.0, 0.0, 0.0), omega, 0.5 * ds) * ds,
      0.0,
    ),
  );
}

@compute @workgroup_size(64)
fn build_local(@builtin(global_invocation_id) global_id: vec3<u32>) {
  let index = global_id.x;
  if (index >= params.samples) {
    return;
  }
  if (index == 0u) {
    target_transforms[index] = identity_transform();
  } else {
    target_transforms[index] = local_interval(index - 1u);
  }
}

@compute @workgroup_size(64)
fn scan_step(@builtin(global_invocation_id) global_id: vec3<u32>) {
  let index = global_id.x;
  if (index >= params.samples) {
    return;
  }
  if (index < params.offset) {
    target_transforms[index] = source_transforms[index];
  } else {
    target_transforms[index] = compose(
      source_transforms[index - params.offset],
      source_transforms[index],
    );
  }
}

@compute @workgroup_size(64)
fn capture_centre(@builtin(global_invocation_id) global_id: vec3<u32>) {
  if (global_id.x == 0u && params.samples >= 3u) {
    centre_value[0] = source_transforms[params.samples / 2u].translation;
  }
}

@compute @workgroup_size(64)
fn emit_path(@builtin(global_invocation_id) global_id: vec3<u32>) {
  let index = global_id.x;
  if (index >= params.samples) {
    return;
  }
  let denominator = f32(params.samples - 1u);
  let p = f32(index) / denominator;
  let s = params.s0 + p * (params.s1 - params.s0);
  let transform = source_transforms[index];
  output_path[index] = PathPoint(
    vec4<f32>(
      transform.translation.xyz - centre_value[0].xyz,
      kappa_schedule(s),
    ),
    vec4<f32>(transform.tangent.xyz, tau_schedule(s)),
    vec4<f32>(transform.normal.xyz, p),
    vec4<f32>(transform.binormal.xyz, s),
  );
}
