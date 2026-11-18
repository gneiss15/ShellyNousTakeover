#!/usr/bin/env python3
# VerifyShellyGuard.py, Version: 1.01
"""Compile the actual app guard with hardware/flash mocks; never use device captures."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parent.parent
text=(root/'ShellyTakeover/App/main/Platform.c').read_text()
a=text.index('static const char * Guard(void)');b=text.index('\nstatic bool InstallLoader',a)
guard=text[a:b]
layout=text[text.index('typedef struct'):text.index('static uint8_t OriginalLoader')]
prelude=r'''
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <assert.h>
#include <stddef.h>
#define ESP_OK 0
#define CHIP_ESP32C3 5
#define ESP_PARTITION_TYPE_APP 0
#define ESP_PARTITION_SUBTYPE_APP_OTA_1 17
#define LOADER_WRITE_SPAN 24576
#define TAKEOVER_RESCUE_SIZE 100
#define TAKEOVER_LARGE_RESCUE_SIZE 100
#define TAKEOVER_APP_OFFSET 0x3a0000
#define TAKEOVER_APP_SPAN 0x2a0000
#define TAKEOVER_RESCUE_OFFSET 0x640000
#define TAKEOVER_RESCUE_SPAN 0x180000
#define TAKEOVER_LARGE_APP_OFFSET 0x400000
#define TAKEOVER_LARGE_APP_SPAN 0x300000
#define TAKEOVER_LARGE_RESCUE_OFFSET 0x700000
#define TAKEOVER_LARGE_RESCUE_SPAN 0xc0000
#define ESP_IMAGE_VERIFY 0
static uint8_t CandidateLoader[24576],RescuePayload[100],OriginalLoader[24576],BootSectors[8192],NewSector[4096],OldTable[4096];

static uint8_t NewTable[4096],LargeOldTable[4096],LargeNewTable[4096],LargeLoader[24576],LargeRescue[100];
#define CandidateLoaderEnd (CandidateLoader+24576)
#define RescuePayloadEnd (RescuePayload+100)
#define LargeLoaderEnd (LargeLoader+24576)
#define LargeRescueEnd (LargeRescue+100)
static uint8_t TakeoverLargeLoaderHash[32],TakeoverLargeRescueHash[32];
static uint8_t TakeoverLoaderHash[32],TakeoverRescueHash[32],PreservedHash[3][32];
static uint32_t PreservedOffset[]={0x6000,0x13000,0x7f0000},PreservedSize[]={0xa000,0x62d000,0x10000};
static bool BaselineValid;
typedef struct {uint32_t offset,size;} esp_partition_pos_t;
typedef struct { unsigned unused; } esp_image_metadata_t;
typedef struct {int model,revision;} esp_chip_info_t;
typedef struct {int type,subtype;uint32_t address,size;} esp_partition_t;
static esp_chip_info_t Chip={5,4};static esp_partition_t Running={0,17,0x3a0000,0x2a0000};
static uint32_t FlashSize=0x800000;static bool Secure,Encrypted,Present=true,TableOk=true,StockOk=true,OriginalOk=true,TailOk=true,StateOk=true,Checkpoint,LoaderIsTarget,HashOk=true,MemoryHashOk=true;
static int Reads,FailRead;static bool Large;
void esp_chip_info(esp_chip_info_t *c){*c=Chip;}
const esp_partition_t *esp_ota_get_running_partition(void){return Present?&Running:NULL;}
int esp_flash_get_physical_size(void *c,uint32_t *s){(void)c;*s=FlashSize;return ESP_OK;}
bool esp_secure_boot_enabled(void){return Secure;}
bool esp_flash_encryption_enabled(void){return Encrypted;}
bool Matches(uint32_t o,const uint8_t *d,uint32_t n){assert(o==0x10000&&n==4096);return TableOk&&d==(Large?LargeOldTable:OldTable);}
int esp_image_verify(int mode,const esp_partition_pos_t *p,esp_image_metadata_t *m){(void)m;assert(mode==ESP_IMAGE_VERIFY&&p->offset==0x20000&&p->size==(Large?0x300000:0x2a0000));return StockOk?ESP_OK:-1;}
bool DigestMatches(uint32_t o,uint32_t n,const char *d){assert(o==0&&n==(Large?20272:20992)&&strlen(d)==64);return OriginalOk;}
bool Erased(uint32_t o,uint32_t n){assert(o==(Large?20272:20992)&&n==24576-o);return TailOk;}
bool LoaderMatches(const uint8_t *d){assert(d==(Large?LargeLoader:CandidateLoader));return LoaderIsTarget;}
void MigrationSetRescueRegion(uint32_t o,uint32_t n){assert(o==(Large?0x700000:0x640000)&&o+n==0x7c0000);}
int mbedtls_sha256(const uint8_t *d,size_t n,uint8_t out[32],int mode){(void)d;(void)n;assert(mode==0);memset(out,0,32);return MemoryHashOk?0:-1;}
int esp_flash_read(void*c,void*d,uint32_t o,uint32_t n){(void)c;(void)o;memset(d,0,n);return ++Reads==FailRead?-1:ESP_OK;}
bool PrepareStockBootState(const uint8_t*s,uint8_t *d,unsigned *t){(void)s;(void)d;*t=0;return StateOk;}
bool MigrationCheckpointPresent(void){return Checkpoint;}
bool HashFlash(uint32_t o,uint32_t n,uint8_t *h){(void)o;(void)n;memset(h,0,32);return HashOk;}
'''
tests=r'''
#define DENIED(Change,Restore) do{Change;assert(Guard()!=NULL);Restore;}while(0)
int main(void){
 assert(Guard()==NULL&&BaselineValid);
 Large=true;assert(Guard()!=NULL);Running.address=0x400000;Running.size=0x300000;assert(Guard()==NULL);
 Large=false;Running.address=0x3a0000;Running.size=0x2a0000;
 DENIED(Chip.model=0,Chip.model=5);DENIED(Chip.revision=3,Chip.revision=4);
 DENIED(FlashSize=0x400000,FlashSize=0x800000);DENIED(Secure=true,Secure=false);DENIED(Encrypted=true,Encrypted=false);
 DENIED(Present=false,Present=true);DENIED(Running.type=1,Running.type=0);DENIED(Running.subtype=16,Running.subtype=17);
 DENIED(Running.address=0x20000,Running.address=0x3a0000);DENIED(Running.size=0x100000,Running.size=0x2a0000);
 DENIED(MemoryHashOk=false,MemoryHashOk=true);DENIED(TableOk=false,TableOk=true);DENIED(StockOk=false,StockOk=true);
 DENIED(OriginalOk=false,OriginalOk=true);DENIED(TailOk=false,TailOk=true);DENIED(StateOk=false,StateOk=true);
 DENIED(Checkpoint=true,Checkpoint=false);DENIED(HashOk=false,HashOk=true);
 Reads=0;FailRead=1;assert(Guard()!=NULL);Reads=0;FailRead=2;assert(Guard()!=NULL);FailRead=0;
 LoaderIsTarget=true;OriginalOk=false;assert(Guard()==NULL);
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'test.c').write_text(prelude+layout+guard+tests)
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('Actual Shelly app guard passed: hardware/security/slot/payload/table/Stock/loader/tail/SH0S/checkpoint/read failures; no writes.')
