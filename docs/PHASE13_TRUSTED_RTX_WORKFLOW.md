# Phase 13 — Trusted self-hosted RTX hardware workflow

## Status

**Workflow implemented; first protected dispatch pending after merge.**

The repository now contains one combined CUDA and WebGPU hardware workflow for a
deliberately labelled self-hosted RTX runner:

```text
.github/workflows/rtx-hardware.yml
```

It automates the same physical checks previously performed through independent
audits while preserving the rule that accelerator evidence is never geometry
authority.

## Threat model

A self-hosted GPU runner has access to local hardware, drivers, containers, the
graphical session, and persistent host state. Running arbitrary public pull
request code on that machine would be an unacceptable trust escalation.

The workflow therefore enforces all of the following:

- `workflow_dispatch` is the only trigger;
- the workflow must be dispatched from `main`;
- the repository identity must be exactly `QSOLKCB/RSH`;
- the dispatch actor must have `admin` or `maintain` permission;
- the job uses the protected `rtx-hardware` GitHub environment;
- the runner must carry the dedicated `rsh-trusted` RTX/CUDA/WebGPU labels;
- checkout credentials are not persisted;
- an optional target must be a full commit SHA already contained in `main`;
- the workflow never checks out an unmerged pull-request head;
- concurrency is one hardware audit at a time;
- no repository or package write permission is granted.

Do not add `pull_request`, `pull_request_target`, issue, comment, or scheduled
triggers to this workflow.

## Required repository configuration

Create a GitHub environment named:

```text
rtx-hardware
```

Recommended environment protection:

1. required reviewer approval;
2. deployment branch restricted to `main`;
3. no environment secrets unless a later adapter has a documented requirement;
4. prevent self-review where the GitHub plan supports it.

The environment is a human approval boundary. The workflow's own actor and
commit checks remain mandatory even when environment protection is configured.

## Runner contract

The self-hosted runner must use these labels:

```text
self-hosted
linux
x64
nvidia
rtx
cuda
webgpu
rsh-trusted
```

The reviewed GPU-agent setup must provide:

```text
rsh-gpu-shell
rsh-gpu-check
google-chrome-stable
puppeteer-core under ~/.local/share/rsh-gpu-agent/webgpu/node_modules
```

It must also provide a usable NVIDIA driver, Docker GPU access, CMake, Rust,
Python, Node, and either:

- an active Wayland/X11 graphical session for the default `graphical` mode; or
- a verified hardware-capable headless Chrome path for `headless` mode.

The graphical runner service must inherit `WAYLAND_DISPLAY` or `DISPLAY` and any
required `XDG_RUNTIME_DIR` value. A browser process that falls back to
SwiftShader, llvmpipe, lavapipe, or another software adapter is rejected.

## Trusted commit selection

The default target is the current `main` commit. A dispatcher may supply an
older full SHA only when:

```text
git merge-base --is-ancestor TARGET origin/main
```

passes. This supports replaying a historical accepted commit without allowing an
unmerged branch or external fork to execute on the private runner.

## CUDA path

CUDA executes inside the runner's reviewed pinned container through
`rsh-gpu-shell`. The workflow:

1. records the host/container readiness report;
2. configures the declared numeric CUDA architecture;
3. builds `rsh-cpp` and `rsh-cuda`;
4. executes the actual RSH CUDA kernel three times;
5. requires repeatable selected sidecar fields;
6. compares readback with the Rust FFI f64 schedule;
7. requires the published `1e-4` residual gate;
8. requires Compute Sanitizer memcheck and racecheck;
9. preserves `geometry_receipt_authority: false`.

A generic `1 + 41 = 42` CUDA smoke test is not accepted as RSH execution.

## WebGPU path

The workflow builds fresh geometry and parallel WASM modules from the tested
commit, serves `web/` only on localhost, and drives Chrome with
`scripts/test_rtx_webgpu.cjs`.

### Schedule field

The browser must:

- obtain a physical NVIDIA adapter;
- execute `kappa_tau_field.wgsl`;
- read back all 4,096 schedule samples;
- export the accepted residual sidecar;
- remain under the `1e-4` schedule gate.

The workflow wraps the browser sidecar in
`RSH-TRUSTED-RTX-WEBGPU-SCHEDULE-V1` to state explicitly:

```text
actual_gpu_execution: true
complete_field_readback: true
speedup_claim: false
universal_speedup_claim: false
geometry_receipt_authority: false
```

### Parallel full path

The browser must execute the 4,097-point normalized-quaternion scan with:

```text
2 warm-up runs
7 measured runs
13 scan passes
32-byte transforms
complete path readback
```

All five unchanged residual gates must pass. A local speedup statement remains
optional and adapter/browser scoped. `universal_speedup_claim` remains false.

## Evidence and privacy

The raw CUDA harness records a stable device UUID as required by its adapter
sidecar. Public workflow logs and artifacts must not publish that identifier.

The workflow therefore separates evidence into:

```text
artifacts/rtx-private/   temporary raw evidence on the runner
artifacts/rtx-publish/   redacted evidence eligible for upload
```

`scripts/verify_rtx_hardware.py` validates the raw inputs and emits the redacted
aggregate:

```text
RSH-TRUSTED-RTX-HARDWARE-AUDIT-V1
```

The uploaded deterministic ZIP contains only:

- the redacted aggregate report;
- WebGPU schedule and parallel sidecars;
- workflow metadata that explicitly records `raw_device_uuid_published: false`;
- a manifest and external SHA-256 receipt.

Raw CUDA evidence is deleted from the runner workspace after packaging. It is
not committed and is not included in the public Actions artifact.

## Portable validation

The privileged workflow itself is never run by pull requests. A separate
GitHub-hosted workflow validates its source:

```text
.github/workflows/rtx-workflow-boundaries.yml
```

Portable checks cover:

- Node and Python syntax;
- evidence validator unit tests;
- dispatch-only trigger policy;
- main-ancestor checkout restriction;
- protected environment and runner labels;
- required sanitizer policy;
- private-evidence upload exclusion;
- NVIDIA hardware and software-adapter rejection;
- authority and universal-speedup boundaries.

Portable validation proves the workflow policy and tooling are well formed. It
does not claim a physical RTX execution.

## First post-merge acceptance run

After merging this phase:

1. configure the `rtx-hardware` environment protections;
2. register the runner with the required labels;
3. run the workflow from `main` with a blank target SHA;
4. use architecture `120` on the audited RTX 5060 Ti;
5. use `graphical` WebGPU mode unless the headless path is independently proven;
6. download and verify the deterministic redacted artifact;
7. record the run ID and redacted PASS summary in the pull request or release
   notes without committing the raw device UUID.

## Evidence boundary

A passing workflow may state that one trusted runner physically executed the
recorded CUDA and WebGPU adapters at one accepted commit. It may not state:

```text
universal speedup
multi-device execution
distributed execution
geometry receipt authority
physical-theory validation
```

The Python/Rust f64 contracts remain the scientific and numerical references.
