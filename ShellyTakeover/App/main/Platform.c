// Platform.c, Version: 1.02
#include "Platform.h"
#include "Migration.h"
#include "LoaderWriter.h"
#include "BootState.h"
#include "PayloadIdentity.h"
#include "esp_flash.h"
#include "esp_flash_internal.h"
#include "esp_chip_info.h"
#include "esp_secure_boot.h"
#include "esp_flash_encrypt.h"
#include "esp_ota_ops.h"
#include "esp_image_format.h"
#include "mbedtls/sha256.h"
#include <string.h>
#include <stdio.h>
extern const uint8_t OldTable[] asm("_binary_OldTable_bin_start");
extern const uint8_t NewTable[] asm("_binary_NewTable_bin_start");
extern const uint8_t CandidateLoader[] asm("_binary_CandidateLoader_bin_start");
extern const uint8_t CandidateLoaderEnd[] asm("_binary_CandidateLoader_bin_end");
extern const uint8_t RescuePayload[] asm("_binary_Rescue_bin_start");
extern const uint8_t RescuePayloadEnd[] asm("_binary_Rescue_bin_end");
extern const uint8_t LargeOldTable[] asm("_binary_LargeOldTable_bin_start");
extern const uint8_t LargeNewTable[] asm("_binary_LargeNewTable_bin_start");
extern const uint8_t LargeLoader[] asm("_binary_LargeLoader_bin_start");
extern const uint8_t LargeLoaderEnd[] asm("_binary_LargeLoader_bin_end");
extern const uint8_t LargeRescue[] asm("_binary_LargeRescue_bin_start");
extern const uint8_t LargeRescueEnd[] asm("_binary_LargeRescue_bin_end");
typedef struct
 {
  const uint8_t * Old, * Target, * Loader, * LoaderEnd, * Rescue, * RescueEnd;
  const uint8_t * LoaderHash, * RescueHash;
  uint32_t AppOffset, AppSize, RescueOffset, RescueSize, PayloadSize;
 } TLayout;
static const TLayout Layouts[] = {
  {OldTable, NewTable, CandidateLoader, CandidateLoaderEnd, RescuePayload, RescuePayloadEnd,
   TakeoverLoaderHash, TakeoverRescueHash, TAKEOVER_APP_OFFSET, TAKEOVER_APP_SPAN,
   TAKEOVER_RESCUE_OFFSET, TAKEOVER_RESCUE_SPAN, TAKEOVER_RESCUE_SIZE},
  {LargeOldTable, LargeNewTable, LargeLoader, LargeLoaderEnd, LargeRescue, LargeRescueEnd,
   TakeoverLargeLoaderHash, TakeoverLargeRescueHash, TAKEOVER_LARGE_APP_OFFSET, TAKEOVER_LARGE_APP_SPAN,
   TAKEOVER_LARGE_RESCUE_OFFSET, TAKEOVER_LARGE_RESCUE_SPAN, TAKEOVER_LARGE_RESCUE_SIZE}
};
static const TLayout * Layout;
static uint8_t OriginalLoader[LOADER_WRITE_SPAN];
static uint8_t Buffer[4096];
static uint8_t BootSectors[8192], NewSector[4096];
static uint8_t PreservedHash[3][32];
static const uint32_t PreservedOffset[] = {0x6000, 0x13000, 0x7F0000};
static uint32_t PreservedSize[] = {0xA000, 0x62D000, 0x10000};
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
    Running->subtype!=ESP_PARTITION_SUBTYPE_APP_OTA_1)
    return "Unsupported chip/security/flash/running slot";
  Layout=NULL;
  for(unsigned I=0;I<sizeof(Layouts)/sizeof(Layouts[0]);I++)
    if(Matches(0x10000,Layouts[I].Old,4096)) {Layout=&Layouts[I];break;}
  if(!Layout) return "Unsupported original partition table";
  if(Running->address!=Layout->AppOffset||Running->size!=Layout->AppSize||
    Running->address+Running->size>Layout->RescueOffset)
    return "Running slot differs from known partition table or overlaps migration";
  const esp_partition_pos_t Stock={.offset=0x20000,.size=Layout->AppSize};
  esp_image_metadata_t Image={0};
  if(esp_image_verify(ESP_IMAGE_VERIFY,&Stock,&Image)!=ESP_OK)
    return "Stock app in app_0 is not a valid ESP image";
  uint8_t Hash[32];
  if(Layout->LoaderEnd-Layout->Loader!=LOADER_WRITE_SPAN||
    mbedtls_sha256(Layout->Loader,LOADER_WRITE_SPAN,Hash,0)!=0||memcmp(Hash,Layout->LoaderHash,32))
    return "Embedded loader integrity check failed";
  if(!LoaderMatches(Layout->Loader))
   {
    const bool Large=Layout==&Layouts[1];
    const uint32_t BootSize=Large?20272:20992;
    const char * BootHash=Large?"c4faf5d46de22ceb11f6e85c9b142f3999316c34670894ba68e77bd00c7e8e8a":
      "8df59da4cb489ce7cb95010966c7ad5ba67c6745cf0b76eac70b9ea4692f9979";
    if(!DigestMatches(0,BootSize,BootHash)||!Erased(BootSize,LOADER_WRITE_SPAN-BootSize))
      return "Unknown bootloader; no write";
   }
  unsigned Target;
  if(esp_flash_read(NULL,BootSectors,0x11000,sizeof(BootSectors))!=ESP_OK||!PrepareStockBootState(BootSectors,NewSector,&Target))
    return "SH0S does not permit verified Stock recovery";
  if(MigrationCheckpointPresent()) return "Existing or unreadable migration checkpoint";
  MigrationSetRescueRegion(Layout->RescueOffset,Layout->RescueSize);
  PreservedSize[1]=Layout->RescueOffset-PreservedOffset[1];
  if(esp_flash_read(NULL,OriginalLoader,0,sizeof(OriginalLoader))!=ESP_OK) return "Cannot retain original loader";
  for(unsigned I=0;I<3;I++)
    if(!HashFlash(PreservedOffset[I],PreservedSize[I],PreservedHash[I])) return "Cannot seal preserved ranges";
  BaselineValid=true;
  if(Layout->RescueEnd-Layout->Rescue!=Layout->PayloadSize||Layout->PayloadSize>Layout->RescueSize)
    return "Embedded Rescue length differs";
  if(mbedtls_sha256(Layout->Rescue,Layout->PayloadSize,Hash,0)!=0||memcmp(Hash,Layout->RescueHash,32))
    return "Embedded Rescue digest differs";
  return NULL;
 }
