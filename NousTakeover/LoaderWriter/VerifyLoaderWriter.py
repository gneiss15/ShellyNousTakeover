# VerifyLoaderWriter.py, Version: 1.00
"""Fault-test actual Nous writer; synthetic flash, no device access."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parent
source = (root / 'LoaderWriter.c').read_text().replace('#include "esp_flash.h"', '').replace('#include "esp_flash_internal.h"', '')
harness = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define ESP_OK 0
static void * esp_flash_default_chip;
static uint8_t Flash[0x10000], Expected[0x7000], Target[0x7000], Baseline[0x10000];
static unsigned Calls, Fail1, Fail2, Corrupt, Erases, Writes, Mutate;
static bool Protected;
static bool fail(void) { return ++Calls == Fail1 || Calls == Fail2; }
static int esp_flash_read(void * c, void * p, unsigned a, unsigned n) {
 (void)c; assert(a + n <= sizeof(Flash)); if(fail()) return -1;
 memcpy(p, Flash + a, n); if(Calls == Corrupt) ((uint8_t *)p)[0] ^= 1; return 0;
}
static int esp_flash_set_dangerous_write_protection(void * c, bool value) {
 (void)c; if(fail()) return -1; Protected = value; return 0;
}
static int esp_flash_erase_region(void * c, unsigned a, unsigned n) {
 (void)c; assert(!Protected && a == 0x1000 && n == 0x7000); ++Erases;
 if(fail()) { memset(Flash + a, 255, n / 2); return -1; }
 memset(Flash + a, 255, n); return 0;
}
static int esp_flash_write(void * c, const void * p, unsigned a, unsigned n) {
 (void)c; assert(!Protected && a >= 0x1000 && a + n <= 0x8000 && n == 4096); ++Writes;
 bool failed = fail(); memcpy(Flash + a, p, failed ? n / 2 : n);
 if(Calls == Mutate) Flash[0xE000] ^= 1;
 return failed ? -1 : 0;
}
'''
tests = r'''
static void reset(void) {
 for(unsigned i = 0; i < sizeof(Flash); ++i) Flash[i] = (uint8_t)(i * 17 + (i >> 8));
 memset(Expected, 0xaa, sizeof(Expected)); memset(Target, 0xbb, sizeof(Target));
 memcpy(Flash + 0x1000, Expected, sizeof(Expected)); memcpy(Baseline, Flash, sizeof(Flash));
 Calls = Fail1 = Fail2 = Corrupt = Erases = Writes = Mutate = 0; Protected = true;
}
static void preserved(void) {
 assert(!memcmp(Flash, Baseline, 0x1000));
 assert(!memcmp(Flash + 0x8000, Baseline + 0x8000, sizeof(Flash) - 0x8000));
}
int main(void) {
 reset(); TNousLoaderResult r = NousWriteLoader(Expected, Target, true, true);
 assert(r.TargetVerified && r.InvariantsVerified && r.ProtectionRestored && !r.DoNotRestart);
 assert(Protected && Erases == 1 && Writes == 7 && !memcmp(Flash + 0x1000, Target, sizeof(Target)));
 unsigned total = Calls; assert(total == 34); preserved();
 for(unsigned point = 1; point <= total; ++point) {
  reset(); Fail1 = point; r = NousWriteLoader(Expected, Target, true, true); preserved();
  if(point <= 15) assert(Erases == 0 && Writes == 0 && r.DoNotRestart);
  else if(point <= 30) {
   assert(r.RollbackVerified && !r.TargetVerified && !r.DoNotRestart && Protected);
   assert(!memcmp(Flash + 0x1000, Expected, sizeof(Expected)));
  } else assert(r.DoNotRestart);
 }
 // Every readback block can detect a bit mismatch and restore the original.
 for(unsigned point = 24; point <= 30; ++point) {
  reset(); Corrupt = point; r = NousWriteLoader(Expected, Target, true, true);
  assert(r.RollbackVerified && !r.TargetVerified && !r.DoNotRestart); preserved();
 }
 // Erase, each write/readback, protection and invariant failures during rollback.
 reset(); Fail1 = 16; r = NousWriteLoader(Expected, Target, true, true);
 unsigned rollbackEnd = Calls; assert(r.RollbackVerified);
 for(unsigned point = 17; point <= rollbackEnd; ++point) {
  reset(); Fail1 = 16; Fail2 = point; r = NousWriteLoader(Expected, Target, true, true);
  assert(!r.TargetVerified && r.DoNotRestart); preserved();
 }
 // Rejected prerequisites and stale identity cannot cause any erase/write.
 for(unsigned denied = 0; denied < 4; ++denied) {
  reset(); r = NousWriteLoader(denied == 0 ? NULL : Expected, denied == 1 ? NULL : Target, denied != 2, denied != 3);
  assert(r.DoNotRestart && Calls == 0 && Erases == 0 && Writes == 0); preserved();
 }
 reset(); Expected[0] ^= 1; r = NousWriteLoader(Expected, Target, true, true);
 assert(r.DoNotRestart && Erases == 0 && Writes == 0); preserved();
 reset(); memcpy(Target, Expected, sizeof(Target)); r = NousWriteLoader(Expected, Target, true, true);
 assert(r.TargetVerified && !r.DoNotRestart && Erases == 0 && Writes == 0); preserved();
 // Unknown OTA selection stops rollback; no second erase is allowed.
 reset(); Fail1 = Mutate = 17; r = NousWriteLoader(Expected, Target, true, true);
 assert(r.DoNotRestart && !r.RollbackVerified && Erases == 1 && Protected);
 assert(!memcmp(Flash, Baseline, 0x1000) && !memcmp(Flash + 0x8000, Baseline + 0x8000, 0x6000));
 printf("Nous writer passed: %u normal API fault positions, %u rollback fault positions, partial erase/write, seven corrupt readbacks, identity/Rescue gates, bounds and unchanged metadata.\n", total, rollbackEnd - 16);
}
'''
with tempfile.TemporaryDirectory() as directory:
    work = Path(directory)
    (work / 'test.c').write_text(harness + source + tests)
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-I', str(root), str(work / 'test.c'), '-o', str(work / 'test')], check=True)
    subprocess.run([str(work / 'test')], check=True)
