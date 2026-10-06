#!/usr/bin/env python3
# VerifyStockRequest.py, Version: 1.01
"""Fault-test the actual candidate stock-state writer and shared SH0S code."""
from pathlib import Path
import subprocess
import tempfile
import zlib

root = Path(__file__).resolve().parent
shared = root / "bootloader_components"
def synthetic_record():
    data = bytearray(512)
    data[:4] = data[12:16] = (10).to_bytes(4, 'little')
    data[8:12] = b'SH0S'
    data[0x1d0:0x1d2] = bytes([0x12, 0x20])
    data[28:32] = zlib.crc32(bytes(4), zlib.crc32(data[:28], 0xffffffff)).to_bytes(4, 'little')
    data[508:512] = zlib.crc32(data[:508], 0xffffffff).to_bytes(4, 'little')
    return bytes(data)

fixture = synthetic_record()
def repaired(data):
    data[28:32] = zlib.crc32(bytes(4), zlib.crc32(data[:28], 0xffffffff)).to_bytes(4, "little")
    data[508:512] = zlib.crc32(data[:508], 0xffffffff).to_bytes(4, "little")
    return data
conflict = bytearray(fixture)
conflict[0x1d0:0x1d2] = bytes([1, 1])
conflict = repaired(conflict)
wrapped = bytearray(fixture)
wrapped[:4] = wrapped[12:16] = bytes([255]) * 4
wrapped = repaired(wrapped)
header = '''#include <stdbool.h>
#include <stddef.h>
#define ESP_OK 0
int bootloader_flash_read(size_t,void*,size_t,bool);
int bootloader_flash_write(size_t,void*,size_t,bool);
int bootloader_flash_erase_sector(size_t);
'''
harness = r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "BootState.h"
#include "StockRequest.h"
static uint8_t flash[8192],snapshot[8192];
static int fail,reads,writes,erases;
int bootloader_flash_read(size_t address,void*out,size_t size,bool decrypt){
 assert(!decrypt && address>=0x11000 && address+size<=0x13000);
 reads++;if((fail==1&&reads==1)||(fail==4&&reads==17))return 1;
 memcpy(out,flash+address-0x11000,size);
 if((fail==6&&reads==1)||(fail==5&&reads==17))((uint8_t*)out)[100]^=1;
 return 0;
}
int bootloader_flash_erase_sector(size_t sector){
 assert(sector==0x11||sector==0x12);erases++;
 if(fail==2)return 1;
 memset(flash+(sector-0x11)*4096,255,4096);return 0;
}
int bootloader_flash_write(size_t address,void*in,size_t size,bool encrypt){
 assert(!encrypt && (address==0x11000||address==0x12000) && size==4096);
 writes++;memcpy(flash+address-0x11000,in,fail==3?128:size);
 return fail==3?1:0;
}
int main(void){
 for(int copy=0;copy<2;copy++)for(fail=0;fail<=6;fail++){
  memset(snapshot,255,sizeof(snapshot));memcpy(snapshot+copy*4096,fixture,512);
  memcpy(flash,snapshot,sizeof(flash));reads=writes=erases=0;
  bool ok=EnsureStockBootState(snapshot);assert(ok==(fail==0));
  assert(memcmp(flash+copy*4096,snapshot+copy*4096,4096)==0);
  if(fail==1||fail==6)assert(erases==0&&writes==0);
  if(ok){TBootState state;int selected=SelectBootState(flash);assert(selected==1-copy);
   DecodeBootState(flash+selected*4096,&state);assert(state.ActiveSlot==0&&state.Committed==1);
   memcpy(snapshot,flash,sizeof(snapshot));reads=writes=erases=0;
   assert(EnsureStockBootState(snapshot));assert(reads==0&&writes==0&&erases==0);
  }
 }
 // Both CRC-valid records with the same sequence but different flags are ambiguous.
 memset(snapshot,255,sizeof(snapshot));memcpy(snapshot,fixture,512);memcpy(snapshot+4096,conflict,512);
 reads=writes=erases=0;assert(SelectBootState(snapshot)==-1);
 assert(!EnsureStockBootState(snapshot));assert(reads==0&&writes==0&&erases==0);
 // Sequence wrap must be rejected before erasing anything.
 memset(snapshot,255,sizeof(snapshot));memcpy(snapshot,wrapped,512);
 reads=writes=erases=0;assert(SelectBootState(snapshot)==0);
 assert(!EnsureStockBootState(snapshot));assert(reads==0&&writes==0&&erases==0);
 memset(snapshot,0,sizeof(snapshot));reads=writes=erases=0;
 assert(!EnsureStockBootState(snapshot));assert(writes==0&&erases==0);
 return 0;
}
'''
with tempfile.TemporaryDirectory() as work:
    path = Path(work)
    (path / "bootloader_flash_priv.h").write_text(header)
    arrays = ''.join('static const unsigned char ' + name + '[]={' +
                     ','.join(str(value) for value in data) + '};\n'
                     for name, data in [('fixture', fixture), ('conflict', conflict), ('wrapped', wrapped)])
    (path / "test.c").write_text('#include <stddef.h>\n' + arrays + harness)
    exe = path / "test"
    subprocess.run(["cc", "-Wall", "-Wextra", "-Werror", "-I", str(path),
                    "-I", str(shared / "main"), "-I", str(root / "bootloader_components/main"),
                    str(path / "test.c"), str(root / "bootloader_components/main/StockRequest.c"),
                    str(shared / "main/BootState.c"), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
print("Actual stock-state writer: both winning copies, 6 failure stages, preservation and no-op checks passed")
