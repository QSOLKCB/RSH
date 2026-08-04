#include "rsh_ffi.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>

namespace {

struct BytesOwner {
  RshOwnedBytesV1 value{};
  ~BytesOwner() { rsh_ffi_free_bytes(&value); }
  BytesOwner(const BytesOwner&) = delete;
  BytesOwner& operator=(const BytesOwner&) = delete;
  BytesOwner() = default;
};

struct ScheduleOwner {
  RshOwnedScheduleV1 value{};
  ~ScheduleOwner() { rsh_ffi_free_schedule(&value); }
  ScheduleOwner(const ScheduleOwner&) = delete;
  ScheduleOwner& operator=(const ScheduleOwner&) = delete;
  ScheduleOwner() = default;
};

struct Options {
  std::uint64_t samples;
  std::string json_path;
  std::string csv_path;
  double threshold;
};

std::string last_error() {
  const char* message = rsh_ffi_last_error();
  return message == nullptr || *message == '\0' ? "unknown RSH FFI error" : message;
}

void validate_abi() {
  if (rsh_ffi_abi_version() != RSH_FFI_ABI_VERSION) {
    throw std::runtime_error("RSH FFI ABI version mismatch");
  }
  if (rsh_ffi_config_size() != sizeof(RshConfigV1) ||
      rsh_ffi_summary_size() != sizeof(RshSummaryV1) ||
      rsh_ffi_schedule_point_size() != sizeof(RshSchedulePointV1)) {
    throw std::runtime_error("RSH FFI structure layout mismatch");
  }
  if (rsh_ffi_max_geometry_samples() != RSH_FFI_MAX_GEOMETRY_SAMPLES ||
      rsh_ffi_max_schedule_samples() != RSH_FFI_MAX_SCHEDULE_SAMPLES) {
    throw std::runtime_error("RSH FFI safety-limit mismatch");
  }
}

RshConfigV1 make_config(std::uint64_t samples) {
  return RshConfigV1{
      static_cast<std::uint32_t>(sizeof(RshConfigV1)),
      RSH_FFI_ABI_VERSION,
      samples,
      0.0,
      4.0,
      0.85,
      0.22,
      0.13,
  };
}

void write_bytes(const std::string& path, const std::uint8_t* data, std::size_t size) {
  std::ofstream output(path, std::ios::binary);
  if (!output) {
    throw std::runtime_error("cannot open output file: " + path);
  }
  output.write(reinterpret_cast<const char*>(data), static_cast<std::streamsize>(size));
  if (!output) {
    throw std::runtime_error("failed to write output file: " + path);
  }
}

Options parse_options(int argc, char** argv, int first, std::uint64_t default_samples) {
  Options options{default_samples, {}, {}, 1.0e-4};
  for (int index = first; index < argc; ++index) {
    const std::string_view argument(argv[index]);
    auto require_value = [&](std::string_view name) -> std::string_view {
      if (index + 1 >= argc) {
        throw std::runtime_error(std::string(name) + " requires a value");
      }
      return argv[++index];
    };

    if (argument == "--samples" || argument == "-n") {
      options.samples = std::stoull(std::string(require_value(argument)));
    } else if (argument == "--json") {
      options.json_path = require_value(argument);
    } else if (argument == "--csv") {
      options.csv_path = require_value(argument);
    } else if (argument == "--threshold") {
      options.threshold = std::stod(std::string(require_value(argument)));
    } else {
      throw std::runtime_error("unknown option: " + std::string(argument));
    }
  }
  if (!std::isfinite(options.threshold) || options.threshold <= 0.0) {
    throw std::runtime_error("threshold must be finite and positive");
  }
  return options;
}

int run_verify(const Options& options) {
  const RshConfigV1 config = make_config(options.samples);
  RshSummaryV1 summary{};
  summary.struct_size = sizeof(RshSummaryV1);
  summary.abi_version = RSH_FFI_ABI_VERSION;
  BytesOwner json;

  const std::int32_t status = rsh_ffi_verify(&config, &summary, &json.value);
  if (status == RSH_FFI_STATUS_REJECTED || status == RSH_FFI_STATUS_PANIC) {
    throw std::runtime_error(last_error());
  }
  if (json.value.ptr == nullptr || json.value.len == 0) {
    throw std::runtime_error("RSH FFI returned an empty JSON report");
  }

  std::cout << "RSH C++ FFI verify ["
            << (status == RSH_FFI_STATUS_PASS ? "PASS" : "FAIL") << "]\n"
            << "  ABI                  = " << rsh_ffi_abi_version() << "\n"
            << "  samples              = " << summary.samples << "\n"
            << std::scientific << std::setprecision(3)
            << "  centre_error         = " << summary.centre_error << "\n"
            << std::fixed << std::setprecision(6)
            << "  max_kappa / bound    = " << summary.max_kappa << " / "
            << summary.kappa_bound << "\n"
            << "  tau range            = [" << summary.min_tau << ", " << summary.max_tau
            << "]\n"
            << std::scientific << std::setprecision(3)
            << "  frame_norm_error     = " << summary.max_frame_norm_error << "\n"
            << "  frame_orthogonality  = " << summary.max_frame_orthogonality_error << "\n"
            << "  receipt              = "
            << reinterpret_cast<const char*>(summary.receipt) << "\n";

  if (!options.json_path.empty()) {
    write_bytes(options.json_path, json.value.ptr, json.value.len);
    std::cout << "  JSON                 = " << options.json_path << "\n";
  }
  return status == RSH_FFI_STATUS_PASS ? EXIT_SUCCESS : EXIT_FAILURE;
}

int run_schedule(const Options& options) {
  const RshConfigV1 config = make_config(options.samples);
  ScheduleOwner schedule;
  const std::int32_t status = rsh_ffi_schedule(&config, &schedule.value);
  if (status != RSH_FFI_STATUS_PASS) {
    throw std::runtime_error(last_error());
  }
  if (schedule.value.ptr == nullptr || schedule.value.len != options.samples) {
    throw std::runtime_error("RSH FFI returned an invalid schedule array");
  }

  double min_kappa = std::numeric_limits<double>::infinity();
  double max_kappa = -std::numeric_limits<double>::infinity();
  double min_tau = std::numeric_limits<double>::infinity();
  double max_tau = -std::numeric_limits<double>::infinity();
  for (std::size_t index = 0; index < schedule.value.len; ++index) {
    const auto& point = schedule.value.ptr[index];
    min_kappa = std::min(min_kappa, point.kappa);
    max_kappa = std::max(max_kappa, point.kappa);
    min_tau = std::min(min_tau, point.tau);
    max_tau = std::max(max_tau, point.tau);
  }

  std::cout << "RSH C++ FFI schedule [PASS]\n"
            << "  samples              = " << schedule.value.len << "\n"
            << std::fixed << std::setprecision(6)
            << "  kappa range          = [" << min_kappa << ", " << max_kappa << "]\n"
            << "  tau range            = [" << min_tau << ", " << max_tau << "]\n";

  if (!options.csv_path.empty()) {
    std::ofstream output(options.csv_path);
    if (!output) {
      throw std::runtime_error("cannot open output file: " + options.csv_path);
    }
    output << "p,s,kappa,tau\n" << std::scientific << std::setprecision(17);
    for (std::size_t index = 0; index < schedule.value.len; ++index) {
      const auto& point = schedule.value.ptr[index];
      output << point.p << ',' << point.s << ',' << point.kappa << ',' << point.tau
             << '\n';
    }
    std::cout << "  CSV                  = " << options.csv_path << "\n";
  }
  return EXIT_SUCCESS;
}

int run_cuda_reference(const Options& options) {
  const RshConfigV1 config = make_config(options.samples);
  ScheduleOwner oracle;
  const std::int32_t status = rsh_ffi_schedule(&config, &oracle.value);
  if (status != RSH_FFI_STATUS_PASS) {
    throw std::runtime_error(last_error());
  }

  const float s0 = static_cast<float>(config.s0);
  const float s1 = static_cast<float>(config.s1);
  const float kappa_fraction = static_cast<float>(config.kappa_fraction);
  const float tau_floor = static_cast<float>(config.tau_floor);
  const float tau_amplitude = static_cast<float>(config.tau_amplitude);
  const float psi_value = static_cast<float>(rsh_ffi_psi());
  const float kappa_bound = static_cast<float>(rsh_ffi_kappa_bound());
  const float denominator = static_cast<float>(options.samples - 1);

  double max_kappa_residual = 0.0;
  double max_tau_residual = 0.0;
  for (std::size_t index = 0; index < oracle.value.len; ++index) {
    const float p = static_cast<float>(index) / denominator;
    const float s = s0 + (s1 - s0) * p;
    const float base = kappa_fraction * kappa_bound;
    const float kappa = base * (0.92F + 0.08F * std::cos(0.35F * s * psi_value));
    const float tau = tau_floor + tau_amplitude *
        (1.0F + std::sin(0.25F * s * psi_value));
    max_kappa_residual = std::max(
        max_kappa_residual,
        std::abs(static_cast<double>(kappa) - oracle.value.ptr[index].kappa));
    max_tau_residual = std::max(
        max_tau_residual,
        std::abs(static_cast<double>(tau) - oracle.value.ptr[index].tau));
  }
  const double maximum = std::max(max_kappa_residual, max_tau_residual);
  const bool pass = maximum <= options.threshold;

  std::cout << "{\n"
            << "  \"schema\": \"RSH-CUDA-F32-REFERENCE-V1\",\n"
            << "  \"status\": \"" << (pass ? "PASS" : "FAIL") << "\",\n"
            << "  \"actual_cuda_execution\": false,\n"
            << "  \"samples\": " << oracle.value.len << ",\n"
            << std::scientific << std::setprecision(17)
            << "  \"max_abs_kappa_vs_rust_f64\": " << max_kappa_residual << ",\n"
            << "  \"max_abs_tau_vs_rust_f64\": " << max_tau_residual << ",\n"
            << "  \"maximum_residual\": " << maximum << ",\n"
            << "  \"threshold\": " << options.threshold << "\n"
            << "}\n";
  return pass ? EXIT_SUCCESS : EXIT_FAILURE;
}

void print_usage() {
  std::cout
      << "RSH C++ native adapter\n\n"
      << "Usage:\n"
      << "  rsh-cpp info\n"
      << "  rsh-cpp verify [--samples N] [--json FILE]       (default N=129)\n"
      << "  rsh-cpp schedule [--samples N] [--csv FILE]      (default N=129)\n"
      << "  rsh-cpp cuda-reference [--samples N] [--threshold VALUE]"
         "  (default N=4096)\n";
}

}  // namespace

