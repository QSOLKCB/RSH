#pragma once

#include <cuda_runtime.h>

#include <cstdint>

namespace rsh_multi_cuda {

constexpr float kPsi = 2.0581710272714922503F;
constexpr float kKappaBound = 0.4142135623730950488F;

struct Parameters {
  std::uint32_t samples;
  float s0;
  float s1;
  float kappa_fraction;
  float tau_floor;
  float tau_amplitude;
};

struct Transform {
  float4 rotation;
  float4 translation;
};
static_assert(sizeof(Transform) == 32, "CUDA transform layout must remain 32 bytes");

struct PathPoint {
  float4 position_kappa;
  float4 tangent_tau;
  float4 normal_p;
  float4 binormal_s;
};
static_assert(sizeof(PathPoint) == 64, "CUDA path point layout must remain 64 bytes");

__host__ __device__ inline float3 vadd(float3 left, float3 right) {
  return make_float3(left.x + right.x, left.y + right.y, left.z + right.z);
}

__host__ __device__ inline float3 vscale(float3 value, float factor) {
  return make_float3(value.x * factor, value.y * factor, value.z * factor);
}

__host__ __device__ inline float vdot(float3 left, float3 right) {
  return left.x * right.x + left.y * right.y + left.z * right.z;
}

__host__ __device__ inline float3 vcross(float3 left, float3 right) {
  return make_float3(
      left.y * right.z - left.z * right.y,
      left.z * right.x - left.x * right.z,
      left.x * right.y - left.y * right.x);
}

__host__ __device__ inline float4 identity_quaternion() {
  return make_float4(0.0F, 0.0F, 0.0F, 1.0F);
}

__host__ __device__ inline float4 normalize_quaternion(float4 value) {
  const float magnitude_squared =
      value.x * value.x + value.y * value.y + value.z * value.z + value.w * value.w;
  if (magnitude_squared <= 1.0e-12F) {
    return identity_quaternion();
  }
  const float inverse = 1.0F / sqrtf(magnitude_squared);
  return make_float4(
      value.x * inverse, value.y * inverse, value.z * inverse, value.w * inverse);
}

__host__ __device__ inline float4 quaternion_multiply(float4 left, float4 right) {
  const float3 left_vector = make_float3(left.x, left.y, left.z);
  const float3 right_vector = make_float3(right.x, right.y, right.z);
  const float3 product_cross = vcross(left_vector, right_vector);
  return make_float4(
      left.x * right.w + right.x * left.w + product_cross.x,
      left.y * right.w + right.y * left.w + product_cross.y,
      left.z * right.w + right.z * left.w + product_cross.z,
      left.w * right.w - vdot(left_vector, right_vector));
}

__host__ __device__ inline float3 rotate_quaternion(float4 rotation, float3 vector) {
  const float3 rotation_vector = make_float3(rotation.x, rotation.y, rotation.z);
  const float3 doubled_cross = vscale(vcross(rotation_vector, vector), 2.0F);
  return vadd(
      vadd(vector, vscale(doubled_cross, rotation.w)),
      vcross(rotation_vector, doubled_cross));
}

__host__ __device__ inline float4 quaternion_from_omega(float3 omega, float step) {
  const float half_step = 0.5F * step;
  const float half_step_squared = half_step * half_step;
  const float half_angle_squared = vdot(omega, omega) * half_step_squared;
  const float half_angle_fourth = half_angle_squared * half_angle_squared;
  const float sinc =
      1.0F - half_angle_squared / 6.0F + half_angle_fourth / 120.0F;
  const float cosine =
      1.0F - half_angle_squared / 2.0F + half_angle_fourth / 24.0F;
  return normalize_quaternion(make_float4(
      omega.x * half_step * sinc,
      omega.y * half_step * sinc,
      omega.z * half_step * sinc,
      cosine));
}

__host__ __device__ inline Transform identity_transform() {
  return Transform{identity_quaternion(), make_float4(0.0F, 0.0F, 0.0F, 0.0F)};
}

__host__ __device__ inline Transform compose(Transform left, Transform right) {
  const float3 rotated = rotate_quaternion(
      left.rotation,
      make_float3(right.translation.x, right.translation.y, right.translation.z));
  return Transform{
      normalize_quaternion(quaternion_multiply(left.rotation, right.rotation)),
      make_float4(
          left.translation.x + rotated.x,
          left.translation.y + rotated.y,
          left.translation.z + rotated.z,
          0.0F)};
}

__host__ __device__ inline float kappa_schedule(float s, Parameters parameters) {
  const float base = parameters.kappa_fraction * kKappaBound;
  return base * (0.92F + 0.08F * cosf(0.35F * s * kPsi));
}

__host__ __device__ inline float tau_schedule(float s, Parameters parameters) {
  return parameters.tau_floor
      + parameters.tau_amplitude * (1.0F + sinf(0.25F * s * kPsi));
}

__host__ __device__ inline Transform local_interval(
    std::uint32_t interval_index,
    Parameters parameters) {
  const float denominator = static_cast<float>(parameters.samples - 1U);
  const float ds = (parameters.s1 - parameters.s0) / denominator;
  const float midpoint =
      parameters.s0 + (static_cast<float>(interval_index) + 0.5F) * ds;
  const float3 omega = make_float3(
      tau_schedule(midpoint, parameters),
      0.0F,
      kappa_schedule(midpoint, parameters));
  const float4 rotation = quaternion_from_omega(omega, ds);
  const float4 half_rotation = quaternion_from_omega(omega, 0.5F * ds);
  const float3 translation =
      vscale(rotate_quaternion(half_rotation, make_float3(1.0F, 0.0F, 0.0F)), ds);
  return Transform{
      rotation,
      make_float4(translation.x, translation.y, translation.z, 0.0F)};
}

__global__ inline void build_local_prefixes(
    Parameters parameters,
    std::uint32_t start_interval,
    std::uint32_t interval_count,
    Transform* prefixes,
    Transform* reduction) {
  if (blockIdx.x != 0U || threadIdx.x != 0U) {
    return;
  }
  Transform current = identity_transform();
  for (std::uint32_t local_index = 0; local_index < interval_count; ++local_index) {
    current = compose(
        current,
        local_interval(start_interval + local_index, parameters));
    prefixes[local_index] = current;
  }
  reduction[0] = current;
}

__global__ inline void emit_identity(Parameters parameters, PathPoint* output) {
  if (blockIdx.x != 0U || threadIdx.x != 0U) {
    return;
  }
  output[0] = PathPoint{
      make_float4(0.0F, 0.0F, 0.0F, kappa_schedule(parameters.s0, parameters)),
      make_float4(1.0F, 0.0F, 0.0F, tau_schedule(parameters.s0, parameters)),
      make_float4(0.0F, 1.0F, 0.0F, 0.0F),
      make_float4(0.0F, 0.0F, 1.0F, parameters.s0)};
}

__global__ inline void apply_base_and_emit(
    Parameters parameters,
    std::uint32_t start_interval,
    std::uint32_t interval_count,
    const Transform* prefixes,
    const Transform* base,
    PathPoint* output) {
  const std::uint32_t local_index = blockIdx.x * blockDim.x + threadIdx.x;
  if (local_index >= interval_count) {
    return;
  }
  const Transform global = compose(base[0], prefixes[local_index]);
  const std::uint32_t sample_index = start_interval + local_index + 1U;
  const float denominator = static_cast<float>(parameters.samples - 1U);
  const float p = static_cast<float>(sample_index) / denominator;
  const float s = parameters.s0 + p * (parameters.s1 - parameters.s0);
  const float4 rotation = normalize_quaternion(global.rotation);
  const float3 tangent =
      rotate_quaternion(rotation, make_float3(1.0F, 0.0F, 0.0F));
  const float3 normal =
      rotate_quaternion(rotation, make_float3(0.0F, 1.0F, 0.0F));
  const float3 binormal =
      rotate_quaternion(rotation, make_float3(0.0F, 0.0F, 1.0F));
  output[local_index] = PathPoint{
      make_float4(
          global.translation.x,
          global.translation.y,
          global.translation.z,
          kappa_schedule(s, parameters)),
      make_float4(tangent.x, tangent.y, tangent.z, tau_schedule(s, parameters)),
      make_float4(normal.x, normal.y, normal.z, p),
      make_float4(binormal.x, binormal.y, binormal.z, s)};
}

}  // namespace rsh_multi_cuda
