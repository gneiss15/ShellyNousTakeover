// Migration.c, Version: 1.00
#include "Migration.h"
#include <string.h>
#include "esp_flash.h"
#include "esp_flash_internal.h"
#include "mbedtls/sha256.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

typedef struct
 {
  uint32_t Magic, FlashSize, RescueSize;
  uint8_t TargetHash[32], RescueHash[32], ProtectedHash[3][32];
  uint8_t Table[4096], State[8192], SelfHash[32];
 } TCheckpoint;
_Static_assert(sizeof(TCheckpoint) == 12492, "Checkpoint format must match the host verifier");
static TCheckpoint Saved, Other;
static uint8_t Buffer[4096];
static bool Uncertain;
static const char * Error = "";
static const char * Step = "NotStaged";
static const uint32_t ProtectedOffsets[3] = { 0, 0x13000, MIG_FACTORY_OFFSET };
static const uint32_t ProtectedSizes[3] = { 0x10000, MIG_RESCUE_OFFSET - 0x13000, MIG_FLASH_SIZE - MIG_FACTORY_OFFSET };

const char * MigrationError(void) { return Error; }
const char * MigrationStep(void) { return Step; }
bool MigrationUncertain(void) { return Uncertain; }
static bool Fail(const char * Message) { Error = Message; return false; }
static bool HashMemory(const void * Data, uint32_t Size, uint8_t * Hash)
 {
  return mbedtls_sha256(Data, Size, Hash, 0) == 0;
 }
static bool HashFlash(uint32_t Offset, uint32_t Size, uint8_t * Hash)
 {
  mbedtls_sha256_context Context;
  mbedtls_sha256_init(&Context);
  int Result = mbedtls_sha256_starts(&Context, 0);
  while( Size && !Result )
   {
    unsigned Count = Size < sizeof(Buffer) ? Size : sizeof(Buffer);
    if( esp_flash_read(NULL, Buffer, Offset, Count) != ESP_OK ) { Result = -1; break; }
    Result = mbedtls_sha256_update(&Context, Buffer, Count);
    Offset += Count; Size -= Count;
    vTaskDelay(1);
   }
  if( !Result ) Result = mbedtls_sha256_finish(&Context, Hash);
  mbedtls_sha256_free(&Context);
  return Result == 0;
 }
static bool Matches(uint32_t Offset, const void * Data, uint32_t Size)
 {
  const uint8_t * Expected = Data;
  while( Size )
   {
    unsigned Count = Size < sizeof(Buffer) ? Size : sizeof(Buffer);
    if( esp_flash_read(NULL, Buffer, Offset, Count) != ESP_OK || memcmp(Buffer, Expected, Count) ) return false;
    Offset += Count; Expected += Count; Size -= Count;
    vTaskDelay(1);
   }
  return true;
 }
static bool Erased(uint32_t Offset, uint32_t Size)
 {
  while( Size )
   {
    unsigned Count = Size < sizeof(Buffer) ? Size : sizeof(Buffer);
    if( esp_flash_read(NULL, Buffer, Offset, Count) != ESP_OK ) return false;
    for( unsigned I = 0; I < Count; ++I ) if( Buffer[I] != 255 ) return false;
    Offset += Count; Size -= Count;
    vTaskDelay(1);
   }
  return true;
 }
static bool Valid(TCheckpoint * C, const uint8_t * NewTable)
 {
  uint8_t Hash[32], Expected[32];
  memcpy(Expected, C->SelfHash, 32); memset(C->SelfHash, 0, 32);
  const bool Ok = HashMemory(C, sizeof(*C), Hash) && !memcmp(Hash, Expected, 32);
  memcpy(C->SelfHash, Expected, 32);
  return Ok && C->Magic == 0x534D4731 && C->FlashSize == MIG_FLASH_SIZE && C->RescueSize && C->RescueSize <= MIG_RESCUE_SIZE &&
    HashMemory(NewTable, 4096, Hash) && !memcmp(Hash, C->TargetHash, 32);
 }
static bool Load(const uint8_t * NewTable)
 {
  if( esp_flash_read(NULL, &Saved, MIG_CHECKPOINT_OFFSET, sizeof(Saved)) != ESP_OK ||
      esp_flash_read(NULL, &Other, MIG_CHECKPOINT_OFFSET + MIG_CHECKPOINT_SIZE, sizeof(Other)) != ESP_OK ||
      memcmp(&Saved, &Other, sizeof(Saved)) || !Valid(&Saved, NewTable) )
    return Fail("Migration checkpoint missing, damaged or inconsistent");
  return true;
 }
