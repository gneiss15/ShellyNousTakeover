// StockRequest.c, Version: 1.00
#include <string.h>
#include "bootloader_flash_priv.h"
#include "BootState.h"
#include "StockRequest.h"

static uint8_t Verify[512] __attribute__((aligned(4)));
static uint8_t NewSector[BOOT_STATE_SECTOR_SIZE] __attribute__((aligned(4)));

bool EnsureStockBootState(const uint8_t * Snapshot)
 {
  const int Selected = SelectBootState(Snapshot);
  if( Selected < 0 )
    return false;
  TBootState State;
  DecodeBootState(Snapshot + Selected * BOOT_STATE_SECTOR_SIZE, &State);
  if( State.ActiveSlot == 0 && State.ReserveSlot == 1 && State.Committed == 1 &&
      (Snapshot[Selected * BOOT_STATE_SECTOR_SIZE + 0x1D0] & 0x0C) == 0 )
    return true;
  unsigned Target;
  if( !PrepareStockBootState(Snapshot, NewSector, &Target) )
    return false;
  // Preserve the winning copy and refuse a changed snapshot before writing.
  for( unsigned Offset = 0; Offset < 2 * BOOT_STATE_SECTOR_SIZE; Offset += sizeof(Verify) )
    if( bootloader_flash_read(0x11000 + Offset, Verify, sizeof(Verify), false) != ESP_OK ||
        memcmp(Snapshot + Offset, Verify, sizeof(Verify)) != 0 )
      return false;
  const uint32_t Address = 0x11000 + Target * BOOT_STATE_SECTOR_SIZE;
  if( bootloader_flash_erase_sector(Address / BOOT_STATE_SECTOR_SIZE) != ESP_OK ||
      bootloader_flash_write(Address, NewSector, sizeof(NewSector), false) != ESP_OK )
    return false;
  for( unsigned Offset = 0; Offset < sizeof(NewSector); Offset += sizeof(Verify) )
    if( bootloader_flash_read(Address + Offset, Verify, sizeof(Verify), false) != ESP_OK ||
        memcmp(NewSector + Offset, Verify, sizeof(Verify)) != 0 )
      return false;
  DecodeBootState(NewSector, &State);
  return State.Valid && State.ActiveSlot == 0 && State.ReserveSlot == 1 &&
    State.Committed == 1 && State.BootAttempts == 0 && State.Mfs == 0;
 }
