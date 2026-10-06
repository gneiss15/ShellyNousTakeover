# VerifyMigration.py, Version: 1.00
"""Compile the actual bounded writer with fault-injected flash and real SHA256."""
from pathlib import Path
import subprocess
import tempfile
import sys
root = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as temp:
    p=Path(temp);(p/'mbedtls').mkdir();(p/'freertos').mkdir()
    (p/'esp_flash.h').write_text('''#include <stdint.h>
#define ESP_OK 0
int esp_flash_read(void*,void*,uint32_t,uint32_t);
int esp_flash_write(void*,const void*,uint32_t,uint32_t);
int esp_flash_erase_region(void*,uint32_t,uint32_t);
int esp_flash_get_size(void*,uint32_t*);
''')
    (p/'esp_flash_internal.h').write_text('#include <stdbool.h>\nextern void * esp_flash_default_chip;\nint esp_flash_set_dangerous_write_protection(void*,bool);\n')
    (p/'mbedtls/sha256.h').write_text('''#include <openssl/sha.h>
typedef SHA256_CTX mbedtls_sha256_context;
static inline void mbedtls_sha256_init(SHA256_CTX*c){(void)c;}
static inline void mbedtls_sha256_free(SHA256_CTX*c){(void)c;}
static inline int mbedtls_sha256_starts(SHA256_CTX*c,int b){(void)b;return SHA256_Init(c)==1?0:-1;}
static inline int mbedtls_sha256_update(SHA256_CTX*c,const unsigned char*d,unsigned n){return SHA256_Update(c,d,n)==1?0:-1;}
static inline int mbedtls_sha256_finish(SHA256_CTX*c,unsigned char*h){return SHA256_Final(h,c)==1?0:-1;}
static inline int mbedtls_sha256(const void*d,unsigned n,unsigned char*h,int b){(void)b;return SHA256(d,n,h)?0:-1;}
''')
    (p/'freertos/FreeRTOS.h').write_text('')
    (p/'freertos/task.h').write_text('static inline void vTaskDelay(unsigned n){(void)n;}\n')
    harness=r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "Migration.c"
