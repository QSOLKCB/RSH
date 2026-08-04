#include "rsh_ffi.h"

#include <cuda_runtime.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr std::uint32_t kSamples = 4096;
constexpr std::uint32_t kBlockSize = 128;
constexpr double kResidualThreshold = 1.0e-4;

struct DeviceScheduleParameters {
  std::uint32_t samples;
  float s0;
  float s1;
  float kappa_fraction;
  float tau_floor;
  float tau_amplitude;
  float psi;
  float kappa_bound;
};

__global__ void evaluate_schedule(DeviceScheduleParameters parameters, float2* output) {
  const std::uint32_t index = blockIdx.x * blockDim.x + threadIdx.x;
  if (index >= parameters.samples) {
    return;
  }
  const float denominator = static_cast<float>(parameters.samples - 1U);
  const float p = static_cast<float>(index) / denominator;
  const float s = parameters.s0 + (parameters.s1 - parameters.s0) * p;
  const float base = parameters.kappa_fraction * parameters.kappa_bound;
  const float kappa = base * (0.92F + 0.08F * cosf(0.35F * s * parameters.psi));
  const float tau = parameters.tau_floor + parameters.tau_amplitude *
      (1.0F + sinf(0.25F * s * parameters.psi));
  output[index] = make_float2(kappa, tau);
}

void check_cuda(cudaError_t status, const char* operation) {
  if (status != cudaSuccess) {
    throw std::runtime_error(std::string(operation) + ": " + cudaGetErrorString(status));
  }
}

struct ScheduleOwner {
  RshOwnedScheduleV1 value{};
  ~ScheduleOwner() { rsh_ffi_free_schedule(&value); }
};

struct DeviceBuffer {
  float2* value = nullptr;
  ~DeviceBuffer() {
    if (value != nullptr) {
      cudaFree(value);
    }
  }
};

std::string ffi_error() {
  const char* value = rsh_ffi_last_error();
  return value == nullptr || *value == '\0' ? "unknown RSH FFI error" : value;
}

}  // namespace

int main() {
  try {
    if (rsh_ffi_abi_version() != RSH_FFI_ABI_VERSION) {
      throw std::runtime_error("RSH FFI ABI version mismatch");
    }

    const RshConfigV1 config{
        static_cast<std::uint32_t>(sizeof(RshConfigV1)),
        RSH_FFI_ABI_VERSION,
        kSamples,
        0.0,
        4.0,
        0.85,
        0.22,
        0.13,
    };
    ScheduleOwner oracle;
    const std::int32_t status = rsh_ffi_schedule(&config, &oracle.value);
    if (status != RSH_FFI_STATUS_PASS) {
      throw std::runtime_error(ffi_error());
    }
    if (oracle.value.ptr == nullptr || oracle.value.len != kSamples) {
      throw std::runtime_error("RSH FFI returned an invalid schedule oracle");
    }

    int device_index = 0;
    check_cuda(cudaGetDevice(&device_index), "cudaGetDevice");
    cudaDeviceProp properties{};
    check_cuda(cudaGetDeviceProperties(&properties, device_index), "cudaGetDeviceProperties");

    const DeviceScheduleParameters parameters{
        kSamples,
        static_cast<float>(config.s0),
        static_cast<float>(config.s1),
        static_cast<float>(config.kappa_fraction),
        static_cast<float>(config.tau_floor),
        static_cast<float>(config.tau_amplitude),
        static_cast<float>(rsh_ffi_psi()),
        static_cast<float>(rsh_ffi_kappa_bound()),
    };

    DeviceBuffer device_output;
    check_cuda(
        cudaMalloc(reinterpret_cast<void**>(&device_output.value), kSamples * sizeof(float2)),
        "cudaMalloc");
    const std::uint32_t blocks = (kSamples + kBlockSize - 1U) / kBlockSize;
    evaluate_schedule<<<blocks, kBlockSize>>>(parameters, device_output.value);
    check_cuda(cudaGetLastError(), "evaluate_schedule launch");
    check_cuda(cudaDeviceSynchronize(), "evaluate_schedule synchronize");

    std::vector<float2> gpu(kSamples);
    check_cuda(
        cudaMemcpy(
            gpu.data(),
            device_output.value,
            kSamples * sizeof(float2),
            cudaMemcpyDeviceToHost),
        "cudaMemcpy device to host");

    double max_kappa = 0.0;
    double max_tau = 0.0;
    for (std::size_t index = 0; index < gpu.size(); ++index) {
      max_kappa = std::max(
          max_kappa,
          std::abs(static_cast<double>(gpu[index].x) - oracle.value.ptr[index].kappa));
      max_tau = std::max(
          max_tau,
          std::abs(static_cast<double>(gpu[index].y) - oracle.value.ptr[index].tau));
    }
    const double maximum = std::max(max_kappa, max_tau);
    const bool pass = maximum <= kResidualThreshold;

    std::cout << "{\n"
              << "  \"schema\": \"RSH-CUDA-RESIDUAL-SIDECAR-V1\",\n"
              << "  \"status\": \"" << (pass ? "PASS" : "FAIL") << "\",\n"
              << "  \"actual_cuda_execution\": true,\n"
              << "  \"device\": \"" << properties.name << "\",\n"
              << "  \"compute_capability\": \"" << properties.major << '.'
              << properties.minor << "\",\n"
              << "  \"samples\": " << kSamples << ",\n"
              << "  \"block_size\": " << kBlockSize << ",\n"
              << std::scientific << std::setprecision(17)
              << "  \"max_abs_kappa_vs_rust_f64\": " << max_kappa << ",\n"
              << "  \"max_abs_tau_vs_rust_f64\": " << max_tau << ",\n"
              << "  \"maximum_residual\": " << maximum << ",\n"
              << "  \"threshold\": " << kResidualThreshold << ",\n"
              << "  \"geometry_receipt_authority\": false\n"
              << "}\n";
    return pass ? EXIT_SUCCESS : EXIT_FAILURE;
  } catch (const std::exception& error) {
    std::cerr << "rsh-cuda: " << error.what() << '\n';
    return EXIT_FAILURE;
  }
}
