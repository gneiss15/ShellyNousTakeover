#!/usr/bin/env python3
# VerifyNousPlatform.py, Version: 1.00
"""Run actual Nous platform and loader writer with synthetic flash and real SHA256."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parent.parent
source=(root/'NousTakeover/App/main/Platform.c').read_text()
source='\n'.join(line for line in source.splitlines() if not line.startswith(('#include','extern const uint8_t')))
writer=(root/'NousTakeover/LoaderWriter/LoaderWriter.c').read_text()
writer='\n'.join(line for line in writer.splitlines() if not line.startswith('#include'))
writer=writer.replace('Matches(', 'WriterMatches(')
prelude=r'''
#include "Flow.h"
#include "LoaderWriter.h"
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <openssl/sha.h>
#define ESP_OK 0
#define CHIP_ESP32 0
#define ESP_PARTITION_TYPE_APP 0
#define ESP_PARTITION_TYPE_DATA 1
#define ESP_PARTITION_SUBTYPE_APP_FACTORY 0
#define ESP_PARTITION_SUBTYPE_APP_OTA_0 16
#define ESP_PARTITION_SUBTYPE_DATA_OTA 0
#define ESP_IMAGE_VERIFY 0
#define TAKEOVER_RESCUE_SIZE 8193
static uint8_t Flash[0x400000], Initial[0x400000];
static uint8_t CandidateLoader[0x7000],RescuePayload[8193],ExpectedTable[4096];
static uint8_t * CandidateLoaderEnd=CandidateLoader+sizeof(CandidateLoader),*RescuePayloadEnd=RescuePayload+sizeof(RescuePayload);
static uint8_t TakeoverLoaderHash[32],TakeoverRescueHash[32],TakeoverOriginalLoaderHash[32];
static unsigned Mutations,Reads,FailRead,PartCalls,FailPart,RawWrites,FailRawWrite;
static bool Protected=true,Secure,Encrypted,ImageOk=true,CommitFail;
static uint32_t PhysicalSize=0x400000;
static void * esp_flash_default_chip;
typedef struct {int model,cores;} esp_chip_info_t;
typedef struct {int type,subtype;unsigned address,size;} esp_partition_t;
typedef struct {unsigned offset,size;} esp_partition_pos_t;
typedef struct {unsigned unused;} esp_image_metadata_t;
static esp_chip_info_t Chip={0,2};
static esp_partition_t Main={0,16,0xE0000,0x2D0000},Factory={0,0,0x10000,0xD0000},OtaPart={1,0,0xE000,8192};
static bool Present=true;
static void esp_chip_info(esp_chip_info_t * c){*c=Chip;}
static int esp_flash_get_physical_size(void * c,uint32_t * n){(void)c;*n=PhysicalSize;return 0;}
static bool esp_secure_boot_enabled(void){return Secure;}
static bool esp_flash_encryption_enabled(void){return Encrypted;}
static const esp_partition_t * esp_ota_get_running_partition(void){return Present?&Main:NULL;}
static const esp_partition_t * esp_ota_get_boot_partition(void){return Flash[0xE000]==255?&Factory:Flash[0xE000]==0x11?&Main:NULL;}
static const esp_partition_t * esp_partition_find_first(int t,int s,const char * label){(void)t;(void)s;return !strcmp(label,"safeboot")?&Factory:&OtaPart;}
static int esp_flash_read(void * c,void * p,unsigned a,unsigned n){(void)c;assert(a+n<=sizeof(Flash));if(++Reads==FailRead)return -1;memcpy(p,Flash+a,n);return 0;}
static int esp_partition_read(const esp_partition_t * p,unsigned a,void * d,unsigned n){return esp_flash_read(NULL,d,p->address+a,n);}
static int esp_flash_set_dangerous_write_protection(void * c,bool v){(void)c;Protected=v;return 0;}
static int esp_flash_erase_region(void * c,unsigned a,unsigned n){(void)c;assert(!Protected&&a==0x1000&&n==0x7000);Mutations++;memset(Flash+a,255,n);return 0;}
static int esp_flash_write(void * c,const void * d,unsigned a,unsigned n){(void)c;assert(!Protected&&a>=0x1000&&a+n<=0x8000);Mutations++;if(++RawWrites==FailRawWrite){memcpy(Flash+a,d,n/2);return -1;}memcpy(Flash+a,d,n);return 0;}
static int esp_partition_erase_range(const esp_partition_t * p,unsigned a,unsigned n){assert(p==&Factory||p==&OtaPart);assert(a+n<=p->size);Mutations++;bool failed=++PartCalls==FailPart;memset(Flash+p->address+a,255,failed?n/2:n);return failed?-1:0;}
static int esp_partition_write(const esp_partition_t * p,unsigned a,const void * d,unsigned n){assert(p==&Factory||p==&OtaPart);assert(a+n<=p->size);Mutations++;bool failed=++PartCalls==FailPart;memcpy(Flash+p->address+a,d,failed?n/2:n);return failed?-1:0;}
static int esp_ota_set_boot_partition(const esp_partition_t * p){assert(p==&Factory);int result=esp_partition_erase_range(&OtaPart,0,8192);return CommitFail?-1:result;}
static int esp_image_verify(int mode,const esp_partition_pos_t * p,esp_image_metadata_t * m){(void)mode;(void)m;assert(p->offset==0x10000&&p->size==0xD0000);return ImageOk?0:-1;}
typedef SHA256_CTX mbedtls_sha256_context;
static void mbedtls_sha256_init(mbedtls_sha256_context * c){memset(c,0,sizeof(*c));}
static int mbedtls_sha256_starts(mbedtls_sha256_context * c,int v){assert(v==0);return SHA256_Init(c)?0:-1;}
static int mbedtls_sha256_update(mbedtls_sha256_context * c,const void * p,size_t n){return SHA256_Update(c,p,n)?0:-1;}
static int mbedtls_sha256_finish(mbedtls_sha256_context * c,uint8_t * h){return SHA256_Final(h,c)?0:-1;}
static void mbedtls_sha256_free(mbedtls_sha256_context * c){(void)c;}
static int mbedtls_sha256(const void * p,size_t n,uint8_t * h,int v){assert(v==0);return SHA256(p,n,h)?0:-1;}
'''
tests=r'''
static void reset(void){
 memset(Flash,0x55,sizeof(Flash));memset(Flash+0x1000,0xaa,0x7000);memset(Flash+0xE000,0x11,8192);
 memset(CandidateLoader,0xbb,sizeof(CandidateLoader));memset(RescuePayload,0xcc,sizeof(RescuePayload));memcpy(ExpectedTable,Flash+0x8000,4096);
 memcpy(Initial,Flash,sizeof(Flash));mbedtls_sha256(CandidateLoader,sizeof(CandidateLoader),TakeoverLoaderHash,0);
 mbedtls_sha256(RescuePayload,sizeof(RescuePayload),TakeoverRescueHash,0);mbedtls_sha256(Flash+0x1000,0x7000,TakeoverOriginalLoaderHash,0);
 BaselineValid=RescueVerified=LoaderChanged=Unsafe=SelectionTouched=false;Secure=Encrypted=CommitFail=false;ImageOk=Present=Protected=true;
 Mutations=Reads=FailRead=PartCalls=FailPart=RawWrites=FailRawWrite=0;LastError="";
}
static void unchanged(void){assert(!memcmp(Flash,Initial,0x1000));assert(!memcmp(Flash+0x8000,Initial+0x8000,0x6000));assert(!memcmp(Flash+0xE0000,Initial+0xE0000,0x320000));}
#define DENY(Change,Restore) do{reset();Change;assert(Guard()!=NULL&&Mutations==0);Restore;}while(0)
int main(void){
 reset();TTakeoverResult r=TakeoverRun(NousTakeoverOperations());assert(r.RescueReady&&!r.DoNotRestart&&Protected&&esp_ota_get_boot_partition()==&Factory);unchanged();
 DENY(Chip.model=1,Chip.model=0);DENY(Chip.cores=1,Chip.cores=2);DENY(PhysicalSize=0x800000,PhysicalSize=0x400000);
 DENY(Secure=true,Secure=false);DENY(Encrypted=true,Encrypted=false);DENY(Present=false,Present=true);
 DENY(Main.address++,Main.address--);DENY(Main.size--,Main.size++);DENY(Main.subtype=0,Main.subtype=16);
 DENY(CandidateLoaderEnd--,CandidateLoaderEnd++);DENY(RescuePayloadEnd--,RescuePayloadEnd++);
 DENY(CandidateLoader[0]^=1,(void)0);DENY(RescuePayload[0]^=1,(void)0);DENY(Flash[0x8000]^=1,(void)0);DENY(Flash[0x1000]^=1,(void)0);
 DENY(ImageOk=false,ImageOk=true);DENY(Flash[0xE000]=255,(void)0);DENY(FailRead=1,(void)0);
 for(unsigned failure=1;failure<=4;failure++){
  reset();FailPart=failure;r=TakeoverRun(NousTakeoverOperations());assert(!r.RescueReady&&r.RollbackVerified&&!r.DoNotRestart&&RawWrites==0&&Protected);unchanged();assert(!memcmp(Flash+0x1000,Initial+0x1000,0x7000));
 }
 for(unsigned failure=1;failure<=7;failure++){
  reset();FailRawWrite=failure;r=TakeoverRun(NousTakeoverOperations());assert(!r.RescueReady&&r.RollbackVerified&&!r.DoNotRestart&&Protected&&esp_ota_get_boot_partition()==&Main);unchanged();assert(!memcmp(Flash+0x1000,Initial+0x1000,0x7000));
 }
 reset();CommitFail=true;r=TakeoverRun(NousTakeoverOperations());assert(!r.RescueReady&&r.RollbackVerified&&!r.DoNotRestart&&Protected);unchanged();assert(!memcmp(Flash+0x1000,Initial+0x1000,0x7000)&&!memcmp(Flash+0xE000,Initial+0xE000,8192));
 reset();assert(!Guard()&&Stage()&&InstallLoader());CommitFail=true;assert(!Commit());FailPart=PartCalls+1;assert(!Rollback()&&Uncertain());unchanged();
 reset();assert(!Guard());unsigned before=Mutations;Flash[0x9000]^=1;assert(!Stage()&&Uncertain()&&Mutations==before);
 reset();assert(!Guard()&&Stage());Flash[0x10000]^=1;before=Mutations;assert(!InstallLoader()&&Uncertain()&&Mutations==before);
 puts("Actual Nous platform passed: real SHA256, guards without writes, full automatic flow, partial Rescue writes, all loader block failures, OTA selection rollback, failed rollback and preservation gates. SDK image validation and hardware are mocked.");
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'test.c').write_text(prelude+writer+'\n'+source+'\n'+tests)
 subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations','-I',str(root/'common/Takeover'),'-I',str(root/'NousTakeover/LoaderWriter'),str(p/'test.c'),str(root/'common/Takeover/Flow.c'),'-lcrypto','-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
