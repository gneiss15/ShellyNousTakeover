#!/usr/bin/env python3
# VerifyTakeoverFlow.py, Version: 1.01
"""Compile actual automatic flow and fault every step; no device access."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parent.parent
harness=r'''
#include "Flow.h"
#include <assert.h>
#include <string.h>
static int Position, Fail, Rollbacks;
static bool Unknown, Unsafe, RollbackOk=true;
static const char * ErrorText="original failure";
static const char * guard(void) { return Unknown ? "unsupported device" : 0; }
static bool step(void) { return ++Position!=Fail; }
static bool uncertain(void) { return Unsafe; }
static bool rollback(void) { Rollbacks++; ErrorText="rollback status"; return RollbackOk; }
static const char * error(void) { return ErrorText; }
static TTakeoverOps Ops={guard,step,step,step,step,uncertain,rollback,error,0,false};
int main(void) {
 TTakeoverResult result=TakeoverRun(&Ops); assert(result.RescueReady&&!result.DoNotRestart&&Position==4&&Rollbacks==0);
 Position=0;Unknown=true;result=TakeoverRun(&Ops);assert(result.Phase==TakeoverFailed&&result.DoNotRestart&&Position==0&&Rollbacks==0);Unknown=false;
 for(int fail=1;fail<=4;fail++) {
  Position=0;Fail=fail;Rollbacks=0;Unsafe=false;ErrorText="original failure";
  result=TakeoverRun(&Ops);assert(!result.RescueReady&&result.RollbackVerified&&!result.DoNotRestart&&Rollbacks==1&&Position==fail);
  assert(!strcmp(result.Error,"original failure"));
  Position=0;Rollbacks=0;Unsafe=true;result=TakeoverRun(&Ops);assert(result.DoNotRestart&&Rollbacks==0&&!result.RollbackVerified);
 }
 Position=0;Fail=2;Unsafe=false;RollbackOk=false;result=TakeoverRun(&Ops);assert(result.DoNotRestart&&!result.RollbackVerified);
 Position=0;Fail=0;Unsafe=true;result=TakeoverRun(&Ops);assert(!result.RescueReady&&result.DoNotRestart);
}
'''
ordering=r'''
#include "Flow.h"
#include <assert.h>
#include <string.h>
static char Trace[8]; static unsigned Count, Fail;
static TTakeoverPhase Current, CommitPhase;
static const char * guard(void) { return 0; }
static bool action(char Code, TTakeoverPhase Expected) { assert(Current==Expected);Trace[Count++]=Code;return Count!=Fail; }
static bool loader(void) { return action('L',TakeoverLoader); }
static bool stage(void) { return action('S',TakeoverStaging); }
static bool commit(void) { return action('C',CommitPhase); }
static bool ready(void) { return action('R',TakeoverFinalCheck); }
static bool uncertain(void) { return false; }
static bool rollback(void) { assert(Current==TakeoverRollingBack);Trace[Count++]='B';return true; }
static const char * error(void) { return "failure"; }
static void phase(TTakeoverPhase Phase) { Current=Phase; }
int main(void) {
 for(unsigned nous=0;nous<2;++nous) {
  TTakeoverOps Ops={guard,loader,stage,commit,ready,uncertain,rollback,error,phase,nous!=0};
  CommitPhase=nous?TakeoverSelectingRescue:TakeoverPartitionTable;
  const char * Order=nous?"SLCR":"LSCR";
  for(Fail=0;Fail<=4;++Fail) {
   Count=0;memset(Trace,0,sizeof(Trace));TTakeoverResult Result=TakeoverRun(&Ops);
   if(!Fail) assert(Result.RescueReady&&!strcmp(Trace,Order));
   else { assert(!Result.RescueReady&&Result.RollbackVerified&&Count==Fail+1);assert(!memcmp(Trace,Order,Fail)&&Trace[Fail]=='B'); }
  }
 }
 assert(!strcmp(TakeoverPhaseName(TakeoverSelectingRescue),"SelectingRescue"));
}
'''
with tempfile.TemporaryDirectory() as t:
    work=Path(t); (work/'test.c').write_text(harness)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(root/'common/Takeover'),str(work/'test.c'),str(root/'common/Takeover/Flow.c'),'-o',str(work/'test')],check=True)
    subprocess.run([str(work/'test')],check=True)
    (work/'ordering.c').write_text(ordering)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(root/'common/Takeover'),str(work/'ordering.c'),str(root/'common/Takeover/Flow.c'),'-o',str(work/'ordering')],check=True)
    subprocess.run([str(work/'ordering')],check=True)
print('Actual automatic flow passed: Shelly/Nous order and phases, guard denial, each failed step, uncertainty, rollback success/failure, original error retained.')
