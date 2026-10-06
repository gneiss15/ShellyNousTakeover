// LoaderWriter.c, Version: 1.01
#include "LoaderWriter.h"
#include <string.h>
#include "esp_flash.h"
#include "esp_flash_internal.h"
static uint8_t Original[NOUS_LOADER_SPAN];
static uint8_t Metadata[0x3000];
static uint8_t Verify[4096];
static bool Matches(const uint8_t * Image)
 {
  for( unsigned Offset = 0; Offset < NOUS_LOADER_SPAN; Offset += sizeof(Verify) )
    if( esp_flash_read(NULL, Verify, NOUS_LOADER_OFFSET + Offset, sizeof(Verify)) != ESP_OK ||
        memcmp(Verify, Image + Offset, sizeof(Verify)) ) return false;
  return true;
 }
static bool Invariants(void)
 {
  // The partition table and both OTA selection sectors must remain unchanged.
  const unsigned Addresses[] = { 0x8000, 0xE000, 0xF000 };
  for( unsigned Index = 0; Index < 3; ++Index )
    if( esp_flash_read(NULL, Verify, Addresses[Index], sizeof(Verify)) != ESP_OK ||
        memcmp(Verify, Metadata + Index * sizeof(Verify), sizeof(Verify)) ) return false;
  return true;
 }
static bool Replace(const uint8_t * Image)
 {
  if( esp_flash_erase_region(NULL, NOUS_LOADER_OFFSET, NOUS_LOADER_SPAN) != ESP_OK ) return false;
  for( unsigned Offset = 0; Offset < NOUS_LOADER_SPAN; Offset += sizeof(Verify) )
   {
    // Embedded candidate bytes live in flash; write from RAM while cache is off.
    memcpy(Verify, Image + Offset, sizeof(Verify));
    if( esp_flash_write(NULL, Verify, NOUS_LOADER_OFFSET + Offset, sizeof(Verify)) != ESP_OK ) return false;
   }
  return Matches(Image);
 }
TNousLoaderResult NousWriteLoader(const uint8_t * Expected, const uint8_t * Target,
  bool OriginalApproved, bool RescueVerified)
 {
  TNousLoaderResult Result = { .ProtectionRestored = true, .DoNotRestart = true };
  if( !Expected || !Target || !OriginalApproved || !RescueVerified ) return Result;
  // Copy the concrete original bytes, not a vendor payload supplied by the PC.
  if( esp_flash_read(NULL, Original, NOUS_LOADER_OFFSET, sizeof(Original)) != ESP_OK ||
      memcmp(Original, Expected, sizeof(Original)) ) return Result;
  const unsigned Addresses[] = { 0x8000, 0xE000, 0xF000 };
  for( unsigned Index = 0; Index < 3; ++Index )
    if( esp_flash_read(NULL, Metadata + Index * sizeof(Verify), Addresses[Index], sizeof(Verify)) != ESP_OK ) return Result;
  if( !Matches(Original) || !Invariants() ) return Result;
  if( !memcmp(Original, Target, sizeof(Original)) )
   {
    Result.TargetVerified = Result.InvariantsVerified = true;
    Result.DoNotRestart = false;
    return Result;
   }
  if( esp_flash_set_dangerous_write_protection(esp_flash_default_chip, false) != ESP_OK )
   {
    Result.ProtectionRestored = esp_flash_set_dangerous_write_protection(esp_flash_default_chip, true) == ESP_OK;
    return Result;
   }
  Result.TargetVerified = Replace(Target);
  // Restore only while the preserved layout and boot selection are still known.
  if( !Result.TargetVerified && Invariants() ) Result.RollbackVerified = Replace(Original);
  Result.ProtectionRestored = esp_flash_set_dangerous_write_protection(esp_flash_default_chip, true) == ESP_OK;
  Result.InvariantsVerified = Invariants();
  Result.DoNotRestart = !(Result.TargetVerified || Result.RollbackVerified) ||
    !Result.ProtectionRestored || !Result.InvariantsVerified;
  return Result;
 }
