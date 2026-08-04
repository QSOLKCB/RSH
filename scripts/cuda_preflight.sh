#!/bin/sh
# Report CUDA build readiness without installing packages or changing the host.
set -u

ready=1

section() {
  printf '\n== %s ==\n' "$1"
}

run_optional() {
  label=$1
  shift
  printf '%s: ' "$label"
  if command -v "$1" >/dev/null 2>&1; then
    printf '\n'
    "$@" || true
  else
    printf 'not found\n'
    ready=0
  fi
}

section "Host"
uname -a || true
if [ -r /etc/os-release ]; then
  cat /etc/os-release
fi
getconf GNU_LIBC_VERSION 2>/dev/null || true

section "Toolchain"
run_optional "CMake" cmake --version
run_optional "C++ compiler" c++ --version
run_optional "Rust compiler" rustc --version
run_optional "Cargo" cargo --version
run_optional "CUDA compiler" nvcc --version

section "NVIDIA runtime"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi || ready=0
  printf '\nDetected devices:\n'
  nvidia-smi --query-gpu=index,name,driver_version,compute_cap,memory.total --format=csv || true
  capability=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | sed -n '1p' | tr -d '. ')
  if [ -n "$capability" ]; then
    printf 'Suggested CMake option: -DRSH_CUDA_ARCHITECTURES=%s\n' "$capability"
  fi
else
  printf 'nvidia-smi: not found\n'
  ready=0
fi

section "Diagnostics"
if command -v compute-sanitizer >/dev/null 2>&1; then
  compute-sanitizer --version || true
else
  printf 'compute-sanitizer: not found (optional)\n'
fi

section "RSH build hint"
printf '%s\n' \
  'cmake -S native/cpp -B build/cuda -DCMAKE_BUILD_TYPE=Release -DRSH_ENABLE_CUDA=ON -DRSH_CUDA_ARCHITECTURES=native' \
  'cmake --build build/cuda --target rsh-cuda --parallel'

if [ "$ready" -eq 1 ]; then
  printf '\nRSH CUDA preflight: READY\n'
  exit 0
fi
printf '\nRSH CUDA preflight: BLOCKED BY ENVIRONMENT\n'
exit 2
