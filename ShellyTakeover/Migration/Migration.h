// Migration.h, Version: 1.00
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "Geometry.h"
#ifdef __cplusplus
extern "C" {
#endif
// Calls are serialized by the app's HTTP service; no arbitrary write address API.
const char * MigrationError(void);
const char * MigrationStep(void);
bool MigrationUncertain(void);
bool MigrationCheckpointPresent(void);
bool MigrationStage(const uint8_t * Rescue, uint32_t Size, const uint8_t * OldTable,
  const uint8_t * NewTable, const uint8_t * Loader);
bool MigrationReleaseCheckpoint(const uint8_t * NewTable);
bool MigrationCommit(const uint8_t * NewTable);
bool MigrationRestartReady(const uint8_t * NewTable);
bool MigrationRollbackReady(const uint8_t * NewTable);
bool MigrationRollback(const uint8_t * NewTable);
bool MigrationRollbackRestartReady(const uint8_t * NewTable);
#ifdef __cplusplus
}
#endif
