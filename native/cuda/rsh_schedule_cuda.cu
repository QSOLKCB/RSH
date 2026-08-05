#include "rsh_ffi.h"

#include <cuda_runtime.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#ifndef RSH_CUDA_ARCHITECTURES
#define RSH_CUDA_ARCHITECTURES "unspecified"
#endif

namespace {

constexpr std::uint32_t kDefaultSamples = 4096;
constexpr std::uint32_t kDefaultBlockSize = 128;
constexpr double kDefaultResidualThreshold = 1.0e-4;
constexpr double kDiagnosticObservationBand = 1.0e-6;

struct Options {
  std::uint32_t samples = kDefaultSamples;
  std::uint32_t block_size = kDefaultBlockSize;
  double threshold = kDefaultResidualThreshold;
  int device = 0;
  std::uint32_t repeat_run = 0;
};

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
  ScheduleOwner(const ScheduleOwner&) = delete;
  ScheduleOwner& operator=(const ScheduleOwner&) = delete;
  ScheduleOwner() = default;
};

struct DeviceBuffer {
  float2* value = nullptr;
  ~DeviceBuffer() {
    if (value != nullptr) {
      cudaFree(value);
    }
  }
  DeviceBuffer(const DeviceBuffer&) = delete;
  DeviceBuffer& operator=(const DeviceBuffer&) = delete;
  DeviceBuffer() = default;
};

std::string ffi_error() {
  const char* value = rsh_ffi_last_error();
  return value == nullptr || *value == '\0' ? "unknown RSH FFI error" : value;
}

std::string json_escape(std::string_view input) {
  std::ostringstream output;
  for (const unsigned char character : input) {
    switch (character) {
      case '"': output << "\\\""; break;
      case '\\': output << "\\\\"; break;
      case '\b': output << "\\b"; break;
      case '\f': output << "\\f"; break;
      case '\n': output << "\\n"; break;
      case '\r': output << "\\r"; break;
      case '\t': output << "\\t"; break;
      default:
        if (character < 0x20U) {
          output << "\\u" << std::hex << std::setw(4) << std::setfill('0')
                 << static_cast<unsigned int>(character) << std::dec;
        } else {
          output << static_cast<char>(character);
        }
    }
  }
  return output.str();
}

std::string format_cuda_version(int value) {
  if (value <= 0) {
    return "unknown";
  }
  const int major = value / 1000;
  const int minor = (value % 1000) / 10;
  const int patch = value % 10;
  std::ostringstream output;
  output << major << '.' << minor;
  if (patch != 0) {
    output << '.' << patch;
  }
  return output.str();
}

std::string format_uuid(const cudaUUID_t& uuid) {
  static constexpr char digits[] = "0123456789abcdef";
  std::string output;
  output.reserve(36);
  for (std::size_t index = 0; index < sizeof(uuid.bytes); ++index) {
    if (index == 4 || index == 6 || index == 8 || index == 10) {
      output.push_back('-');
    }
    const auto byte = static_cast<unsigned char>(uuid.bytes[index]);
    output.push_back(digits[byte >> 4U]);
    output.push_back(digits[byte & 0x0FU]);
  }
  return output;
}

std::uint64_t parse_unsigned(std::string_view text, std::string_view option) {
  std::size_t consumed = 0;
  const std::string value(text);
  const unsigned long long parsed = std::stoull(value, &consumed, 10);
  if (consumed != value.size()) {
    throw std::runtime_error(std::string(option) + " requires an unsigned integer");
  }
  return parsed;
}

double parse_positive_double(std::string_view text, std::string_view option) {
  std::size_t consumed = 0;
  const std::string value(text);
  const double parsed = std::stod(value, &consumed);
  if (consumed != value.size() || !std::isfinite(parsed) || parsed <= 0.0) {
    throw std::runtime_error(std::string(option) + " requires a finite positive value");
  }
  return parsed;
}

