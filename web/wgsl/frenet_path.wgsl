struct Params {
  samples: u32,
  _pad0: vec3<u32>,
  s0: f32,
  s1: f32,
  kappa_fraction: f32,
  tau_floor: f32,
  tau_amplitude: f32,
  psi: f32,
  kappa_bound: f32,
  _pad1: f32,
};

struct PathPoint {
  position_kappa: vec4<f32>,
  tangent_tau: vec4<f32>,
  normal_p: vec4<f32>,
  binormal_s: vec4<f32>,
};

struct Frame {
  tangent: vec3<f32>,
  normal: vec3<f32>,
  binormal: vec3<f32>,
};

@group(0) @binding(0) var<uniform> params: Params;
@group(0) @binding(1) var<storage, read_write> output_path: array<PathPoint>;

fn kappa_schedule(s: f32) -> f32 {
  let base = params.kappa_fraction * params.kappa_bound;
  return base * (0.92 + 0.08 * cos(0.35 * s * params.psi));
}

fn tau_schedule(s: f32) -> f32 {
  return params.tau_floor
    + params.tau_amplitude * (1.0 + sin(0.25 * s * params.psi));
}

fn safe_normalize(vector: vec3<f32>) -> vec3<f32> {
  return vector * inverseSqrt(max(dot(vector, vector), 1.0e-20));
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

fn world_from_body(frame: Frame, body: vec3<f32>) -> vec3<f32> {
  return frame.tangent * body.x
    + frame.normal * body.y
    + frame.binormal * body.z;
}

fn orthonormalize(tangent: vec3<f32>, normal: vec3<f32>) -> Frame {
  let projected_tangent = safe_normalize(tangent);
  let projected_normal = safe_normalize(
    normal - projected_tangent * dot(normal, projected_tangent)
  );
  let projected_binormal = safe_normalize(
    cross(projected_tangent, projected_normal)
  );
  return Frame(
    projected_tangent,
    projected_normal,
    projected_binormal,
  );
}

@compute @workgroup_size(1)
fn main(@builtin(global_invocation_id) global_id: vec3<u32>) {
  if (global_id.x != 0u || params.samples < 3u) {
    return;
  }

  let denominator = f32(params.samples - 1u);
  let ds = (params.s1 - params.s0) / denominator;
  let body_tangent = vec3<f32>(1.0, 0.0, 0.0);
  let body_normal = vec3<f32>(0.0, 1.0, 0.0);
  let body_binormal = vec3<f32>(0.0, 0.0, 1.0);

  var frame = Frame(body_tangent, body_normal, body_binormal);
  var position = vec3<f32>(0.0, 0.0, 0.0);
  var index = 0u;

  loop {
    let p = f32(index) / denominator;
    let s = params.s0 + f32(index) * ds;
    let kappa = kappa_schedule(s);
    let tau = tau_schedule(s);
    output_path[index] = PathPoint(
      vec4<f32>(position, kappa),
      vec4<f32>(frame.tangent, tau),
      vec4<f32>(frame.normal, p),
      vec4<f32>(frame.binormal, s),
    );

    if (index + 1u >= params.samples) {
      break;
    }

    let midpoint = s + 0.5 * ds;
    let body_omega = vec3<f32>(
      tau_schedule(midpoint),
      0.0,
      kappa_schedule(midpoint),
    );
    let midpoint_body_tangent = rotate_body(
      body_tangent,
      body_omega,
      0.5 * ds,
    );
    position += world_from_body(frame, midpoint_body_tangent) * ds;

    let next_tangent = world_from_body(
      frame,
      rotate_body(body_tangent, body_omega, ds),
    );
    let next_normal = world_from_body(
      frame,
      rotate_body(body_normal, body_omega, ds),
    );
    frame = orthonormalize(next_tangent, next_normal);
    index += 1u;
  }

  let centre = output_path[params.samples / 2u].position_kappa.xyz;
  index = 0u;
  loop {
    output_path[index].position_kappa = vec4<f32>(
      output_path[index].position_kappa.xyz - centre,
      output_path[index].position_kappa.w,
    );
    index += 1u;
    if (index >= params.samples) {
      break;
    }
  }
}
