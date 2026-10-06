// Platform.c, Version: 1.00
#include "Platform.h"
#include "LoaderWriter.h"
#include "PayloadIdentity.h"
#include "esp_chip_info.h"
#include "esp_flash.h"
#include "esp_flash_encrypt.h"
#include "esp_secure_boot.h"
#include "esp_ota_ops.h"
#include "esp_image_format.h"
#include "mbedtls/sha256.h"
#include <string.h>
extern const uint8_t CandidateLoader[] asm("_binary_CandidateLoader_bin_start");
extern const uint8_t CandidateLoaderEnd[] asm("_binary_CandidateLoader_bin_end");
extern const uint8_t RescuePayload[] asm("_binary_Rescue_bin_start");
extern const uint8_t RescuePayloadEnd[] asm("_binary_Rescue_bin_end");
extern const uint8_t ExpectedTable[] asm("_binary_ExpectedTable_bin_start");
static uint8_t OriginalLoader[NOUS_LOADER_SPAN], OriginalOta[8192], Buffer[4096];
static uint8_t BaselineHash[3][32];
static const unsigned PreservedAddress[]={0,0x8000,0xE0000};
static const unsigned PreservedSize[]={0x1000,0x6000,0x320000};
static const esp_partition_t * Rescue, * Ota;
static bool BaselineValid, RescueVerified, LoaderChanged, Unsafe, SelectionTouched;
static const char * LastError="";
static bool HashFlash(unsigned Address,unsigned Size,uint8_t Hash[32])
 {
  mbedtls_sha256_context Context;mbedtls_sha256_init(&Context);
  bool Ok=mbedtls_sha256_starts(&Context,0)==0;
  while(Size&&Ok)
   {
    unsigned Count=Size<sizeof(Buffer)?Size:sizeof(Buffer);
    Ok=esp_flash_read(NULL,Buffer,Address,Count)==ESP_OK&&mbedtls_sha256_update(&Context,Buffer,Count)==0;
    Size-=Count;Address+=Count;
   }
  if(Ok) Ok=mbedtls_sha256_finish(&Context,Hash)==0;
  mbedtls_sha256_free(&Context);return Ok;
 }
static bool Matches(unsigned Address,const uint8_t * Data,unsigned Size)
 {
  for(unsigned Offset=0;Offset<Size;)
   {
    unsigned Count=Size-Offset<sizeof(Buffer)?Size-Offset:sizeof(Buffer);
    if(esp_flash_read(NULL,Buffer,Address+Offset,Count)!=ESP_OK||memcmp(Buffer,Data+Offset,Count)) return false;
    Offset+=Count;
   }
  return true;
 }
static bool Preserved(void)
 {
  uint8_t Hash[32];if(!BaselineValid) return false;
  for(unsigned Index=0;Index<3;++Index)
    if(!HashFlash(PreservedAddress[Index],PreservedSize[Index],Hash)||memcmp(Hash,BaselineHash[Index],32)) return false;
  return true;
 }
static bool ImageValid(const esp_partition_t * Partition)
 {
  if(!Partition) return false;
  esp_partition_pos_t Position={.offset=Partition->address,.size=Partition->size};
  esp_image_metadata_t Metadata={0};
  return esp_image_verify(ESP_IMAGE_VERIFY,&Position,&Metadata)==ESP_OK;
 }
static const char * Guard(void)
 {
  esp_chip_info_t Chip={0};esp_chip_info(&Chip);uint32_t Size=0;
  const esp_partition_t * Running=esp_ota_get_running_partition();
  if(Chip.model!=CHIP_ESP32||Chip.cores!=2||esp_flash_get_physical_size(NULL,&Size)!=ESP_OK||Size!=0x400000||
    esp_secure_boot_enabled()||esp_flash_encryption_enabled()||!Running||Running->type!=ESP_PARTITION_TYPE_APP||
    Running->subtype!=ESP_PARTITION_SUBTYPE_APP_OTA_0||Running->address!=0xE0000||Running->size!=0x2D0000)
    return "Unsupported chip/security/flash/running slot";
  if(CandidateLoaderEnd-CandidateLoader!=NOUS_LOADER_SPAN||RescuePayloadEnd-RescuePayload!=TAKEOVER_RESCUE_SIZE||
    TAKEOVER_RESCUE_SIZE>0xD0000||!Matches(0x8000,ExpectedTable,4096)) return "Unsupported layout or payload length";
  uint8_t Hash[32];
  if(mbedtls_sha256(CandidateLoader,NOUS_LOADER_SPAN,Hash,0)!=0||memcmp(Hash,TakeoverLoaderHash,32)||
    mbedtls_sha256(RescuePayload,TAKEOVER_RESCUE_SIZE,Hash,0)!=0||memcmp(Hash,TakeoverRescueHash,32))
    return "Embedded payload digest differs";
  if(!HashFlash(NOUS_LOADER_OFFSET,NOUS_LOADER_SPAN,Hash)||memcmp(Hash,TakeoverOriginalLoaderHash,32))
    return "Unknown original bootloader; no write";
  Rescue=esp_partition_find_first(ESP_PARTITION_TYPE_APP,ESP_PARTITION_SUBTYPE_APP_FACTORY,"safeboot");
  Ota=esp_partition_find_first(ESP_PARTITION_TYPE_DATA,ESP_PARTITION_SUBTYPE_DATA_OTA,"otadata");
  if(!Rescue||Rescue->address!=0x10000||Rescue->size!=0xD0000||!Ota||Ota->address!=0xE000||Ota->size!=8192||
    !ImageValid(Rescue)||esp_ota_get_boot_partition()!=Running) return "SafeBoot image/partition/boot selection invalid";
  if(esp_flash_read(NULL,OriginalLoader,NOUS_LOADER_OFFSET,sizeof(OriginalLoader))!=ESP_OK||
    mbedtls_sha256(OriginalLoader,sizeof(OriginalLoader),Hash,0)!=0||memcmp(Hash,TakeoverOriginalLoaderHash,32)||
    esp_partition_read(Ota,0,OriginalOta,sizeof(OriginalOta))!=ESP_OK) return "Cannot retain verified recovery baseline";
  for(unsigned Index=0;Index<3;++Index)
    if(!HashFlash(PreservedAddress[Index],PreservedSize[Index],BaselineHash[Index])) return "Cannot seal preserved ranges";
  BaselineValid=true;return NULL;
 }
