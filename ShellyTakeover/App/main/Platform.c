// Platform.c, Version: 1.02
#include "Platform.h"
#include "Migration.h"
#include "LoaderWriter.h"
#include "BootState.h"
#include "PayloadIdentity.h"
#include "esp_flash.h"
#include "esp_chip_info.h"
#include "esp_secure_boot.h"
#include "esp_flash_encrypt.h"
#include "esp_ota_ops.h"
#include "mbedtls/sha256.h"
#include <string.h>
#include <stdio.h>
extern const uint8_t OldTable[] asm("_binary_OldTable_bin_start");
extern const uint8_t NewTable[] asm("_binary_NewTable_bin_start");
extern const uint8_t CandidateLoader[] asm("_binary_CandidateLoader_bin_start");
extern const uint8_t CandidateLoaderEnd[] asm("_binary_CandidateLoader_bin_end");
extern const uint8_t RescuePayload[] asm("_binary_Rescue_bin_start");
extern const uint8_t RescuePayloadEnd[] asm("_binary_Rescue_bin_end");
static uint8_t OriginalLoader[LOADER_WRITE_SPAN];
static uint8_t Buffer[4096];
static uint8_t BootSectors[8192], NewSector[4096];
static uint8_t PreservedHash[3][32];
static const uint32_t PreservedOffset[] = {0x6000, 0x13000, 0x7F0000};
static const uint32_t PreservedSize[] = {0xA000, 0x62D000, 0x10000};
static bool LoaderChanged, LoaderUncertain, BaselineValid;
static const char * LastError = "";
static bool HashFlash(uint32_t Offset, uint32_t Size, uint8_t Hash[32])
 {
  mbedtls_sha256_context Context;
  mbedtls_sha256_init(&Context);
  bool Ok = mbedtls_sha256_starts(&Context,0)==0;
  while( Size && Ok )
   {
    const uint32_t Count = Size < sizeof(Buffer) ? Size : sizeof(Buffer);
    Ok = esp_flash_read(NULL, Buffer, Offset, Count)==ESP_OK && mbedtls_sha256_update(&Context,Buffer,Count)==0;
    Offset+=Count;Size-=Count;
   }
  if( Ok ) Ok=mbedtls_sha256_finish(&Context,Hash)==0;
  mbedtls_sha256_free(&Context);
  return Ok;
 }
static bool DigestMatches(uint32_t Offset, uint32_t Size, const char * Expected)
 {
  uint8_t Hash[32]; char Hex[65];
  if( !HashFlash(Offset,Size,Hash) ) return false;
  for(unsigned I=0;I<32;I++) snprintf(Hex+I*2,3,"%02x",Hash[I]);
  return strcmp(Hex,Expected)==0;
 }
static bool Matches(uint32_t Offset,const uint8_t * Data,uint32_t Size)
 {
  for(uint32_t I=0;I<Size;)
   {
    uint32_t Count=Size-I<sizeof(Buffer)?Size-I:sizeof(Buffer);
    if(esp_flash_read(NULL,Buffer,Offset+I,Count)!=ESP_OK || memcmp(Buffer,Data+I,Count)) return false;
    I+=Count;
   }
  return true;
 }
static bool Erased(uint32_t Offset,uint32_t Size)
 {
  for(uint32_t I=0;I<Size;)
   {
    uint32_t Count=Size-I<sizeof(Buffer)?Size-I:sizeof(Buffer);
    if(esp_flash_read(NULL,Buffer,Offset+I,Count)!=ESP_OK) return false;
    for(uint32_t J=0;J<Count;J++) if(Buffer[J]!=255) return false;
    I+=Count;
   }
  return true;
 }
static bool Preserved(void)
 {
  if(!BaselineValid) return false;
  uint8_t Hash[32];
  for(unsigned I=0;I<3;I++)
    if(!HashFlash(PreservedOffset[I],PreservedSize[I],Hash)||memcmp(Hash,PreservedHash[I],32)) return false;
  return true;
 }
