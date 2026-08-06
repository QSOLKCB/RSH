#pragma once

#include "rsh_multi_device_kernels.cuh"

#include <cuda_runtime.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <limits>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#ifndef RSH_CUDA_ARCHITECTURES
#define RSH_CUDA_ARCHITECTURES "unspecified"
#endif

namespace rsh_multi_cuda {

constexpr const char* kSchema = "RSH-FRENET-MULTI-DEVICE-CUDA-SIDECAR-V1";
constexpr const char* kContract = "RSH-FRENET-MULTI-DEVICE-CUDA-V1";
constexpr const char* kParallelContract = "RSH-FRENET-PARALLEL-V1";
constexpr const char* kShardContract = "RSH-FRENET-SHARD-PREFIX-V1";
constexpr std::uint32_t kDefaultSamples = 4097;
constexpr std::uint32_t kDefaultIntervalWidth = 257;
constexpr std::uint32_t kDefaultBlockSize = 128;
constexpr float kDefaultFrameGate = 5.0e-5F;
constexpr float kDefaultCentreGate = 1.0e-6F;
constexpr float kDefaultTailGate = 1.0e-5F;
constexpr std::uint32_t kMaximumDevices = 8;
constexpr std::uint32_t kMaximumShards = 65536;

struct Options {
  std::uint32_t samples = kDefaultSamples;
  std::uint32_t interval_width = kDefaultIntervalWidth;
  std::uint32_t block_size = kDefaultBlockSize;
  std::vector<int> devices;
  std::uint32_t repeat_run = 0;
  float frame_gate = kDefaultFrameGate;
  float centre_gate = kDefaultCentreGate;
  float tail_gate = kDefaultTailGate;
  std::string output_csv;
};

struct Shard {
  std::uint32_t index;
  std::uint32_t start_interval;
  std::uint32_t interval_count;
  std::uint32_t device_slot;
  Transform* prefixes = nullptr;
  Transform* reduction = nullptr;
  Transform* base = nullptr;
  PathPoint* points = nullptr;
};

struct DeviceContext {
  int cuda_index = -1;
  cudaDeviceProp properties{};
  cudaStream_t stream = nullptr;
  PathPoint* identity_point = nullptr;
  std::string redacted_id;
};

inline void check_cuda(cudaError_t status, const char* operation) {
  if (status != cudaSuccess) {
    throw std::runtime_error(std::string(operation) + ": " + cudaGetErrorString(status));
  }
}

inline std::string json_escape(std::string_view input) {
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

inline std::uint64_t fnv_update(
    std::uint64_t state,
    const unsigned char* data,
    std::size_t size) {
  constexpr std::uint64_t prime = 0x100000001b3ULL;
  for (std::size_t index = 0; index < size; ++index) {
    state ^= static_cast<std::uint64_t>(data[index]);
    state *= prime;
  }
  return state;
}

inline std::string redacted_device_id(const cudaUUID_t& uuid) {
  std::uint64_t state = 0xcbf29ce484222325ULL;
  state = fnv_update(
      state,
      reinterpret_cast<const unsigned char*>(kContract),
      std::char_traits<char>::length(kContract));
  state = fnv_update(
      state,
      reinterpret_cast<const unsigned char*>(uuid.bytes),
      sizeof(uuid.bytes));
  std::ostringstream output;
  output << std::hex << std::setw(16) << std::setfill('0') << state;
  return output.str();
}

inline std::string format_cuda_version(int value) {
  if (value <= 0) {
    return "unknown";
  }
  std::ostringstream output;
  output << value / 1000 << '.' << (value % 1000) / 10;
  if (value % 10 != 0) {
    output << '.' << value % 10;
  }
  return output.str();
}

inline std::uint64_t parse_unsigned(
    std::string_view text,
    std::string_view option) {
  const std::string value(text);
  std::size_t consumed = 0;
  const unsigned long long parsed = std::stoull(value, &consumed, 10);
  if (consumed != value.size()) {
    throw std::runtime_error(std::string(option) + " requires an unsigned integer");
  }
  return parsed;
}

inline float parse_positive_float(
    std::string_view text,
    std::string_view option) {
  const std::string value(text);
  std::size_t consumed = 0;
  const float parsed = std::stof(value, &consumed);
  if (consumed != value.size() || !std::isfinite(parsed) || parsed <= 0.0F) {
    throw std::runtime_error(std::string(option) + " requires a finite positive value");
  }
  return parsed;
}

inline std::vector<int> parse_devices(std::string_view text) {
  std::vector<int> devices;
  std::set<int> seen;
  std::size_t start = 0;
  while (start < text.size()) {
    const std::size_t separator = text.find(',', start);
    const std::size_t end =
        separator == std::string_view::npos ? text.size() : separator;
    if (end == start) {
      throw std::runtime_error("--devices must be a comma-separated list of integers");
    }
    const auto parsed = parse_unsigned(text.substr(start, end - start), "--devices");
    if (parsed > static_cast<std::uint64_t>(std::numeric_limits<int>::max())) {
      throw std::runtime_error("--devices contains an index outside the integer range");
    }
    const int device = static_cast<int>(parsed);
    if (!seen.insert(device).second) {
      throw std::runtime_error("--devices contains a duplicate index");
    }
    devices.push_back(device);
    if (separator == std::string_view::npos) {
      break;
    }
    start = separator + 1;
  }
  if (devices.size() < 2 || devices.size() > kMaximumDevices) {
    throw std::runtime_error("--devices must select between 2 and 8 unique devices");
  }
  return devices;
}

inline Options parse_options(int argc, char** argv) {
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
      if (value < 3 || value > 1048577 || value % 2 == 0) {
        throw std::runtime_error("--samples must be an odd value in [3, 1048577]");
      }
      options.samples = static_cast<std::uint32_t>(value);
    } else if (argument == "--interval-width") {
      const auto value = parse_unsigned(require_value(argument), argument);
      if (value == 0 || value > std::numeric_limits<std::uint32_t>::max()) {
        throw std::runtime_error("--interval-width must be a positive 32-bit value");
      }
      options.interval_width = static_cast<std::uint32_t>(value);
    } else if (argument == "--block-size") {
      const auto value = parse_unsigned(require_value(argument), argument);
      if (value == 0 || value > 1024) {
        throw std::runtime_error("--block-size must be in [1, 1024]");
      }
      options.block_size = static_cast<std::uint32_t>(value);
    } else if (argument == "--devices") {
      options.devices = parse_devices(require_value(argument));
    } else if (argument == "--repeat-run") {
      const auto value = parse_unsigned(require_value(argument), argument);
      if (value > std::numeric_limits<std::uint32_t>::max()) {
        throw std::runtime_error("--repeat-run is outside the supported range");
      }
      options.repeat_run = static_cast<std::uint32_t>(value);
    } else if (argument == "--frame-gate") {
      options.frame_gate = parse_positive_float(require_value(argument), argument);
    } else if (argument == "--centre-gate") {
      options.centre_gate = parse_positive_float(require_value(argument), argument);
    } else if (argument == "--tail-gate") {
      options.tail_gate = parse_positive_float(require_value(argument), argument);
    } else if (argument == "--output-csv") {
      options.output_csv = std::string(require_value(argument));
      if (options.output_csv.empty()) {
        throw std::runtime_error("--output-csv must not be empty");
      }
    } else if (argument == "--help" || argument == "-h") {
      std::cout
          << "RSH physical multi-device CUDA path experiment\n\n"
          << "Usage: rsh-multi-cuda [options]\n\n"
          << "  --samples N          odd path sample count (default 4097)\n"
          << "  --interval-width N   contiguous intervals per shard (default 257)\n"
          << "  --block-size N       emission kernel block size (default 128)\n"
          << "  --devices A,B        at least two unique CUDA device indices\n"
          << "  --repeat-run N       run identifier copied into the sidecar\n"
          << "  --frame-gate X       frame invariant gate (default 5e-5)\n"
          << "  --centre-gate X      centred midpoint gate (default 1e-6)\n"
          << "  --tail-gate X        reduction/tail gate (default 1e-5)\n"
          << "  --output-csv PATH    complete ordered path readback\n";
      std::exit(EXIT_SUCCESS);
    } else {
      throw std::runtime_error("unknown option: " + std::string(argument));
    }
  }
  if (options.output_csv.empty()) {
    throw std::runtime_error("--output-csv is required for complete readback evidence");
  }
  return options;
}

