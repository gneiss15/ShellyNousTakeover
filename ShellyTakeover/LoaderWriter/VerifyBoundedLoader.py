# VerifyBoundedLoader.py, Version: 1.01
"""Fault-test the production writer implementation, including explicit repair."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parent
source=(root/'LoaderWriter.c').read_text().replace('#include "esp_flash.h"','').replace('#include "esp_flash_internal.h"','')
header=r'''
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
#define ESP_OK 0
static void * esp_flash_default_chip;
static uint8_t Flash[0x13000], Original[0x6000], Candidate[0x6000];
static unsigned Calls, Fail1, Fail2, Erases, Writes, Corrupt;
static bool Protected;
static bool fail(void){++Calls;return Calls==Fail1||Calls==Fail2;}
static int esp_flash_read(void*c,void*p,unsigned a,unsigned n){(void)c;assert(a+n<=sizeof(Flash));if(fail())return -1;memcpy(p,Flash+a,n);if(Calls==Corrupt)((uint8_t*)p)[0]^=1;return 0;}
static int esp_flash_set_dangerous_write_protection(void*c,bool b){(void)c;if(fail())return -1;Protected=b;return 0;}
static int esp_flash_erase_region(void*c,unsigned a,unsigned n){(void)c;assert(!Protected&&a==0&&n==0x6000);++Erases;if(fail())return -1;memset(Flash,255,n);return 0;}
static int esp_flash_write(void*c,const void*p,unsigned a,unsigned n){(void)c;assert(!Protected&&a==0&&n==0x6000);++Writes;if(fail()){memcpy(Flash,p,n/2);return -1;}memcpy(Flash,p,n);return 0;}
'''
tests=r'''
static void reset(void){memset(Original,0xaa,sizeof(Original));memset(Candidate,0xbb,sizeof(Candidate));memset(Flash,0x55,sizeof(Flash));memcpy(Flash,Original,sizeof(Original));Calls=Fail1=Fail2=Erases=Writes=Corrupt=0;Protected=true;SnapshotValid=false;}
static void invariants(void){for(unsigned i=0x6000;i<sizeof(Flash);i++)assert(Flash[i]==0x55);}
int main(void){
 reset();TLoaderWriteResult r=WriteBoundedLoader(Original,Candidate,false);assert(r.TargetVerified&&!r.DoNotRestart&&r.ProtectionRestored&&r.InvariantsVerified);assert(Protected&&Erases==1&&Writes==1);assert(memcmp(Flash,Candidate,0x6000)==0);unsigned count=Calls;assert(count==30);invariants();
 for(unsigned stage=1;stage<=count;stage++){
  reset();Fail1=stage;r=WriteBoundedLoader(Original,Candidate,false);assert(!r.TargetVerified||r.DoNotRestart);invariants();
  if(stage<=18){assert(Erases==0&&Writes==0&&memcmp(Flash,Original,0x6000)==0);}
  if(stage>=19&&stage<=26){assert(r.RollbackVerified&&!r.DoNotRestart&&memcmp(Flash,Original,0x6000)==0);}
  if(stage>=27)assert(r.DoNotRestart);
 }
 reset();Original[0]^=1;r=WriteBoundedLoader(Original,Candidate,false);assert(!r.TargetVerified&&Erases==0&&Writes==0);
 reset();Corrupt=21;r=WriteBoundedLoader(Original,Candidate,false);assert(r.RollbackVerified&&!r.DoNotRestart);invariants();
 reset();Fail1=20;Fail2=22;r=WriteBoundedLoader(Original,Candidate,false);assert(r.DoNotRestart&&!r.RollbackVerified);invariants();
 Calls=Fail1=Fail2=Corrupt=0;r=WriteBoundedLoader(NULL,Original,true);assert(r.TargetVerified&&!r.DoNotRestart&&memcmp(Flash,Original,0x6000)==0);invariants();
 reset();r=WriteBoundedLoader(NULL,Original,true);assert(r.DoNotRestart&&Erases==0&&Writes==0);
 reset();Fail1=20;Fail2=22;r=WriteBoundedLoader(Original,Candidate,false);assert(r.DoNotRestart);Flash[0x11000]^=1;Calls=Fail1=Fail2=0;unsigned before=Erases;r=WriteBoundedLoader(NULL,Original,true);assert(r.DoNotRestart&&Erases==before);
 return 0;}
'''
with tempfile.TemporaryDirectory() as work:
    p=Path(work);(p/'test.c').write_text(header+source+tests)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(root),str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
print('Production writer: 30 API fault points, bounds, rollback, mismatch, explicit retry and invariant gates passed')