static const char * Guard(void)
 {
  uint32_t Size=0; esp_chip_info_t Chip={0};esp_chip_info(&Chip);
  const esp_partition_t * Running=esp_ota_get_running_partition();
  if(esp_flash_get_physical_size(NULL,&Size)!=ESP_OK||Size!=0x800000||Chip.model!=CHIP_ESP32C3||Chip.revision!=4||
    esp_secure_boot_enabled()||esp_flash_encryption_enabled()||!Running||Running->type!=ESP_PARTITION_TYPE_APP||
    Running->subtype!=ESP_PARTITION_SUBTYPE_APP_OTA_1||Running->address!=0x3A0000||Running->size!=0x2A0000)
    return "Unsupported chip/security/flash/running slot";
  if(CandidateLoaderEnd-CandidateLoader!=LOADER_WRITE_SPAN||RescuePayloadEnd-RescuePayload!=TAKEOVER_RESCUE_SIZE)
    return "Embedded payload lengths differ";
  uint8_t Hash[32];
  if(mbedtls_sha256(RescuePayload,TAKEOVER_RESCUE_SIZE,Hash,0)!=0||memcmp(Hash,TakeoverRescueHash,32)||
    mbedtls_sha256(CandidateLoader,LOADER_WRITE_SPAN,Hash,0)!=0||memcmp(Hash,TakeoverLoaderHash,32))
    return "Embedded payload digest differs";
  if(!Matches(0x10000,OldTable,4096)) return "Unsupported original partition table";
  if(!DigestMatches(0x20000,2708368,"80ce0363774d9904464e5e11c0b2740e5ba221a0104615a841213a83129e6514") &&
    !DigestMatches(0x20000,2712352,"82f71b5db76025617ef0f12966dfcd9b0c7af765adf9a114615dd32b41efaeef"))
    return "Stock app is not a supported 2.0.0/2.0.1 image";
  if(!LoaderMatches(CandidateLoader) &&
    (!DigestMatches(0,20992,"8df59da4cb489ce7cb95010966c7ad5ba67c6745cf0b76eac70b9ea4692f9979")||!Erased(20992,LOADER_WRITE_SPAN-20992)))
    return "Unknown bootloader; no write";
  unsigned Target;
  if(esp_flash_read(NULL,BootSectors,0x11000,sizeof(BootSectors))!=ESP_OK||!PrepareStockBootState(BootSectors,NewSector,&Target))
    return "SH0S does not permit verified Stock recovery";
  if(MigrationCheckpointPresent()||!Erased(0x640000,0x1B0000)) return "Not a fresh supported migration; high area is not erased";
  if(esp_flash_read(NULL,OriginalLoader,0,sizeof(OriginalLoader))!=ESP_OK) return "Cannot retain original loader";
  for(unsigned I=0;I<3;I++)
    if(!HashFlash(PreservedOffset[I],PreservedSize[I],PreservedHash[I])) return "Cannot seal preserved ranges";
  BaselineValid=true;
  return NULL;
 }
static bool InstallLoader(void)
 {
  if(LoaderMatches(CandidateLoader)) return Preserved();
  TLoaderWriteResult Result=WriteBoundedLoader(OriginalLoader,CandidateLoader,false);
  LoaderUncertain=Result.DoNotRestart;
  LoaderChanged=Result.TargetVerified;
  if(!Result.TargetVerified||!Preserved())
   {
    LastError="Bootloader write/readback/preserved range failed";
    if(!Preserved()) LoaderUncertain=true;
    return false;
   }
  return true;
 }
static bool Stage(void)
 {
  return MigrationStage(RescuePayload,TAKEOVER_RESCUE_SIZE,OldTable,NewTable,CandidateLoader);
 }
static bool Commit(void) { return MigrationCommit(NewTable); }
static bool Ready(void) { return !LoaderUncertain&&LoaderMatches(CandidateLoader)&&Preserved()&&MigrationRestartReady(NewTable); }
static bool Uncertain(void) { return LoaderUncertain||MigrationUncertain(); }
static const char * Error(void) { return LastError[0]?LastError:MigrationError(); }
static bool Rollback(void)
 {
  if(Uncertain()||!Preserved()) return false;
  if(MigrationCheckpointPresent())
   {
    if(Matches(0x10000,NewTable,4096)&&!MigrationRollback(NewTable)) return false;
    if(!Matches(0x10000,OldTable,4096)||!MigrationReleaseCheckpoint(NewTable)) return false;
   }
  if(!Matches(0x10000,OldTable,4096)||!Matches(0x11000,BootSectors,8192)) return false;
  if(LoaderChanged)
   {
    TLoaderWriteResult Result=WriteBoundedLoader(CandidateLoader,OriginalLoader,false);
    LoaderUncertain=Result.DoNotRestart;
    if(!Result.TargetVerified||LoaderUncertain) return false;
   }
  return Preserved()&&LoaderMatches(OriginalLoader);
 }
static const TTakeoverOps Ops={Guard,InstallLoader,Stage,Commit,Ready,Uncertain,Rollback,Error,NULL,false};
const TTakeoverOps * ShellyTakeoverOperations(void) { return &Ops; }