inline std::vector<Transform> inclusive_scan(
    std::vector<Transform> current,
    std::uint32_t* passes) {
  std::uint32_t offset = 1;
  *passes = 0;
  while (offset < current.size()) {
    const std::vector<Transform> previous = current;
    for (std::size_t index = offset; index < current.size(); ++index) {
      current[index] = compose(previous[index - offset], previous[index]);
    }
    offset *= 2U;
    ++*passes;
  }
  return current;
}

inline float vector_norm(float3 value) {
  return std::hypot(value.x, value.y, value.z);
}

inline void write_csv(
    const std::string& path,
    const std::vector<PathPoint>& points) {
  std::ofstream output(path, std::ios::binary | std::ios::trunc);
  if (!output) {
    throw std::runtime_error("cannot open --output-csv path");
  }
  output << "index,p,s,x,y,z,kappa,tau,tx,ty,tz,nx,ny,nz,bx,by,bz\n";
  output << std::setprecision(9);
  for (std::size_t index = 0; index < points.size(); ++index) {
    const PathPoint& point = points[index];
    output << index << ',' << point.normal_p.w << ',' << point.binormal_s.w << ','
           << point.position_kappa.x << ',' << point.position_kappa.y << ','
           << point.position_kappa.z << ',' << point.position_kappa.w << ','
           << point.tangent_tau.w << ',' << point.tangent_tau.x << ','
           << point.tangent_tau.y << ',' << point.tangent_tau.z << ','
           << point.normal_p.x << ',' << point.normal_p.y << ',' << point.normal_p.z
           << ',' << point.binormal_s.x << ',' << point.binormal_s.y << ','
           << point.binormal_s.z << '\n';
  }
  if (!output) {
    throw std::runtime_error("failed while writing complete path CSV");
  }
}

inline void cleanup(
    std::vector<DeviceContext>& devices,
    std::vector<Shard>& shards) {
  for (Shard& shard : shards) {
    const int cuda_index = devices[shard.device_slot].cuda_index;
    cudaSetDevice(cuda_index);
    if (shard.prefixes != nullptr) cudaFree(shard.prefixes);
    if (shard.reduction != nullptr) cudaFree(shard.reduction);
    if (shard.base != nullptr) cudaFree(shard.base);
    if (shard.points != nullptr) cudaFree(shard.points);
    shard.prefixes = nullptr;
    shard.reduction = nullptr;
    shard.base = nullptr;
    shard.points = nullptr;
  }
  for (DeviceContext& device : devices) {
    cudaSetDevice(device.cuda_index);
    if (device.identity_point != nullptr) cudaFree(device.identity_point);
    if (device.stream != nullptr) cudaStreamDestroy(device.stream);
    device.identity_point = nullptr;
    device.stream = nullptr;
  }
}

}  // namespace rsh_multi_cuda
