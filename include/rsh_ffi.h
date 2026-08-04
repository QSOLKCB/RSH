#ifndef RSH_FFI_H
#define RSH_FFI_H

#include <stddef.h>
#include <stdint.h>

#if defined(_WIN32)
  #if defined(RSH_FFI_BUILD)
    #define RSH_FFI_API __declspec(dllexport)
  #else
    #define RSH_FFI_API __declspec(dllimport)
  #endif
#else
  #define RSH_FFI_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

enum {
  RSH_FFI_ABI_VERSION = 1,
  RSH_FFI_STATUS_PASS = 0,
  RSH_FFI_STATUS_CONTRACT_FAIL = 1,
  RSH_FFI_STATUS_REJECTED = 2,
  RSH_FFI_STATUS_PANIC = 3
};

typedef struct RshConfigV1 {
  uint32_t struct_size;
  uint32_t abi_version;
  uint64_t samples;
  double s0;
  double s1;
  double kappa_fraction;
  double tau_floor;
  double tau_amplitude;
} RshConfigV1;

typedef struct RshSummaryV1 {
  uint32_t struct_size;
  uint32_t abi_version;
  uint32_t pass_all;
  uint32_t reserved;
  uint64_t samples;
  double centre_error;
  double max_kappa;
  double kappa_bound;
  double min_tau;
  double max_tau;
  double max_frame_norm_error;
  double max_frame_orthogonality_error;
  double path_length;
  double entry[3];
  double centre[3];
  double exit[3];
  uint8_t receipt[65];
} RshSummaryV1;

typedef struct RshOwnedBytesV1 {
  const uint8_t *ptr;
  size_t len;
  void *handle;
} RshOwnedBytesV1;

typedef struct RshSchedulePointV1 {
  double p;
  double s;
  double kappa;
  double tau;
} RshSchedulePointV1;

typedef struct RshOwnedScheduleV1 {
  const RshSchedulePointV1 *ptr;
  size_t len;
  void *handle;
} RshOwnedScheduleV1;

RSH_FFI_API uint32_t rsh_ffi_abi_version(void);
RSH_FFI_API size_t rsh_ffi_config_size(void);
RSH_FFI_API size_t rsh_ffi_summary_size(void);
RSH_FFI_API size_t rsh_ffi_schedule_point_size(void);
RSH_FFI_API double rsh_ffi_psi(void);
RSH_FFI_API double rsh_ffi_kappa_bound(void);
RSH_FFI_API const char *rsh_ffi_last_error(void);

RSH_FFI_API int32_t rsh_ffi_verify(
  const RshConfigV1 *config,
  RshSummaryV1 *summary,
  RshOwnedBytesV1 *json
);

RSH_FFI_API int32_t rsh_ffi_schedule(
  const RshConfigV1 *config,
  RshOwnedScheduleV1 *schedule
);

RSH_FFI_API void rsh_ffi_free_bytes(RshOwnedBytesV1 *value);
RSH_FFI_API void rsh_ffi_free_schedule(RshOwnedScheduleV1 *value);

#ifdef __cplusplus
}

static_assert(sizeof(RshConfigV1) == 56, "RSH ABI v1 config layout changed");
static_assert(sizeof(RshSummaryV1) == 232, "RSH ABI v1 summary layout changed");
static_assert(sizeof(RshSchedulePointV1) == 32, "RSH ABI v1 schedule layout changed");
#endif

#endif