bool MigrationCheckpointPresent(void)
 {
  // Non-erased or unreadable metadata blocks destructive updates, even if corrupt.
  return !Erased(MIG_CHECKPOINT_OFFSET, 2 * MIG_CHECKPOINT_SIZE);
 }
static bool Protected(void)
 {
  uint8_t Hash[32];
  for( unsigned I = 0; I < 3; ++I )
    if( !HashFlash(ProtectedOffsets[I], ProtectedSizes[I], Hash) || memcmp(Hash, Saved.ProtectedHash[I], 32) )
      return Fail("Preserved loader/stock/NVS/FS/Main/factory data differ from baseline");
  return true;
 }
static bool Staged(void)
 {
  uint8_t Hash[32];
  return HashFlash(MIG_RESCUE_OFFSET, Saved.RescueSize, Hash) && !memcmp(Hash, Saved.RescueHash, 32) &&
    Erased(MIG_RESCUE_OFFSET + Saved.RescueSize, MIG_RESCUE_SIZE - Saved.RescueSize) &&
    Erased(MIG_NVS_OFFSET, MIG_NVS_SIZE) && Erased(MIG_OTA_OFFSET, 8192);
 }
static bool BeginWrite(void)
 {
  Uncertain = true;
  if( esp_flash_set_dangerous_write_protection(esp_flash_default_chip, false) == ESP_OK ) return true;
  Uncertain = esp_flash_set_dangerous_write_protection(esp_flash_default_chip, true) != ESP_OK;
  return Fail("Cannot disable flash protection");
 }
static bool EndWrite(bool Verified)
 {
  const bool ProtectedAgain = esp_flash_set_dangerous_write_protection(esp_flash_default_chip, true) == ESP_OK;
  Uncertain = !Verified || !ProtectedAgain;
  return Verified && ProtectedAgain ? true : Fail("Write/readback/protection uncertain; restart and writes locked");
 }
static bool Replace(uint32_t Offset, uint32_t Span, const void * Data, uint32_t Size)
 {
  if( esp_flash_erase_region(NULL, Offset, Span) != ESP_OK ) return false;
  // Bounded chunks keep the service responsive to RTOS/watchdog tasks.
  const uint8_t * Bytes = Data;
  for( uint32_t I = 0; I < Size; )
   {
    uint32_t Count = Size - I < 4096 ? Size - I : 4096;
    if( esp_flash_write(NULL, Bytes + I, Offset + I, Count) != ESP_OK ) return false;
    I += Count; vTaskDelay(1);
   }
  return (!Size || Matches(Offset, Data, Size)) && Erased(Offset + Size, Span - Size);
 }

bool MigrationStage(const uint8_t * Rescue, uint32_t Size, const uint8_t * OldTable,
  const uint8_t * NewTable, const uint8_t * Loader)
 {
  Error = "";
  uint32_t FlashSize = 0;
  if( Uncertain || !Size || Size > MIG_RESCUE_SIZE || esp_flash_get_size(NULL, &FlashSize) != ESP_OK || FlashSize != MIG_FLASH_SIZE ||
      !Matches(0, Loader, 0x6000) || !Matches(0x10000, OldTable, 4096) )
    return Fail("Staging hardware, loader or original-table guard failed");
  if( MigrationCheckpointPresent() )
   {
    if( !Load(NewTable) || !Protected() || !Matches(0x11000, Saved.State, 8192) ) return false;
    uint8_t Hash[32];
    if( !HashMemory(Rescue, Size, Hash) || Saved.RescueSize != Size || memcmp(Hash, Saved.RescueHash, 32) )
      return Fail("Embedded Rescue differs from existing checkpoint");
   }
  else
   {
    memset(&Saved, 0, sizeof(Saved));
    Saved.Magic = 0x534D4731; Saved.FlashSize = MIG_FLASH_SIZE; Saved.RescueSize = Size;
    memcpy(Saved.Table, OldTable, 4096);
    if( esp_flash_read(NULL, Saved.State, 0x11000, 8192) != ESP_OK || !HashMemory(NewTable, 4096, Saved.TargetHash) ||
        !HashMemory(Rescue, Size, Saved.RescueHash) ) return Fail("Cannot capture baseline");
    for( unsigned I = 0; I < 3; ++I )
      if( !HashFlash(ProtectedOffsets[I], ProtectedSizes[I], Saved.ProtectedHash[I]) ) return Fail("Cannot hash baseline");
    if( !HashMemory(&Saved, sizeof(Saved), Saved.SelfHash) ) return Fail("Cannot seal baseline");
   }
  if( !Protected() || !Matches(0x11000, Saved.State, 8192) || !BeginWrite() ) return false;
  bool Ok = Replace(MIG_CHECKPOINT_OFFSET, MIG_CHECKPOINT_SIZE, &Saved, sizeof(Saved)) &&
    Replace(MIG_CHECKPOINT_OFFSET + MIG_CHECKPOINT_SIZE, MIG_CHECKPOINT_SIZE, &Saved, sizeof(Saved));
  if( Ok ) { Step = "BaselineCopiesVerified"; Ok = Replace(MIG_RESCUE_OFFSET, MIG_RESCUE_SIZE, Rescue, Size); }
  if( Ok ) { Step = "RescueReadbackVerified"; Ok = Replace(MIG_NVS_OFFSET, MIG_NVS_SIZE, NULL, 0) && Replace(MIG_OTA_OFFSET, 8192, NULL, 0); }
  Ok = Ok && Staged() && Protected() && Matches(0x10000, Saved.Table, 4096) && Matches(0x11000, Saved.State, 8192);
  if( !EndWrite(Ok) ) return false;
  Step = "StagingVerified"; return true;
 }

