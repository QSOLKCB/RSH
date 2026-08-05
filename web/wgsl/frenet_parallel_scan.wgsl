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
  rotation: vec4<f32>,
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

fn identity_quaternion() -> vec4<f32> {
  return vec4<f32>(0.0, 0.0, 0.0, 1.0);
}

fn normalize_quaternion(value: vec4<f32>) -> vec4<f32> {
  let magnitude_squared = dot(value, value);
  if (magnitude_squared <= 1.0e-12) {
    return identity_quaternion();
  }
  return value * inverseSqrt(magnitude_squared);
}

fn quaternion_multiply(left: vec4<f32>, right: vec4<f32>) -> vec4<f32> {
  return vec4<f32>(
    left.xyz * right.w + right.xyz * left.w + cross(left.xyz, right.xyz),
    left.w * right.w - dot(left.xyz, right.xyz),
  );
}

fn rotate_quaternion(rotation: vec4<f32>, vector: vec3<f32>) -> vec3<f32> {
  let unit = normalize_quaternion(rotation);
  let doubled_cross = 2.0 * cross(unit.xyz, vector);
  return vector + unit.w * doubled_cross + cross(unit.xyz, doubled_cross);
}

fn quaternion_from_omega(omega: vec3<f32>, step: f32) -> vec4<f32> {
  let magnitude = length(omega);
  if (magnitude <= 1.0e-8) {
    return identity_quaternion();
  }
  let half_angle = 0.5 * magnitude * step;
  return normalize_quaternion(vec4<f32>(
    (omega / magnitude) * sin(half_angle),
    cos(half_angle),
  ));
}

fn identity_transform() -> Transform {
  return Transform(
    identity_quaternion(),
    vec4<f32>(0.0, 0.0, 0.0, 0.0),
  );
}

fn compose(left: Transform, right: Transform) -> Transform {
  let left_rotation = normalize_quaternion(left.rotation);
  let right_rotation = normalize_quaternion(right.rotation);
  return Transform(
    normalize_quaternion(quaternion_multiply(left_rotation, right_rotation)),
    vec4<f32>(
      left.translation.xyz
        + rotate_quaternion(left_rotation, right.translation.xyz),
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
  let rotation = quaternion_from_omega(omega, ds);
  let half_rotation = quaternion_from_omega(omega, 0.5 * ds);
  return Transform(
    rotation,
    vec4<f32>(
      rotate_quaternion(half_rotation, vec3<f32>(1.0, 0.0, 0.0)) * ds,
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
  let rotation = normalize_quaternion(transform.rotation);
  let tangent = rotate_quaternion(rotation, vec3<f32>(1.0, 0.0, 0.0));
  let normal = rotate_quaternion(rotation, vec3<f32>(0.0, 1.0, 0.0));
  let binormal = rotate_quaternion(rotation, vec3<f32>(0.0, 0.0, 1.0));
  output_path[index] = PathPoint(
    vec4<f32>(
      transform.translation.xyz - centre_value[0].xyz,
      kappa_schedule(s),
    ),
    vec4<f32>(tangent, tau_schedule(s)),
    vec4<f32>(normal, p),
    vec4<f32>(binormal, s),
  );
}