static unsigned char Flash[MIG_FLASH_SIZE],Baseline[MIG_FLASH_SIZE];
static unsigned char Old[4096],Target[4096],Loader[0x6000],Rescue[0x13000];
void *esp_flash_default_chip;
static int Calls,FailAt,Failures,MutationCalls;
static bool ProtectedFlag=true;
static bool readonly(uint32_t o,uint32_t n){if(memcmp(Flash+0x10000,Target,4096))return false;return (o<0x13000&&o+n>0x11000)||(o<0x80000&&o+n>0x14000)||(o+n>MIG_FACTORY_OFFSET);}
static int fault(void){Calls++;if(Calls==FailAt){Failures++;return 1;}return 0;}
int esp_flash_get_size(void*c,uint32_t*s){(void)c;*s=sizeof(Flash);return fault();}
int esp_flash_read(void*c,void*d,uint32_t o,uint32_t n){(void)c;assert(o+n<=sizeof(Flash));if(fault())return 1;memcpy(d,Flash+o,n);return 0;}
int esp_flash_write(void*c,const void*d,uint32_t o,uint32_t n){(void)c;assert(!ProtectedFlag&&o+n<=sizeof(Flash));MutationCalls++;if(readonly(o,n))return 1;if(fault()){if(n>1)memcpy(Flash+o,d,n/2);return 1;}memcpy(Flash+o,d,n);return 0;}
int esp_flash_erase_region(void*c,uint32_t o,uint32_t n){(void)c;assert(!ProtectedFlag&&o%4096==0&&n%4096==0&&o+n<=sizeof(Flash));MutationCalls++;if(readonly(o,n))return 1;if(fault()){memset(Flash+o,255,n/2);return 1;}memset(Flash+o,255,n);return 0;}
int esp_flash_set_dangerous_write_protection(void*c,bool b){(void)c;if(fault())return 1;ProtectedFlag=b;return 0;}
static void reset(void){
 memset(Flash,255,sizeof(Flash));for(unsigned i=0;i<sizeof(Loader);i++)Loader[i]=(i*31)%251;
 memset(Old,0xA1,sizeof(Old));memset(Target,0xB2,sizeof(Target));memset(Rescue,0xC3,sizeof(Rescue));
 memcpy(Flash,Loader,sizeof(Loader));memcpy(Flash+0x10000,Old,4096);memset(Flash+0x11000,0x55,8192);
 for(unsigned i=0x13000;i<MIG_RESCUE_OFFSET;i++)Flash[i]=(i*17)%253;
 memset(Flash+MIG_FACTORY_OFFSET,0x78,MIG_FLASH_SIZE-MIG_FACTORY_OFFSET);
 memcpy(Baseline,Flash,sizeof(Flash));memset(&Saved,0,sizeof(Saved));Uncertain=false;Error="";Step="NotStaged";Calls=FailAt=Failures=MutationCalls=0;ProtectedFlag=true;
}
static void invariant(void){assert(!memcmp(Flash,Baseline,0x10000));assert(!memcmp(Flash+0x13000,Baseline+0x13000,MIG_RESCUE_OFFSET-0x13000));assert(!memcmp(Flash+MIG_FACTORY_OFFSET,Baseline+MIG_FACTORY_OFFSET,MIG_FLASH_SIZE-MIG_FACTORY_OFFSET));}
static void stage(void){assert(MigrationStage(Rescue,sizeof(Rescue),Old,Target,Loader));assert(ProtectedFlag&&!Uncertain);invariant();}
int main(void){
 reset();assert(!MigrationCommit(Target)&&MutationCalls==0);assert(!MigrationRollback(Target)&&MutationCalls==0);
 reset();Flash[0]^=1;assert(!MigrationStage(Rescue,sizeof(Rescue),Old,Target,Loader)&&MutationCalls==0);
 reset();Flash[0x10000]^=1;assert(!MigrationStage(Rescue,sizeof(Rescue),Old,Target,Loader)&&MutationCalls==0);
 reset();stage();assert(MigrationCheckpointPresent());assert(MigrationStage(Rescue,sizeof(Rescue),Old,Target,Loader));assert(MigrationCommit(Target));assert(MigrationRestartReady(Target));
 // High NVS/OTA can change in Rescue without preventing a baseline rollback.
 Flash[MIG_NVS_OFFSET]=0;Flash[MIG_OTA_OFFSET]=0;
 assert(MigrationRollbackReady(Target));assert(MigrationRollback(Target));assert(MigrationRollbackRestartReady(Target));assert(!memcmp(Flash+0x10000,Baseline+0x10000,0x3000));invariant();
 reset();stage();assert(MigrationCommit(Target));assert(MigrationRollback(Target));assert(MigrationReleaseCheckpoint(Target));assert(!MigrationCheckpointPresent());invariant();
 reset();stage();Flash[MIG_CHECKPOINT_OFFSET]^=1;MutationCalls=0;assert(!MigrationCommit(Target)&&MutationCalls==0);
 reset();stage();Flash[MIG_FS_OFFSET]^=1;MutationCalls=0;assert(!MigrationCommit(Target)&&MutationCalls==0);
 reset();stage();Flash[MIG_OTA_OFFSET]=0;MutationCalls=0;assert(!MigrationCommit(Target)&&MutationCalls==0);
 reset();stage();assert(MigrationCommit(Target));Flash[0x11000]^=1;MutationCalls=0;assert(!MigrationRollback(Target)&&MutationCalls==0);
 reset();stage();assert(MigrationCommit(Target));Flash[MIG_MAIN_OFFSET]^=1;MutationCalls=0;assert(!MigrationRollback(Target)&&MutationCalls==0);
 reset();stage();int StageCalls=Calls;
 // Every API failure position in actual staging, including partial writes.
 for(int f=1;f<=StageCalls;f++){reset();FailAt=f;bool ok=MigrationStage(Rescue,sizeof(Rescue),Old,Target,Loader);assert(!ok);invariant();if(Uncertain){MutationCalls=0;assert(!MigrationCommit(Target)&&MutationCalls==0);}}
 reset();stage();Calls=0;assert(MigrationCommit(Target));int CommitCalls=Calls;
 for(int f=1;f<=CommitCalls;f++){reset();stage();Calls=0;FailAt=f;bool ok=MigrationCommit(Target);assert(!ok);invariant();assert(!memcmp(Flash+0x11000,Baseline+0x11000,8192));if(!Uncertain)assert(!memcmp(Flash+0x10000,Old,4096)||!memcmp(Flash+0x10000,Target,4096));}
 reset();stage();assert(MigrationCommit(Target));Calls=0;assert(MigrationRollback(Target));int RollbackCalls=Calls;
 for(int f=1;f<=RollbackCalls;f++){reset();stage();assert(MigrationCommit(Target));Calls=0;FailAt=f;bool ok=MigrationRollback(Target);assert(!ok);invariant();if(!Uncertain)assert(!memcmp(Flash+0x10000,Old,4096)||!memcmp(Flash+0x10000,Target,4096));}
 printf("Actual migration writer: %d stage, %d commit, %d rollback API fault positions; real SHA256/invariants/metadata locks passed\n",StageCalls,CommitCalls,RollbackCalls);return 0;}
'''
    (p/'test.c').write_text(harness)
    defines = [] if '--shelly-geometry' in sys.argv else ['-DMIGRATION_NODE_TEST']
    subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations'] + defines + ['-I',str(p),'-I',str(root),str(p/'test.c'),'-lcrypto','-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
