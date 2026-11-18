# VerifyLayouts.py, Version: 1.00
"""Compile the actual geometry detector for each build variant."""
import pathlib
import subprocess
import tempfile
Root = pathlib.Path(__file__).resolve().parent
MacroNames = ('APP0_SIZE', 'APP1_OFFSET', 'APP1_SIZE', 'RESCUE_OFFSET', 'RESCUE_SIZE', 'OTA_OFFSET')
for Variant, Values in (
    ('standard', (0x2A0000, 0x3A0000, 0x2A0000, 0x640000, 0x180000, 0x7E0000)),
    ('large', (0x300000, 0x400000, 0x300000, 0x700000, 0xC0000, 0x7E0000)),
    ('node', (0x100000, 0x130000, 0x100000, 0x260000, 0x140000, 0x3C0000)),
):
  Node = Variant == 'node'
  Defines = '#define DUAL_LAYOUT_NODE_TEST\n' if Node else ''
  Defines += ''.join(f'#define {Name} {Value:#x}\n' for Name, Value in zip(MacroNames, Values))
  Source = Defines + '''#include <assert.h>
#include "Layout.h"
int main(void) {
 unsigned Old[] = {2,0x20000,APP0_SIZE,APP1_OFFSET,APP1_SIZE,0,0,0x11000,0x2000,0};
 unsigned New[] = {1,''' + ('0xD0000,0x190000' if Node else 'APP1_OFFSET,APP1_SIZE') + ''',0,0,RESCUE_OFFSET,RESCUE_SIZE,OTA_OFFSET,0x2000,0};
 #define CHECK(A) DetectLayout(A[0],A[1],A[2],A[3],A[4],A[5],A[6],A[7],A[8],A[9])
 assert(CHECK(Old)==LayoutStock); assert(CHECK(New)==LayoutRescue);
 for(unsigned i=0;i<10;i++) {
  unsigned saved=Old[i]; Old[i]^=0x1000;
  if(i!=5) assert(CHECK(Old)==LayoutUnknown);
  Old[i]=saved;
  saved=New[i]; New[i]^=0x1000;
  if(i!=3) assert(CHECK(New)==LayoutUnknown);
  New[i]=saved;
 }
 return 0;
}
'''
  with tempfile.TemporaryDirectory() as Temp:
    C = pathlib.Path(Temp)/'test.c'; C.write_text(Source)
    Exe = pathlib.Path(Temp)/'test'
    subprocess.run(['cc','-std=c11','-Wall','-I',str(Root/'bootloader_components/main'),str(C),'-o',str(Exe)],check=True)
    subprocess.run([str(Exe)],check=True)
print('Actual dual-layout detector: stock/rescue and geometry mutations passed for both Shelly variants and node')
