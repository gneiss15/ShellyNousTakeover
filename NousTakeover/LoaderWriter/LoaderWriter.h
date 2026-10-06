// LoaderWriter.h, Version: 1.00
#pragma once
#include <stdbool.h>
#include <stdint.h>
#define NOUS_LOADER_OFFSET 0x1000u
#define NOUS_LOADER_SPAN 0x7000u
typedef struct
 {
  bool TargetVerified, RollbackVerified, ProtectionRestored, InvariantsVerified;
  bool DoNotRestart;
 } TNousLoaderResult;
// Both identities and Rescue must be checked by the platform before calling.
TNousLoaderResult NousWriteLoader(const uint8_t * Expected, const uint8_t * Target,
  bool OriginalApproved, bool RescueVerified);
