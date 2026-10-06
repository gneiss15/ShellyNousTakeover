// BootState.h, Version: 1.00
#ifndef SHELLY_READOUT_BOOT_STATE_H
#define SHELLY_READOUT_BOOT_STATE_H

#include <stdbool.h>
#include <stdint.h>

#define BOOT_STATE_SECTOR_SIZE 4096

typedef struct
 {
  uint32_t Sequence;
  uint8_t ActiveSlot;
  uint8_t ReserveSlot;
  uint8_t BootAttempts;
  uint8_t Committed;
  uint8_t Mfs;
  bool Valid;
 } TBootState;

void DecodeBootState(const uint8_t * Sector, TBootState * State);
int SelectBootState(const uint8_t * Sectors);
bool PrepareStockBootState(const uint8_t * Sectors, uint8_t * NewSector,
  unsigned * TargetSector);

#endif