static bool InstallLoader(void)
 {
  if(LoaderMatches(Layout->Loader)) return Preserved();
  TLoaderWriteResult Result=WriteBoundedLoader(OriginalLoader,Layout->Loader,false);
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
  return MigrationStage(Layout->Rescue,Layout->PayloadSize,Layout->Old,Layout->Target,Layout->Loader);
 }
static bool Commit(void) { return MigrationCommit(Layout->Target); }
static bool Ready(void) { return !LoaderUncertain&&LoaderMatches(Layout->Loader)&&Preserved()&&MigrationRestartReady(Layout->Target); }
static bool Uncertain(void) { return LoaderUncertain||MigrationUncertain(); }
static const char * Error(void) { return LastError[0]?LastError:MigrationError(); }
static bool Rollback(void)
 {
  if(Uncertain()||!Preserved()) return false;
  if(MigrationCheckpointPresent())
   {
    if(Matches(0x10000,Layout->Target,4096)&&!MigrationRollback(Layout->Target)) return false;
    if(!Matches(0x10000,Layout->Old,4096)||!MigrationReleaseCheckpoint(Layout->Target)) return false;
   }
  if(!Matches(0x10000,Layout->Old,4096)||!Matches(0x11000,BootSectors,8192)) return false;
  if(LoaderChanged)
   {
    TLoaderWriteResult Result=WriteBoundedLoader(Layout->Loader,OriginalLoader,false);
    LoaderUncertain=Result.DoNotRestart;
    if(!Result.TargetVerified||LoaderUncertain) return false;
   }
  return Preserved()&&LoaderMatches(OriginalLoader);
 }
static const TTakeoverOps Ops={Guard,InstallLoader,Stage,Commit,Ready,Uncertain,Rollback,Error,NULL,false};
const TTakeoverOps * ShellyTakeoverOperations(void) { return &Ops; }

bool ShellyReturnToStock(void)
 {
  unsigned Target;
  if(!BaselineValid||Uncertain()||!Preserved()||!LoaderMatches(OriginalLoader)||
    !Matches(0x10000,Layout->Old,4096)||!Matches(0x11000,BootSectors,sizeof(BootSectors))||
    !PrepareStockBootState(BootSectors,NewSector,&Target))
    return false;
  const uint32_t Address=0x11000+Target*BOOT_STATE_SECTOR_SIZE;
  const uint32_t Winner=1-Target;
  bool Written=false;
  if(esp_flash_set_dangerous_write_protection(esp_flash_default_chip,false)==ESP_OK)
    Written=esp_flash_erase_region(NULL,Address,BOOT_STATE_SECTOR_SIZE)==ESP_OK&&
      esp_flash_write(NULL,NewSector,Address,BOOT_STATE_SECTOR_SIZE)==ESP_OK;
  const bool ProtectedAgain=esp_flash_set_dangerous_write_protection(esp_flash_default_chip,true)==ESP_OK;
  return Written&&ProtectedAgain&&Matches(Address,NewSector,BOOT_STATE_SECTOR_SIZE)&&
    Matches(0x11000+Winner*BOOT_STATE_SECTOR_SIZE,
      BootSectors+Winner*BOOT_STATE_SECTOR_SIZE,BOOT_STATE_SECTOR_SIZE)&&
    Matches(0x10000,Layout->Old,4096)&&Preserved()&&LoaderMatches(OriginalLoader);
 }