Options parse_options(int argc, char** argv) {
  Options options;
  for (int index = 1; index < argc; ++index) {
    const std::string_view argument(argv[index]);
    auto require_value = [&](std::string_view name) -> std::string_view {
      if (index + 1 >= argc) {
        throw std::runtime_error(std::string(name) + " requires a value");
      }
      return argv[++index];
    };

    if (argument == "--samples") {
      const auto value = parse_unsigned(require_value(argument), argument);
      if (value < 2 || value > RSH_FFI_MAX_SCHEDULE_SAMPLES ||
          value > std::numeric_limits<std::uint32_t>::max()) {
        throw std::runtime_error(
            "--samples must be between 2 and the published FFI schedule limit");
      }
      options.samples = static_cast<std::uint32_t>(value);
    } else if (argument == "--block-size") {
      const auto value = parse_unsigned(require_value(argument), argument);
      if (value < 1 || value > 1024) {
        throw std::runtime_error("--block-size must be in [1, 1024]");
      }
      options.block_size = static_cast<std::uint32_t>(value);
    } else if (argument == "--threshold") {
      options.threshold = parse_positive_double(require_value(argument), argument);
    } else if (argument == "--device") {
      const auto value = parse_unsigned(require_value(argument), argument);
      if (value > static_cast<std::uint64_t>(std::numeric_limits<int>::max())) {
        throw std::runtime_error("--device is outside the supported integer range");
      }
      options.device = static_cast<int>(value);
    } else if (argument == "--repeat-run") {
      const auto value = parse_unsigned(require_value(argument), argument);
      if (value > std::numeric_limits<std::uint32_t>::max()) {
        throw std::runtime_error("--repeat-run is outside the supported range");
      }
      options.repeat_run = static_cast<std::uint32_t>(value);
    } else if (argument == "--help" || argument == "-h") {
      std::cout
          << "RSH CUDA schedule residual adapter\n\n"
          << "Usage: rsh-cuda [options]\n\n"
          << "  --samples N       schedule grid size (default 4096)\n"
          << "  --block-size N    CUDA threads per block (default 128)\n"
          << "  --threshold X     maximum accepted residual (default 1e-4)\n"
          << "  --device N        CUDA device index (default 0)\n"
          << "  --repeat-run N    run identifier copied into the sidecar\n";
      std::exit(EXIT_SUCCESS);
    } else {
      throw std::runtime_error("unknown option: " + std::string(argument));
    }
  }
  return options;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    const Options options = parse_options(argc, argv);
    if (rsh_ffi_abi_version() != RSH_FFI_ABI_VERSION) {
      throw std::runtime_error("RSH FFI ABI version mismatch");
    }

    int device_count = 0;
    check_cuda(cudaGetDeviceCount(&device_count), "cudaGetDeviceCount");
    if (device_count <= 0) {
      throw std::runtime_error("no CUDA-capable device is available");
    }
    if (options.device < 0 || options.device >= device_count) {
      throw std::runtime_error("requested CUDA device index is unavailable");
    }
    check_cuda(cudaSetDevice(options.device), "cudaSetDevice");

    cudaDeviceProp properties{};
    check_cuda(
        cudaGetDeviceProperties(&properties, options.device),
        "cudaGetDeviceProperties");
    if (options.block_size > static_cast<std::uint32_t>(properties.maxThreadsPerBlock)) {
      throw std::runtime_error("requested block size exceeds the selected device limit");
    }

    const cudaUUID_t uuid = properties.uuid;
    int driver_api_version = 0;
    int runtime_version = 0;
    check_cuda(cudaDriverGetVersion(&driver_api_version), "cudaDriverGetVersion");
    check_cuda(cudaRuntimeGetVersion(&runtime_version), "cudaRuntimeGetVersion");

    const RshConfigV1 config{
        static_cast<std::uint32_t>(sizeof(RshConfigV1)),
        RSH_FFI_ABI_VERSION,
        options.samples,
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
    if (oracle.value.ptr == nullptr || oracle.value.len != options.samples) {
      throw std::runtime_error("RSH FFI returned an invalid schedule oracle");
    }

    const DeviceScheduleParameters parameters{
        options.samples,
        static_cast<float>(config.s0),
        static_cast<float>(config.s1),
        static_cast<float>(config.kappa_fraction),
        static_cast<float>(config.tau_floor),
        static_cast<float>(config.tau_amplitude),
        static_cast<float>(rsh_ffi_psi()),
        static_cast<float>(rsh_ffi_kappa_bound()),
    };

    const std::size_t allocation_bytes =
        static_cast<std::size_t>(options.samples) * sizeof(float2);
    DeviceBuffer device_output;
    check_cuda(
        cudaMalloc(reinterpret_cast<void**>(&device_output.value), allocation_bytes),
        "cudaMalloc");
    const std::uint32_t blocks =
        (options.samples + options.block_size - 1U) / options.block_size;
    evaluate_schedule<<<blocks, options.block_size>>>(parameters, device_output.value);
    check_cuda(cudaGetLastError(), "evaluate_schedule launch");
    check_cuda(cudaDeviceSynchronize(), "evaluate_schedule synchronize");

    std::vector<float2> gpu(options.samples);
    check_cuda(
        cudaMemcpy(
            gpu.data(),
            device_output.value,
            allocation_bytes,
            cudaMemcpyDeviceToHost),
        "cudaMemcpy device to host");

    double max_kappa = 0.0;
    double max_tau = 0.0;
    for (std::size_t index = 0; index < gpu.size(); ++index) {
      const double kappa_residual =
          std::abs(static_cast<double>(gpu[index].x) - oracle.value.ptr[index].kappa);
      const double tau_residual =
          std::abs(static_cast<double>(gpu[index].y) - oracle.value.ptr[index].tau);
      if (!std::isfinite(kappa_residual) || !std::isfinite(tau_residual)) {
        throw std::runtime_error("CUDA readback produced a non-finite residual");
      }
      max_kappa = std::max(max_kappa, kappa_residual);
      max_tau = std::max(max_tau, tau_residual);
    }
    const double maximum = std::max(max_kappa, max_tau);
    const bool pass = maximum <= options.threshold;
    const char* diagnostic_status =
        maximum <= kDiagnosticObservationBand ? "NOMINAL" : "PASS_WITH_WARNING";

    std::cout << "{\n"
              << "  \"schema\": \"RSH-CUDA-RESIDUAL-SIDECAR-V1\",\n"
              << "  \"status\": \"" << (pass ? "PASS" : "FAIL") << "\",\n"
              << "  \"diagnostic_status\": \""
              << (pass ? diagnostic_status : "OUTSIDE_GATE") << "\",\n"
              << "  \"actual_cuda_execution\": true,\n"
              << "  \"device_index\": " << options.device << ",\n"
              << "  \"device\": \"" << json_escape(properties.name) << "\",\n"
              << "  \"device_uuid\": \"" << format_uuid(uuid) << "\",\n"
              << "  \"compute_capability\": \"" << properties.major << '.'
              << properties.minor << "\",\n"
              << "  \"compiled_architectures\": \""
              << json_escape(RSH_CUDA_ARCHITECTURES) << "\",\n"
              << "  \"cuda_driver_api_version\": " << driver_api_version << ",\n"
              << "  \"cuda_driver_api\": \"" << format_cuda_version(driver_api_version)
              << "\",\n"
              << "  \"cuda_runtime_version\": " << runtime_version << ",\n"
              << "  \"cuda_runtime\": \"" << format_cuda_version(runtime_version)
              << "\",\n"
              << "  \"cuda_compile_version\": " << CUDART_VERSION << ",\n"
              << "  \"cuda_compile\": \"" << format_cuda_version(CUDART_VERSION)
              << "\",\n"
              << "  \"host_pointer_width\": " << sizeof(void*) * 8U << ",\n"
              << "  \"repeat_run\": " << options.repeat_run << ",\n"
              << "  \"samples\": " << options.samples << ",\n"
              << "  \"block_size\": " << options.block_size << ",\n"
              << "  \"grid_blocks\": " << blocks << ",\n"
              << std::scientific << std::setprecision(17)
              << "  \"max_abs_kappa_vs_rust_f64\": " << max_kappa << ",\n"
              << "  \"max_abs_tau_vs_rust_f64\": " << max_tau << ",\n"
              << "  \"maximum_residual\": " << maximum << ",\n"
              << "  \"diagnostic_observation_band\": "
              << kDiagnosticObservationBand << ",\n"
              << "  \"threshold\": " << options.threshold << ",\n"
              << "  \"geometry_receipt_authority\": false\n"
              << "}\n";
    return pass ? EXIT_SUCCESS : EXIT_FAILURE;
  } catch (const std::exception& error) {
    std::cerr << "rsh-cuda: " << error.what() << '\n';
    return EXIT_FAILURE;
  }
}
