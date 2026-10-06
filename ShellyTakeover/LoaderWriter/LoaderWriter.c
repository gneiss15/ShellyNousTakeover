// LoaderWriter.c, Version: 1.00
#include <string.h>
#include "esp_flash.h"
#include "esp_flash_internal.h"
#include "LoaderWriter.h"

static uint8_t Verify[4096];
static uint8_t SavedTable[4096];
static uint8_t SavedState[8192];
static bool SnapshotValid;

bool LoaderMatches(const uint8_t * Image)
 {
  for( unsigned Offset = 0; Offset < LOADER_WRITE_SPAN; Offset += sizeof(Verify) )
    if( esp_flash_read(NULL, Verify, Offset, sizeof(Verify)) != ESP_OK ||
        memcmp(Image + Offset, Verify, sizeof(Verify)) != 0 )
      return false;
  return true;
 }

static bool InvariantsMatch(void)
 {
  if( !SnapshotValid || esp_flash_read(NULL, Verify, 0x10000, 4096) != ESP_OK ||
      memcmp(Verify, SavedTable, 4096) != 0 )
    return false;
  for( unsigned Offset = 0; Offset < sizeof(SavedState); Offset += sizeof(Verify) )
    if( esp_flash_read(NULL, Verify, 0x11000 + Offset, sizeof(Verify)) != ESP_OK ||
        memcmp(Verify, SavedState + Offset, sizeof(Verify)) != 0 )
      return false;
  return true;
 }

static bool ReplaceLoader(const uint8_t * Image)
 {
  return esp_flash_erase_region(NULL, 0, LOADER_WRITE_SPAN) == ESP_OK &&
    esp_flash_write(NULL, Image, 0, LOADER_WRITE_SPAN) == ESP_OK && LoaderMatches(Image);
 }

TLoaderWriteResult WriteBoundedLoader(const uint8_t * Expected,
  const uint8_t * Target, bool Retry)
 {
  TLoaderWriteResult Result = { 0 };
  Result.ProtectionRestored = true;
  // An explicit recovery retry may repair an unknown/partially written loader,
  // but only in this process with the original table/SH0S snapshot still valid.
  if( Retry )
   {
    Result.DoNotRestart = true;
    if( !InvariantsMatch() ) return Result;
   }
  else
   {
    if( !LoaderMatches(Expected) ) return Result;
    SnapshotValid = false;
    if( esp_flash_read(NULL, SavedTable, 0x10000, sizeof(SavedTable)) != ESP_OK ||
        esp_flash_read(NULL, SavedState, 0x11000, sizeof(SavedState)) != ESP_OK )
      return Result;
    SnapshotValid = true;
    if( !LoaderMatches(Expected) || !InvariantsMatch() ) return Result;
   }
  if( esp_flash_set_dangerous_write_protection(esp_flash_default_chip, false) != ESP_OK )
   {
    Result.ProtectionRestored = esp_flash_set_dangerous_write_protection(esp_flash_default_chip, true) == ESP_OK;
    Result.DoNotRestart = Retry || !Result.ProtectionRestored;
    return Result;
   }
  Result.TargetVerified = ReplaceLoader(Target);
  // Restore the exact known pre-write image after a failed normal operation.
  // Keep the checkpoint and block all restart/other-write actions if uncertain.
  if( !Result.TargetVerified && !Retry )
    Result.RollbackVerified = ReplaceLoader(Expected);
  Result.ProtectionRestored = esp_flash_set_dangerous_write_protection(esp_flash_default_chip, true) == ESP_OK;
  Result.InvariantsVerified = InvariantsMatch();
  Result.DoNotRestart = !(Result.TargetVerified || Result.RollbackVerified) ||
    !Result.ProtectionRestored || !Result.InvariantsVerified;
  return Result;
 }
