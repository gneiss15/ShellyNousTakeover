#!/usr/bin/env python3
# VerifyShellyGuard.py, Version: 1.01
"""Compile the actual app guard with hardware/flash mocks; never use device captures."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parent.parent
text=(root/'ShellyTakeover/App/main/Platform.c').read_text()
a=text.index('static const char * Guard(void)');b=text.index('\nstatic bool InstallLoader',a)
guard=text[a:b]
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
static uint8_t CandidateLoader[24576],RescuePayload[100],OriginalLoader[24576],BootSectors[8192],NewSector[4096],OldTable[4096];
static uint8_t *CandidateLoaderEnd=CandidateLoader+24576,*RescuePayloadEnd=RescuePayload+100;
static uint8_t TakeoverLoaderHash[32],TakeoverRescueHash[32],PreservedHash[3][32];
static uint32_t PreservedOffset[]={0x6000,0x13000,0x7f0000},PreservedSize[]={0xa000,0x62d000,0x10000};
static bool BaselineValid;
typedef struct {int model,revision;} esp_chip_info_t;
typedef struct {int type,subtype;uint32_t address,size;} esp_partition_t;
static esp_chip_info_t Chip={5,4};static esp_partition_t Running={0,17,0x3a0000,0x2a0000};
static uint32_t FlashSize=0x800000;static bool Secure,Encrypted,Present=true,TableOk=true,StockOk=true,OriginalOk=true,TailOk=true,HighOk=true,StateOk=true,Checkpoint,LoaderIsTarget,HashOk=true,MemoryHashOk=true;
static int Reads,FailRead;static uint32_t StockSize=2708368;
void esp_chip_info(esp_chip_info_t *c){*c=Chip;}
const esp_partition_t *esp_ota_get_running_partition(void){return Present?&Running:NULL;}
int esp_flash_get_physical_size(void *c,uint32_t *s){(void)c;*s=FlashSize;return ESP_OK;}
bool esp_secure_boot_enabled(void){return Secure;}
bool esp_flash_encryption_enabled(void){return Encrypted;}
bool Matches(uint32_t o,const uint8_t *d,uint32_t n){(void)d;assert(o==0x10000&&n==4096);return TableOk;}
bool DigestMatches(uint32_t o,uint32_t n,const char *d){assert(strlen(d)==64);if(o==0x20000){assert(n==2708368||n==2712352);assert(strcmp(d,n==2708368?"80ce0363774d9904464e5e11c0b2740e5ba221a0104615a841213a83129e6514":"82f71b5db76025617ef0f12966dfcd9b0c7af765adf9a114615dd32b41efaeef")==0);return StockOk&&n==StockSize;}assert(o==0&&n==20992);return OriginalOk;}
bool Erased(uint32_t o,uint32_t n){if(o==20992){assert(n==24576-20992);return TailOk;}assert(o==0x640000&&n==0x1b0000);return HighOk;}
bool LoaderMatches(const uint8_t *d){assert(d==CandidateLoader);return LoaderIsTarget;}
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
 StockSize=2712352;assert(Guard()==NULL);StockSize=0;assert(Guard()!=NULL);StockSize=2708368;
 DENIED(Chip.model=0,Chip.model=5);DENIED(Chip.revision=3,Chip.revision=4);
 DENIED(FlashSize=0x400000,FlashSize=0x800000);DENIED(Secure=true,Secure=false);DENIED(Encrypted=true,Encrypted=false);
 DENIED(Present=false,Present=true);DENIED(Running.type=1,Running.type=0);DENIED(Running.subtype=16,Running.subtype=17);
 DENIED(Running.address=0x20000,Running.address=0x3a0000);DENIED(Running.size=0x100000,Running.size=0x2a0000);
 DENIED(CandidateLoaderEnd--,CandidateLoaderEnd++);DENIED(RescuePayloadEnd--,RescuePayloadEnd++);
 DENIED(MemoryHashOk=false,MemoryHashOk=true);DENIED(TableOk=false,TableOk=true);DENIED(StockOk=false,StockOk=true);
 DENIED(OriginalOk=false,OriginalOk=true);DENIED(TailOk=false,TailOk=true);DENIED(StateOk=false,StateOk=true);
 DENIED(Checkpoint=true,Checkpoint=false);DENIED(HighOk=false,HighOk=true);DENIED(HashOk=false,HashOk=true);
 Reads=0;FailRead=1;assert(Guard()!=NULL);Reads=0;FailRead=2;assert(Guard()!=NULL);FailRead=0;
 LoaderIsTarget=true;OriginalOk=false;assert(Guard()==NULL);
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'test.c').write_text(prelude+guard+tests)
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('Actual Shelly app guard passed: hardware/security/slot/payload/table/Stock/loader/tail/SH0S/high-area/checkpoint/read failures; no writes.')
