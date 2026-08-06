#include "rsh_multi_device_support.hpp"

#include <chrono>
#include <iostream>

namespace rsh_multi_cuda {

struct Metrics {
  float max_frame_norm_error = 0.0F;
  float max_frame_orthogonality_error = 0.0F;
  float max_tail_error = 0.0F;
  float centre_error = 0.0F;
  bool pass_finite = true;
  bool pass_coverage = true;
  bool pass_schedule_bounds = true;
  bool pass_frame = true;
  bool pass_centre = true;
  bool pass_tail = true;
  bool pass_all = true;
};

Metrics validate_path(
    std::vector<PathPoint>& path,
    const std::vector<Shard>& shards,
    const std::vector<Transform>& reductions,
    const std::vector<Transform>& bases,
    const Options& options) {
  Metrics metrics;
  for (const Shard& shard : shards) {
    const Transform expected = compose(bases[shard.index], reductions[shard.index]);
    const PathPoint& tail = path[shard.start_interval + shard.interval_count];
    const float3 tangent =
        rotate_quaternion(expected.rotation, make_float3(1.0F, 0.0F, 0.0F));
    const float3 normal =
        rotate_quaternion(expected.rotation, make_float3(0.0F, 1.0F, 0.0F));
    const float3 binormal =
        rotate_quaternion(expected.rotation, make_float3(0.0F, 0.0F, 1.0F));
    const float expected_values[] = {
        expected.translation.x,
        expected.translation.y,
        expected.translation.z,
        tangent.x,
        tangent.y,
        tangent.z,
        normal.x,
        normal.y,
        normal.z,
        binormal.x,
        binormal.y,
        binormal.z};
    const float actual_values[] = {
        tail.position_kappa.x,
        tail.position_kappa.y,
        tail.position_kappa.z,
        tail.tangent_tau.x,
        tail.tangent_tau.y,
        tail.tangent_tau.z,
        tail.normal_p.x,
        tail.normal_p.y,
        tail.normal_p.z,
        tail.binormal_s.x,
        tail.binormal_s.y,
        tail.binormal_s.z};
    for (std::size_t index = 0; index < 12; ++index) {
      metrics.max_tail_error = std::max(
          metrics.max_tail_error,
          std::abs(expected_values[index] - actual_values[index]));
    }
  }

  const float3 centre = make_float3(
      path[options.samples / 2U].position_kappa.x,
      path[options.samples / 2U].position_kappa.y,
      path[options.samples / 2U].position_kappa.z);
  for (PathPoint& point : path) {
    point.position_kappa.x -= centre.x;
    point.position_kappa.y -= centre.y;
    point.position_kappa.z -= centre.z;
    const float3 tangent = make_float3(
        point.tangent_tau.x, point.tangent_tau.y, point.tangent_tau.z);
    const float3 normal =
        make_float3(point.normal_p.x, point.normal_p.y, point.normal_p.z);
    const float3 binormal = make_float3(
        point.binormal_s.x, point.binormal_s.y, point.binormal_s.z);
    metrics.max_frame_norm_error = std::max(
        metrics.max_frame_norm_error,
        std::max({
            std::abs(vector_norm(tangent) - 1.0F),
            std::abs(vector_norm(normal) - 1.0F),
            std::abs(vector_norm(binormal) - 1.0F)}));
    metrics.max_frame_orthogonality_error = std::max(
        metrics.max_frame_orthogonality_error,
        std::max({
            std::abs(vdot(tangent, normal)),
            std::abs(vdot(tangent, binormal)),
            std::abs(vdot(normal, binormal))}));
    const float values[] = {
        point.position_kappa.x,
        point.position_kappa.y,
        point.position_kappa.z,
        point.position_kappa.w,
        point.tangent_tau.x,
        point.tangent_tau.y,
        point.tangent_tau.z,
        point.tangent_tau.w,
        point.normal_p.x,
        point.normal_p.y,
        point.normal_p.z,
        point.normal_p.w,
        point.binormal_s.x,
        point.binormal_s.y,
        point.binormal_s.z,
        point.binormal_s.w};
    for (const float value : values) {
      metrics.pass_finite = metrics.pass_finite && std::isfinite(value);
    }
    metrics.pass_schedule_bounds = metrics.pass_schedule_bounds
        && point.position_kappa.w >= 0.0F
        && point.position_kappa.w <= kKappaBound + 1.0e-6F
        && point.tangent_tau.w > 0.0F
        && point.tangent_tau.w < 1.0F;
  }

  const PathPoint& centred = path[options.samples / 2U];
  metrics.centre_error = std::hypot(
      centred.position_kappa.x,
      centred.position_kappa.y,
      centred.position_kappa.z);
  metrics.pass_coverage =
      !shards.empty()
      && shards.front().start_interval == 0U
      && shards.back().start_interval + shards.back().interval_count
          == options.samples - 1U
      && std::adjacent_find(
             shards.begin(),
             shards.end(),
             [](const Shard& left, const Shard& right) {
               return left.start_interval + left.interval_count
                   != right.start_interval;
             }) == shards.end();
  metrics.pass_frame =
      metrics.max_frame_norm_error <= options.frame_gate
      && metrics.max_frame_orthogonality_error <= options.frame_gate;
  metrics.pass_centre = metrics.centre_error <= options.centre_gate;
  metrics.pass_tail = metrics.max_tail_error <= options.tail_gate;
  metrics.pass_all = metrics.pass_finite && metrics.pass_coverage
      && metrics.pass_schedule_bounds && metrics.pass_frame
      && metrics.pass_centre && metrics.pass_tail;
  return metrics;
}

void emit_sidecar(
    const Options& options,
    int detected_device_count,
    int driver_version,
    int runtime_version,
    std::uint32_t interval_count,
    std::uint32_t shard_prefix_passes,
    const std::vector<DeviceContext>& devices,
    const std::vector<Shard>& shards,
    const Metrics& metrics,
    double end_to_end_milliseconds) {
  const std::uint64_t reduction_bytes =
      static_cast<std::uint64_t>(shards.size()) * sizeof(Transform);
  const std::uint64_t base_bytes =
      static_cast<std::uint64_t>(shards.size()) * sizeof(Transform);
  const std::uint64_t readback_bytes =
      static_cast<std::uint64_t>(options.samples) * sizeof(PathPoint);

  std::cout << "{\n"
            << "  \"schema\": \"" << kSchema << "\",\n"
            << "  \"contract\": \"" << kContract << "\",\n"
            << "  \"source_parallel_contract\": \"" << kParallelContract << "\",\n"
            << "  \"source_shard_prefix_contract\": \"" << kShardContract << "\",\n"
            << "  \"status\": \"" << (metrics.pass_all ? "PASS" : "FAIL") << "\",\n"
            << "  \"actual_cuda_execution\": true,\n"
            << "  \"actual_multi_device_execution\": true,\n"
            << "  \"single_host_execution\": true,\n"
            << "  \"distributed_execution\": false,\n"
            << "  \"universal_speedup_claim\": false,\n"
            << "  \"geometry_receipt_authority\": false,\n"
            << "  \"raw_device_uuid_published\": false,\n"
            << "  \"assignment_policy\": \"round-robin-contiguous-shards-v1\",\n"
            << "  \"local_prefix_policy\": \"sequential-local-inclusive-quaternion-se3-f32-v1\",\n"
            << "  \"shard_prefix_policy\": \"hillis-steele-exclusive-shard-se3-f32-v1\",\n"
            << "  \"assembly_policy\": \"ordered-base-compose-local-prefix-v1\",\n"
            << "  \"repeat_run\": " << options.repeat_run << ",\n"
            << "  \"detected_device_count\": " << detected_device_count << ",\n"
            << "  \"used_device_count\": " << devices.size() << ",\n"
            << "  \"samples\": " << options.samples << ",\n"
            << "  \"intervals\": " << interval_count << ",\n"
            << "  \"interval_width\": " << options.interval_width << ",\n"
            << "  \"shard_count\": " << shards.size() << ",\n"
            << "  \"shard_prefix_passes\": " << shard_prefix_passes << ",\n"
            << "  \"final_shard_interval_count\": "
            << shards.back().interval_count << ",\n"
            << "  \"block_size\": " << options.block_size << ",\n"
            << "  \"stream_count_per_device\": 1,\n"
            << "  \"reduction_transfer_bytes\": " << reduction_bytes << ",\n"
            << "  \"base_transfer_bytes\": " << base_bytes << ",\n"
            << "  \"inter_device_peer_bytes\": 0,\n"
            << "  \"final_readback_bytes\": " << readback_bytes << ",\n"
            << "  \"readback_point_count\": " << options.samples << ",\n"
            << "  \"readback_float_components_per_point\": 16,\n"
            << "  \"complete_path_readback\": true,\n"
            << "  \"compiled_architectures\": \""
            << json_escape(RSH_CUDA_ARCHITECTURES) << "\",\n"
            << "  \"cuda_driver_api_version\": " << driver_version << ",\n"
            << "  \"cuda_driver_api\": \""
            << format_cuda_version(driver_version) << "\",\n"
            << "  \"cuda_runtime_version\": " << runtime_version << ",\n"
            << "  \"cuda_runtime\": \""
            << format_cuda_version(runtime_version) << "\",\n"
            << "  \"cuda_compile_version\": " << CUDART_VERSION << ",\n"
            << "  \"cuda_compile\": \""
            << format_cuda_version(CUDART_VERSION) << "\",\n"
            << std::scientific << std::setprecision(17)
            << "  \"max_frame_norm_error\": "
            << metrics.max_frame_norm_error << ",\n"
            << "  \"max_frame_orthogonality_error\": "
            << metrics.max_frame_orthogonality_error << ",\n"
            << "  \"max_tail_vs_reduction_component_error\": "
            << metrics.max_tail_error << ",\n"
            << "  \"centre_error\": " << metrics.centre_error << ",\n"
            << "  \"frame_gate\": " << options.frame_gate << ",\n"
            << "  \"tail_gate\": " << options.tail_gate << ",\n"
            << "  \"centre_gate\": " << options.centre_gate << ",\n"
            << "  \"end_to_end_milliseconds\": "
            << end_to_end_milliseconds << ",\n"
            << "  \"pass_finite\": "
            << (metrics.pass_finite ? "true" : "false") << ",\n"
            << "  \"pass_coverage\": "
            << (metrics.pass_coverage ? "true" : "false") << ",\n"
            << "  \"pass_schedule_bounds\": "
            << (metrics.pass_schedule_bounds ? "true" : "false") << ",\n"
            << "  \"pass_frame\": "
            << (metrics.pass_frame ? "true" : "false") << ",\n"
            << "  \"pass_centre\": "
            << (metrics.pass_centre ? "true" : "false") << ",\n"
            << "  \"pass_tail_integrity\": "
            << (metrics.pass_tail ? "true" : "false") << ",\n"
            << "  \"devices\": [\n";
  for (std::size_t index = 0; index < devices.size(); ++index) {
    const DeviceContext& device = devices[index];
    std::cout << "    {\"logical_slot\": " << index
              << ", \"cuda_index\": " << device.cuda_index
              << ", \"name\": \"" << json_escape(device.properties.name)
              << "\", \"redacted_device_id\": \"" << device.redacted_id
              << "\", \"compute_capability\": \"" << device.properties.major
              << '.' << device.properties.minor
              << "\", \"total_memory_bytes\": "
              << static_cast<unsigned long long>(device.properties.totalGlobalMem)
              << ", \"stream_ordinal\": 0}"
              << (index + 1U == devices.size() ? "\n" : ",\n");
  }
  std::cout << "  ],\n  \"shards\": [\n";
  for (std::size_t index = 0; index < shards.size(); ++index) {
    const Shard& shard = shards[index];
    const DeviceContext& device = devices[shard.device_slot];
    std::cout << "    {\"shard_index\": " << shard.index
              << ", \"start_interval\": " << shard.start_interval
              << ", \"end_interval_exclusive\": "
              << shard.start_interval + shard.interval_count
              << ", \"interval_count\": " << shard.interval_count
              << ", \"device_slot\": " << shard.device_slot
              << ", \"cuda_device_index\": " << device.cuda_index
              << ", \"stream_ordinal\": 0}"
              << (index + 1U == shards.size() ? "\n" : ",\n");
  }
  std::cout << "  ]\n}\n";
}

}  // namespace rsh_multi_cuda

