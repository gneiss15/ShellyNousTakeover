// LoaderWriter.h, Version: 1.01
#ifndef READOUT_LOADER_WRITER_H
#define READOUT_LOADER_WRITER_H
#include <stdbool.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define LOADER_WRITE_SPAN 0x6000

typedef struct
 {
  bool TargetVerified;
  bool RollbackVerified;
  bool ProtectionRestored;
  bool InvariantsVerified;
  bool DoNotRestart;
 } TLoaderWriteResult;

bool LoaderMatches(const uint8_t * Image);
TLoaderWriteResult WriteBoundedLoader(const uint8_t * Expected,
  const uint8_t * Target, bool Retry);
#ifdef __cplusplus
}
#endif
#endif