bool MigrationCommit(const uint8_t * NewTable)
 {
  Error = "";
  if( Uncertain || !Load(NewTable) || !Protected() || !Matches(0x10000, Saved.Table, 4096) ||
      !Matches(0x11000, Saved.State, 8192) || !Staged() ) return Fail("Commit prerequisites failed; no table write");
  if( !BeginWrite() ) return false;
  const bool Written = Replace(0x10000, 4096, NewTable, 4096);
  const bool Restored = Written ? false : Replace(0x10000, 4096, Saved.Table, 4096);
  const bool Invariants = Protected() && Matches(0x11000, Saved.State, 8192) && Staged();
  if( !EndWrite((Written || Restored) && Invariants) ) return false;
  if( !Written ) return Fail("Table write failed; original table restored and verified");
  Step = "TargetTableVerifiedRestartRequired"; return true;
 }
bool MigrationRestartReady(const uint8_t * NewTable)
 {
  if( Uncertain || !Load(NewTable) || !Matches(0x10000, NewTable, 4096) || !Protected() ||
      !Matches(0x11000, Saved.State, 8192) || !Staged() ) return Fail("Rescue restart verification failed");
  return true;
 }
bool MigrationRollbackReady(const uint8_t * NewTable)
 {
  uint8_t Hash[32];
  if( Uncertain || !Load(NewTable) || !Matches(0x10000, NewTable, 4096) || !Protected() ||
      !Matches(0x11000, Saved.State, 8192) || !HashFlash(MIG_RESCUE_OFFSET, Saved.RescueSize, Hash) || memcmp(Hash, Saved.RescueHash, 32) )
    return Fail("Rollback requires intact original apps/data, unchanged read-only SH0S and Rescue");
  return true;
 }
bool MigrationRollback(const uint8_t * NewTable)
 {
  Error = "";
  if( !MigrationRollbackReady(NewTable) || !BeginWrite() ) return false;
  // Retired SH0S is read-only in the target SDK. Verify it; never rewrite unchanged data.
  // The original table is the only rollback write. Never invoke the SDK OTA selector.
  const bool Written = Matches(0x11000, Saved.State, 8192) && Replace(0x10000, 4096, Saved.Table, 4096);
  const bool RestoredTarget = Written ? false : Replace(0x10000, 4096, NewTable, 4096);
  if( !EndWrite((Written || RestoredTarget) && Protected()) ) return false;
  if( !Written ) return Fail("Rollback failed; target table restored; verify/retry before restart");
  Step = "OriginalTableAndSH0SVerifiedRestartRequired"; return true;
 }
bool MigrationRollbackRestartReady(const uint8_t * NewTable)
 {
  if( Uncertain || !Load(NewTable) || !Protected() || !Matches(0x10000, Saved.Table, 4096) || !Matches(0x11000, Saved.State, 8192) )
    return Fail("Original-layout restart verification failed");
  return true;
 }

// Only the old-layout app calls this after a verified return under the original table.
bool MigrationReleaseCheckpoint(const uint8_t * NewTable)
 {
  Error = "";
  if( !MigrationRollbackRestartReady(NewTable) || !BeginWrite() ) return false;
  const bool Ok = Replace(MIG_CHECKPOINT_OFFSET, 2 * MIG_CHECKPOINT_SIZE, NULL, 0) && Protected() &&
    Matches(0x10000, Saved.Table, 4096) && Matches(0x11000, Saved.State, 8192);
  if( !EndWrite(Ok) ) return false;
  Step = "OriginalLayoutVerifiedCheckpointReleased"; return true;
 }
