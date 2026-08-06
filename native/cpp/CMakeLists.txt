cmake_minimum_required(VERSION 3.20)
project(rsh_native_adapters LANGUAGES CXX)

option(RSH_ENABLE_CUDA "Build the optional CUDA schedule and multi-device path executables" OFF)
set(
  RSH_CUDA_ARCHITECTURES
  ""
  CACHE STRING
  "CUDA architectures for RSH CUDA adapters (empty uses the compiler default; examples: native, 86, 89, 120)"
)

find_program(CARGO_EXECUTABLE cargo REQUIRED)
set(RSH_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../..")
set(RSH_CARGO_TARGET "${CMAKE_BINARY_DIR}/cargo-target")

if(APPLE)
  set(RSH_FFI_SHARED "${RSH_CARGO_TARGET}/release/librsh_ffi.dylib")
elseif(UNIX)
  set(RSH_FFI_SHARED "${RSH_CARGO_TARGET}/release/librsh_ffi.so")
else()
  message(FATAL_ERROR "The checked-in CMake adapter currently targets Unix-like hosts; the C ABI header remains platform-neutral.")
endif()

add_custom_command(
  OUTPUT "${RSH_FFI_SHARED}"
  COMMAND "${CMAKE_COMMAND}" -E env "CARGO_TARGET_DIR=${RSH_CARGO_TARGET}"
          "${CARGO_EXECUTABLE}" build --locked --release -p rsh-ffi
  WORKING_DIRECTORY "${RSH_ROOT}"
  DEPENDS
    "${RSH_ROOT}/Cargo.toml"
    "${RSH_ROOT}/Cargo.lock"
    "${RSH_ROOT}/crates/rsh-core/src/lib.rs"
    "${RSH_ROOT}/crates/rsh-ffi/Cargo.toml"
    "${RSH_ROOT}/crates/rsh-ffi/src/lib.rs"
    "${RSH_ROOT}/include/rsh_ffi.h"
  COMMENT "Building the verified Rust C ABI"
  VERBATIM
)
add_custom_target(rsh_ffi_build ALL DEPENDS "${RSH_FFI_SHARED}")

add_executable(rsh-cpp rsh_cpp.cpp)
add_dependencies(rsh-cpp rsh_ffi_build)
target_compile_features(rsh-cpp PRIVATE cxx_std_17)
target_compile_options(rsh-cpp PRIVATE -Wall -Wextra -Wpedantic -Werror)
target_include_directories(rsh-cpp PRIVATE "${RSH_ROOT}/include")
target_link_libraries(rsh-cpp PRIVATE "${RSH_FFI_SHARED}")
set_target_properties(rsh-cpp PROPERTIES BUILD_RPATH "${RSH_CARGO_TARGET}/release")

if(RSH_ENABLE_CUDA)
  if(RSH_CUDA_ARCHITECTURES STREQUAL "native" AND CMAKE_VERSION VERSION_LESS 3.24)
    message(FATAL_ERROR
      "RSH_CUDA_ARCHITECTURES=native requires CMake 3.24 or newer. "
      "Use an explicit numeric architecture such as 120, or upgrade CMake."
    )
  endif()

  enable_language(CUDA)
  if(RSH_CUDA_ARCHITECTURES)
    set(CMAKE_CUDA_ARCHITECTURES "${RSH_CUDA_ARCHITECTURES}")
  endif()
  if(CMAKE_CUDA_ARCHITECTURES)
    set(RSH_CUDA_ARCHITECTURES_EFFECTIVE "${CMAKE_CUDA_ARCHITECTURES}")
  else()
    set(RSH_CUDA_ARCHITECTURES_EFFECTIVE "compiler-default")
  endif()
  string(REPLACE ";" "," RSH_CUDA_ARCHITECTURES_LABEL "${RSH_CUDA_ARCHITECTURES_EFFECTIVE}")
  message(STATUS "RSH CUDA architectures: ${RSH_CUDA_ARCHITECTURES_EFFECTIVE}")

  add_executable(rsh-cuda "${RSH_ROOT}/native/cuda/rsh_schedule_cuda.cu")
  add_dependencies(rsh-cuda rsh_ffi_build)
  target_compile_features(rsh-cuda PRIVATE cxx_std_17)
  target_compile_definitions(
    rsh-cuda
    PRIVATE RSH_CUDA_ARCHITECTURES="${RSH_CUDA_ARCHITECTURES_LABEL}"
  )
  target_include_directories(rsh-cuda PRIVATE "${RSH_ROOT}/include")
  target_link_libraries(rsh-cuda PRIVATE "${RSH_FFI_SHARED}")
  set_target_properties(
    rsh-cuda
    PROPERTIES
      CUDA_STANDARD 17
      CUDA_STANDARD_REQUIRED YES
      BUILD_RPATH "${RSH_CARGO_TARGET}/release"
  )

  add_executable(
    rsh-multi-cuda
    "${RSH_ROOT}/native/cuda/rsh_multi_device_path_cuda.cu"
  )
  target_compile_features(rsh-multi-cuda PRIVATE cxx_std_17)
  target_compile_definitions(
    rsh-multi-cuda
    PRIVATE RSH_CUDA_ARCHITECTURES="${RSH_CUDA_ARCHITECTURES_LABEL}"
  )
  target_include_directories(
    rsh-multi-cuda
    PRIVATE "${RSH_ROOT}/native/cuda"
  )
  set_target_properties(
    rsh-multi-cuda
    PROPERTIES
      CUDA_STANDARD 17
      CUDA_STANDARD_REQUIRED YES
  )

  if(CMAKE_CUDA_ARCHITECTURES)
    set_property(TARGET rsh-cuda PROPERTY CUDA_ARCHITECTURES "${CMAKE_CUDA_ARCHITECTURES}")
    set_property(TARGET rsh-multi-cuda PROPERTY CUDA_ARCHITECTURES "${CMAKE_CUDA_ARCHITECTURES}")
  endif()
endif()

enable_testing()
add_test(NAME rsh_cpp_info COMMAND rsh-cpp info)
add_test(NAME rsh_cpp_verify COMMAND rsh-cpp verify --samples 129)
add_test(NAME rsh_cpp_schedule COMMAND rsh-cpp schedule --samples 4096)
add_test(NAME rsh_cpp_cuda_reference_default COMMAND rsh-cpp cuda-reference --threshold 1e-4)
add_test(NAME rsh_cpp_cuda_reference_explicit_129 COMMAND rsh-cpp cuda-reference --samples 129 --threshold 1e-4)
set_tests_properties(
  rsh_cpp_cuda_reference_explicit_129
  PROPERTIES PASS_REGULAR_EXPRESSION "\"samples\": 129"
)