int main(int argc, char** argv) {
  try {
    validate_abi();
    if (argc < 2) {
      print_usage();
      return EXIT_FAILURE;
    }
    const std::string command(argv[1]);
    if (command == "info" || command == "--help" || command == "-h") {
      print_usage();
      std::cout << "\nABI version: " << rsh_ffi_abi_version()
                << "\ngeometry sample cap: " << rsh_ffi_max_geometry_samples()
                << "\nschedule sample cap: " << rsh_ffi_max_schedule_samples()
                << "\npsi: " << std::setprecision(17) << rsh_ffi_psi()
                << "\nkappa bound: " << rsh_ffi_kappa_bound() << "\n";
      return EXIT_SUCCESS;
    }

    const std::uint64_t default_samples = command == "cuda-reference" ? 4096 : 129;
    const Options options = parse_options(argc, argv, 2, default_samples);
    if (command == "verify") {
      return run_verify(options);
    }
    if (command == "schedule") {
      return run_schedule(options);
    }
    if (command == "cuda-reference") {
      return run_cuda_reference(options);
    }
    throw std::runtime_error("unknown command: " + command);
  } catch (const std::exception& error) {
    std::cerr << "rsh-cpp: " << error.what() << '\n';
    return EXIT_FAILURE;
  }
}