int main(int argc, char** argv) {
  using namespace rsh_multi_cuda;
  std::vector<DeviceContext> devices;
  std::vector<Shard> shards;
  try {
    const Options options = parse_options(argc, argv);
    int detected_device_count = 0;
    check_cuda(cudaGetDeviceCount(&detected_device_count), "cudaGetDeviceCount");
    if (detected_device_count < 2) {
      throw std::runtime_error("at least two physical CUDA devices are required");
    }
    std::vector<int> selected = options.devices;
    if (selected.empty()) {
      selected = {0, 1};
    }
    for (const int device_index : selected) {
      if (device_index < 0 || device_index >= detected_device_count) {
        throw std::runtime_error("requested CUDA device index is unavailable");
      }
      DeviceContext context;
      context.cuda_index = device_index;
      check_cuda(cudaSetDevice(device_index), "cudaSetDevice");
      check_cuda(
          cudaGetDeviceProperties(&context.properties, device_index),
          "cudaGetDeviceProperties");
      if (options.block_size
          > static_cast<std::uint32_t>(context.properties.maxThreadsPerBlock)) {
        throw std::runtime_error("block size exceeds a selected device limit");
      }
      check_cuda(
          cudaStreamCreateWithFlags(&context.stream, cudaStreamNonBlocking),
          "cudaStreamCreateWithFlags");
      context.redacted_id = redacted_device_id(context.properties.uuid);
      devices.push_back(context);
    }

    const std::uint32_t interval_count = options.samples - 1U;
    const std::uint32_t shard_count =
        (interval_count + options.interval_width - 1U) / options.interval_width;
    if (shard_count == 0 || shard_count > kMaximumShards) {
      throw std::runtime_error("shard count is outside the published bound");
    }
    shards.reserve(shard_count);
    for (std::uint32_t shard_index = 0; shard_index < shard_count; ++shard_index) {
      const std::uint32_t start = shard_index * options.interval_width;
      const std::uint32_t end =
          std::min(start + options.interval_width, interval_count);
      shards.push_back(Shard{
          shard_index,
          start,
          end - start,
          shard_index % static_cast<std::uint32_t>(devices.size())});
    }

    const Parameters parameters{
        options.samples, 0.0F, 4.0F, 0.85F, 0.22F, 0.13F};
    std::vector<Transform> reductions(shard_count);
    const auto started = std::chrono::steady_clock::now();

    for (Shard& shard : shards) {
      DeviceContext& device = devices[shard.device_slot];
      check_cuda(cudaSetDevice(device.cuda_index), "cudaSetDevice build phase");
      const std::size_t transform_bytes =
          static_cast<std::size_t>(shard.interval_count) * sizeof(Transform);
      const std::size_t point_bytes =
          static_cast<std::size_t>(shard.interval_count) * sizeof(PathPoint);
      check_cuda(
          cudaMalloc(reinterpret_cast<void**>(&shard.prefixes), transform_bytes),
          "cudaMalloc shard prefixes");
      check_cuda(
          cudaMalloc(reinterpret_cast<void**>(&shard.reduction), sizeof(Transform)),
          "cudaMalloc shard reduction");
      check_cuda(
          cudaMalloc(reinterpret_cast<void**>(&shard.base), sizeof(Transform)),
          "cudaMalloc shard base");
      check_cuda(
          cudaMalloc(reinterpret_cast<void**>(&shard.points), point_bytes),
          "cudaMalloc shard points");
      build_local_prefixes<<<1, 1, 0, device.stream>>>(
          parameters,
          shard.start_interval,
          shard.interval_count,
          shard.prefixes,
          shard.reduction);
      check_cuda(cudaGetLastError(), "build_local_prefixes launch");
      check_cuda(
          cudaMemcpyAsync(
              &reductions[shard.index],
              shard.reduction,
              sizeof(Transform),
              cudaMemcpyDeviceToHost,
              device.stream),
          "cudaMemcpyAsync shard reduction");
    }
    for (DeviceContext& device : devices) {
      check_cuda(cudaSetDevice(device.cuda_index), "cudaSetDevice reduction sync");
      check_cuda(
          cudaStreamSynchronize(device.stream),
          "reduction stream synchronize");
    }

    std::uint32_t shard_prefix_passes = 0;
    const std::vector<Transform> inclusive =
        inclusive_scan(reductions, &shard_prefix_passes);
    std::vector<Transform> bases(shard_count, identity_transform());
    for (std::uint32_t index = 1; index < shard_count; ++index) {
      bases[index] = inclusive[index - 1U];
    }

    std::vector<PathPoint> path(options.samples);
    DeviceContext& identity_device = devices.front();
    check_cuda(
        cudaSetDevice(identity_device.cuda_index),
        "cudaSetDevice identity phase");
    check_cuda(
        cudaMalloc(
            reinterpret_cast<void**>(&identity_device.identity_point),
            sizeof(PathPoint)),
        "cudaMalloc identity point");
    emit_identity<<<1, 1, 0, identity_device.stream>>>(
        parameters, identity_device.identity_point);
    check_cuda(cudaGetLastError(), "emit_identity launch");
    check_cuda(
        cudaMemcpyAsync(
            path.data(),
            identity_device.identity_point,
            sizeof(PathPoint),
            cudaMemcpyDeviceToHost,
            identity_device.stream),
        "cudaMemcpyAsync identity point readback");

    for (Shard& shard : shards) {
      DeviceContext& device = devices[shard.device_slot];
      check_cuda(cudaSetDevice(device.cuda_index), "cudaSetDevice assembly phase");
      check_cuda(
          cudaMemcpyAsync(
              shard.base,
              &bases[shard.index],
              sizeof(Transform),
              cudaMemcpyHostToDevice,
              device.stream),
          "cudaMemcpyAsync shard base");
      const std::uint32_t blocks =
          (shard.interval_count + options.block_size - 1U) / options.block_size;
      apply_base_and_emit<<<blocks, options.block_size, 0, device.stream>>>(
          parameters,
          shard.start_interval,
          shard.interval_count,
          shard.prefixes,
          shard.base,
          shard.points);
      check_cuda(cudaGetLastError(), "apply_base_and_emit launch");
      check_cuda(
          cudaMemcpyAsync(
              path.data() + shard.start_interval + 1U,
              shard.points,
              static_cast<std::size_t>(shard.interval_count) * sizeof(PathPoint),
              cudaMemcpyDeviceToHost,
              device.stream),
          "cudaMemcpyAsync complete shard path readback");
    }
    for (DeviceContext& device : devices) {
      check_cuda(cudaSetDevice(device.cuda_index), "cudaSetDevice readback sync");
      check_cuda(
          cudaStreamSynchronize(device.stream),
          "readback stream synchronize");
    }

    Metrics metrics = validate_path(path, shards, reductions, bases, options);
    write_csv(options.output_csv, path);
    const auto finished = std::chrono::steady_clock::now();
    const double end_to_end_milliseconds =
        std::chrono::duration<double, std::milli>(finished - started).count();

    int driver_version = 0;
    int runtime_version = 0;
    check_cuda(cudaDriverGetVersion(&driver_version), "cudaDriverGetVersion");
    check_cuda(cudaRuntimeGetVersion(&runtime_version), "cudaRuntimeGetVersion");
    emit_sidecar(
        options,
        detected_device_count,
        driver_version,
        runtime_version,
        interval_count,
        shard_prefix_passes,
        devices,
        shards,
        metrics,
        end_to_end_milliseconds);
    cleanup(devices, shards);
    return metrics.pass_all ? EXIT_SUCCESS : EXIT_FAILURE;
  } catch (const std::exception& error) {
    cleanup(devices, shards);
    std::cerr << "rsh-multi-cuda: " << error.what() << '\n';
    return EXIT_FAILURE;
  }
}
