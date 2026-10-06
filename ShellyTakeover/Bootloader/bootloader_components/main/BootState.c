// BootState.c, Version: 1.01
#include "BootState.h"
#include <string.h>

static uint32_t Read32(const uint8_t * Bytes)
 {
  return (uint32_t)Bytes[0] | ((uint32_t)Bytes[1] << 8) |
    ((uint32_t)Bytes[2] << 16) | ((uint32_t)Bytes[3] << 24);
 }

static void Write32(uint8_t * Bytes, uint32_t Value)
 {
  for( unsigned Index = 0; Index < 4; ++Index )
    Bytes[Index] = (uint8_t)(Value >> (8 * Index));
 }

// Match esp_rom_crc32_le chaining; verified against all supplied SH0S dumps.
static uint32_t Crc32(uint32_t Seed, const uint8_t * Bytes, unsigned Size)
 {
  uint32_t Crc = ~Seed;
  for( unsigned Index = 0; Index < Size; ++Index )
   {
    Crc ^= Bytes[Index];
    for( unsigned Bit = 0; Bit < 8; ++Bit )
      Crc = (Crc >> 1) ^ ((Crc & 1) ? 0xEDB88320u : 0);
   }
  return ~Crc;
 }

static uint32_t HeaderCrc(const uint8_t * Sector)
 {
  static const uint8_t Zero[4] = { 0 };
  return Crc32(Crc32(UINT32_MAX, Sector, 0x1C), Zero, sizeof(Zero));
 }

void DecodeBootState(const uint8_t * Sector, TBootState * State)
 {
  State->Sequence = Read32(Sector);
  State->ReserveSlot = Sector[0x1D1] & 15;
  State->ActiveSlot = Sector[0x1D0] >> 4;
  State->BootAttempts = (Sector[0x1D0] >> 1) & 1;
  State->Committed = Sector[0x1D0] & 1;
  State->Mfs = Sector[0x1D1] >> 4;
  State->Valid = memcmp(Sector + 8, "SH0S", 4) == 0 &&
    State->Sequence != 0 && State->Sequence == Read32(Sector + 0x0C) &&
    Read32(Sector + 0x1C) == HeaderCrc(Sector) &&
    Read32(Sector + 0x1FC) == Crc32(UINT32_MAX, Sector, 0x1FC);
 }

int SelectBootState(const uint8_t * Sectors)
 {
  TBootState State[2];
  DecodeBootState(Sectors, &State[0]);
  DecodeBootState(Sectors + BOOT_STATE_SECTOR_SIZE, &State[1]);
  if( !State[0].Valid && !State[1].Valid )
    return -1;
  if( !State[0].Valid )
    return 1;
  if( !State[1].Valid )
    return 0;
  if( State[0].Sequence == State[1].Sequence &&
      memcmp(Sectors, Sectors + BOOT_STATE_SECTOR_SIZE, 0x200) != 0 )
    return -1;
  return State[0].Sequence >= State[1].Sequence ? 0 : 1;
 }

bool PrepareStockBootState(const uint8_t * Sectors, uint8_t * NewSector,
  unsigned * TargetSector)
 {
  const int Selected = SelectBootState(Sectors);
  if( Selected < 0 )
    return false;
  TBootState State;
  const uint8_t * Source = Sectors + Selected * BOOT_STATE_SECTOR_SIZE;
  DecodeBootState(Source, &State);
  // Only the confirmed app_1 -> stock app_0 direction is permitted.
  if( State.ActiveSlot != 1 || State.ReserveSlot != 0 ||
      State.Committed > 1 || (Source[0x1D0] & 0x0C) != 0 ||
      State.Sequence == UINT32_MAX )
    return false;
  memcpy(NewSector, Source, BOOT_STATE_SECTOR_SIZE);
  Write32(NewSector, State.Sequence + 1);
  Write32(NewSector + 0x0C, State.Sequence + 1);
  NewSector[0x1D0] = 0x01; // active=0, committed=1, boot attempt=0
  NewSector[0x1D1] = 0x01; // reserve=1, mfs=0
  Write32(NewSector + 0x1C, HeaderCrc(NewSector));
  Write32(NewSector + 0x1FC, Crc32(UINT32_MAX, NewSector, 0x1FC));
  DecodeBootState(NewSector, &State);
  *TargetSector = (unsigned)(1 - Selected);
  return State.Valid;
 }