static bool RescueMatches(void)
 {
  if(!Matches(0x10000,RescuePayload,TAKEOVER_RESCUE_SIZE)) return false;
  for(unsigned Offset=TAKEOVER_RESCUE_SIZE;Offset<0xD0000;)
   {
    unsigned Count=0xD0000-Offset<sizeof(Buffer)?0xD0000-Offset:sizeof(Buffer);
    if(esp_flash_read(NULL,Buffer,0x10000+Offset,Count)!=ESP_OK) return false;
    for(unsigned Index=0;Index<Count;++Index) if(Buffer[Index]!=255) return false;
    Offset+=Count;
   }
  return ImageValid(Rescue);
 }
static bool Stage(void)
 {
  LastError="Rescue erase/write/readback failed";
  if(!BaselineValid||!Preserved()||!Matches(0xE000,OriginalOta,8192)) {Unsafe=true;return false;}
  if(esp_partition_erase_range(Rescue,0,Rescue->size)!=ESP_OK) return false;
  for(unsigned Offset=0;Offset<TAKEOVER_RESCUE_SIZE;)
   {
    unsigned Count=TAKEOVER_RESCUE_SIZE-Offset<sizeof(Buffer)?TAKEOVER_RESCUE_SIZE-Offset:sizeof(Buffer);
    // Copy embedded flash bytes into RAM before calling a flash write API.
    memcpy(Buffer,RescuePayload+Offset,Count);
    if(esp_partition_write(Rescue,Offset,Buffer,Count)!=ESP_OK) return false;
    Offset+=Count;
   }
  RescueVerified=RescueMatches();
  if(!Preserved()||!Matches(0xE000,OriginalOta,8192)) Unsafe=true;
  return RescueVerified&&!Unsafe;
 }
static bool InstallLoader(void)
 {
  LastError="Bootloader write/readback failed";
  if(!RescueVerified||!RescueMatches()||!Preserved()) {Unsafe=true;return false;}
  TNousLoaderResult Result=NousWriteLoader(OriginalLoader,CandidateLoader,BaselineValid,RescueVerified);
  LoaderChanged=Result.TargetVerified;Unsafe=Result.DoNotRestart;
  if(!Preserved()||!Matches(0xE000,OriginalOta,8192)) Unsafe=true;
  return Result.TargetVerified&&!Unsafe;
 }
static bool Commit(void)
 {
  LastError="Selecting Rescue failed";
  if(Unsafe||!Preserved()||!RescueMatches()||!Matches(NOUS_LOADER_OFFSET,CandidateLoader,NOUS_LOADER_SPAN)||
    !Matches(0xE000,OriginalOta,8192)) return false;
  SelectionTouched=true;
  return esp_ota_set_boot_partition(Rescue)==ESP_OK&&esp_ota_get_boot_partition()==Rescue;
 }
static bool Ready(void)
 {
  LastError="Final Rescue start verification failed";
  if(!Preserved()) Unsafe=true;
  return !Unsafe&&RescueMatches()&&Matches(NOUS_LOADER_OFFSET,CandidateLoader,NOUS_LOADER_SPAN)&&
    esp_ota_get_boot_partition()==Rescue;
 }
static bool Rollback(void)
 {
  // Limited recovery: keep the running Takeover bootable; old SafeBoot is not backed up.
  if(Unsafe||!BaselineValid||!Preserved()) return false;
  if(SelectionTouched)
   {
    if(esp_partition_erase_range(Ota,0,8192)!=ESP_OK||esp_partition_write(Ota,0,OriginalOta,8192)!=ESP_OK||
      !Matches(0xE000,OriginalOta,8192)) {Unsafe=true;return false;}
   }
  if(!Matches(0xE000,OriginalOta,8192)) {Unsafe=true;return false;}
  if(LoaderChanged)
   {
    TNousLoaderResult Result=NousWriteLoader(CandidateLoader,OriginalLoader,true,RescueVerified);
    Unsafe=Result.DoNotRestart;
    if(!Result.TargetVerified||Unsafe) return false;
   }
  return Preserved()&&Matches(NOUS_LOADER_OFFSET,OriginalLoader,NOUS_LOADER_SPAN)&&
    esp_ota_get_boot_partition()==esp_ota_get_running_partition();
 }
static bool Uncertain(void) { return Unsafe; }
static const char * Error(void) { return LastError; }
static const TTakeoverOps Ops={Guard,InstallLoader,Stage,Commit,Ready,Uncertain,Rollback,Error,NULL,true};
const TTakeoverOps * NousTakeoverOperations(void) { return &Ops; }
