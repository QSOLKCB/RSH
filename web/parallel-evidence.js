export const PARALLEL_GATES = Object.freeze({
  position: 5e-4,
  frame: 5e-4,
  schedule: 1e-4,
  frameNorm: 5e-5,
  frameOrthogonality: 5e-5,
});

const RESIDUAL_DEFINITIONS = Object.freeze([
  {
    resultKey: "maxPosition",
    gateKey: "position",
    name: "position_component",
    sidecarKey: "max_position_component_vs_parallel_wasm_f64",
  },
  {
    resultKey: "maxFrame",
    gateKey: "frame",
    name: "frame_component",
    sidecarKey: "max_frame_component_vs_parallel_wasm_f64",
  },
  {
    resultKey: "maxSchedule",
    gateKey: "schedule",
    name: "schedule_component",
    sidecarKey: "max_schedule_component_vs_parallel_wasm_f64",
  },
  {
    resultKey: "maxFrameNorm",
    gateKey: "frameNorm",
    name: "frame_norm",
    sidecarKey: "max_frame_norm_error",
  },
  {
    resultKey: "maxFrameOrthogonality",
    gateKey: "frameOrthogonality",
    name: "frame_orthogonality",
    sidecarKey: "max_frame_orthogonality_error",
  },
]);

export function residualSnapshot(result) {
  return Object.fromEntries(
    RESIDUAL_DEFINITIONS.map(({ resultKey, sidecarKey }) => [sidecarKey, result[resultKey]]),
  );
}

export function failedResidualGates(result, gates = PARALLEL_GATES) {
  return RESIDUAL_DEFINITIONS.flatMap(({ resultKey, gateKey, name }) => {
    const observed = Number(result[resultKey]);
    const gate = Number(gates[gateKey]);
    return Number.isFinite(observed) && observed <= gate
      ? []
      : [{ name, observed, gate, finite: Number.isFinite(observed) }];
  });
}

export function gatePassed(result, gates = PARALLEL_GATES) {
  return failedResidualGates(result, gates).length === 0;
}

export class ParallelResidualGateError extends Error {
  constructor(stage, runIndex, result, gates = PARALLEL_GATES) {
    const failures = failedResidualGates(result, gates);
    const summary = failures
      .map(({ name, observed, gate }) => `${name}=${observed} > ${gate}`)
      .join(", ");
    super(`WebGPU ${stage} run ${runIndex} exceeded residual gates: ${summary}`);
    this.name = "ParallelResidualGateError";
    this.stage = stage;
    this.runIndex = runIndex;
    this.result = result;
    this.failures = failures;
  }
}

export function assertResidualGates(result, stage, runIndex, gates = PARALLEL_GATES) {
  if (!gatePassed(result, gates)) {
    throw new ParallelResidualGateError(stage, runIndex, result, gates);
  }
}

export function createRejectedParallelSidecar({
  oracle,
  config,
  error,
  gates = PARALLEL_GATES,
  warmupRuns,
  measuredRuns,
  wasmTimings,
  gpuTimings,
  wasmMedian,
  minimumSpeedupSamples,
}) {
  if (!(error instanceof ParallelResidualGateError)) {
    throw new TypeError("A residual-gate error is required to create rejection evidence");
  }

  return {
    schema: "RSH-WEBGPU-FRENET-PARALLEL-BENCHMARK-V1",
    status: "REJECTED",
    parallel_contract: oracle.parallel_contract,
    interval_policy: oracle.interval_policy,
    scan_policy: oracle.scan_policy,
    model: oracle.model,
    model_version: oracle.model_version,
    configuration: config,
    metadata: error.result.metadata,
    failure: {
      stage: error.stage,
      run_index: error.runIndex,
      message: error.message,
      failed_gates: error.failures,
      failed_run_elapsed_milliseconds: error.result.elapsedMilliseconds,
    },
    residuals: residualSnapshot(error.result),
    gates,
    benchmark: {
      warmup_runs_required: warmupRuns,
      measured_runs_required: measuredRuns,
      wasm_end_to_end_milliseconds: wasmTimings,
      gpu_completed_end_to_end_readback_milliseconds: gpuTimings,
      wasm_median_milliseconds: wasmMedian,
      minimum_samples_for_speedup_statement: minimumSpeedupSamples,
      statistic: "median",
      timing_scope: {
        wasm: "ABI-call-JSON-serialization-memory-read-and-JSON-parse",
        webgpu: error.result.metadata.timing_scope,
      },
      benchmark_completed: false,
    },
    actual_gpu_execution: true,
    parallel_scan_execution: true,
    complete_path_readback: true,
    conformance_passed: false,
    actual_multi_device_execution: false,
    distributed_execution: false,
    speedup_claim: false,
    speedup_claim_scope: "none",
    universal_speedup_claim: false,
    geometry_receipt_authority: false,
    evidence_note: "A physical WebGPU adapter executed and returned the complete path, but one or more published residual gates failed. The diagnostic sidecar is retained; no speedup or geometry-authority claim is permitted.",
  };
}
