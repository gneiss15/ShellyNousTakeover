#!/usr/bin/env python3
# VerifyPlatformActions.py, Version: 1.00
"""Compile actual platform action adapters and inject their writer outcomes."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parent.parent
source=(root/'ShellyTakeover/App/main/Platform.c').read_text()
a=source.index('static bool InstallLoader(void)');b=source.index('\nstatic const TTakeoverOps Ops',a)
functions=source[a:b]
prelude=r'''
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <assert.h>
#define TAKEOVER_RESCUE_SIZE 100
#define LOADER_WRITE_SPAN 24576
static uint8_t OriginalLoader[24576],CandidateLoader[24576],RescuePayload[100],OldTable[4096],NewTable[4096],BootSectors[8192];
static bool LoaderChanged,LoaderUncertain,BaselineValid=true;
static const char * LastError="";
typedef struct {bool TargetVerified,RollbackVerified,ProtectionRestored,InvariantsVerified,DoNotRestart;} TLoaderWriteResult;
static TLoaderWriteResult Writer={true,false,true,true,false};
static bool FinalLoader=false,PreservedOk=true,Checkpoint=false,TableNew=false,TableOld=true,StateOk=true,RollbackOk=true,ReleaseOk=true,MigrationUnsafe=false,RestartOk=true;
static int LoaderWrites,TableRollbacks,Releases;
bool LoaderMatches(const uint8_t*p){return p==CandidateLoader?FinalLoader:!FinalLoader;}
bool Preserved(void){return BaselineValid&&PreservedOk;}
TLoaderWriteResult WriteBoundedLoader(const uint8_t*e,const uint8_t*t,bool retry){(void)e;assert(!retry);LoaderWrites++;if(Writer.TargetVerified)FinalLoader=t==CandidateLoader;return Writer;}
bool MigrationStage(const uint8_t*r,uint32_t n,const uint8_t*o,const uint8_t*t,const uint8_t*l){assert(r==RescuePayload&&n==100&&o==OldTable&&t==NewTable&&l==CandidateLoader);return true;}
bool MigrationCommit(const uint8_t*t){assert(t==NewTable);return true;}
bool MigrationRestartReady(const uint8_t*t){assert(t==NewTable);return RestartOk;}
bool MigrationUncertain(void){return MigrationUnsafe;}
const char *MigrationError(void){return "injected migration error";}
bool MigrationCheckpointPresent(void){return Checkpoint;}
bool Matches(uint32_t o,const uint8_t*d,uint32_t n){if(o==0x10000){assert(n==4096);return d==NewTable?TableNew:TableOld;}assert(o==0x11000&&d==BootSectors&&n==8192);return StateOk;}
bool MigrationRollback(const uint8_t*t){assert(t==NewTable);TableRollbacks++;if(RollbackOk){TableNew=false;TableOld=true;}return RollbackOk;}
bool MigrationReleaseCheckpoint(const uint8_t*t){assert(t==NewTable);Releases++;return ReleaseOk;}
'''
tests=r'''
int main(void){
 assert(InstallLoader()&&LoaderChanged&&LoaderWrites==1&&FinalLoader);
 assert(InstallLoader()&&LoaderWrites==1);assert(Stage()&&Commit()&&Ready());
 PreservedOk=false;assert(!Ready()&&!Rollback());PreservedOk=true;
 Checkpoint=true;TableNew=true;TableOld=false;assert(Rollback()&&TableRollbacks==1&&Releases==1&&LoaderWrites==2&&!FinalLoader);
 TableNew=true;TableOld=false;RollbackOk=false;LoaderWrites=0;Releases=0;assert(!Rollback()&&LoaderWrites==0&&Releases==0);
 TableNew=false;TableOld=true;RollbackOk=true;ReleaseOk=false;assert(!Rollback()&&LoaderWrites==0);
 Checkpoint=false;ReleaseOk=true;StateOk=false;assert(!Rollback());StateOk=true;
 MigrationUnsafe=true;assert(Uncertain()&&!Rollback());MigrationUnsafe=false;
 Writer=(TLoaderWriteResult){false,true,true,true,false};FinalLoader=false;LoaderChanged=false;assert(!InstallLoader()&&!LoaderUncertain);
 Writer.DoNotRestart=true;assert(!InstallLoader()&&LoaderUncertain&&!Rollback());
 assert(Error()[0]);
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'test.c').write_text(prelude+functions+tests)
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('Actual platform adapters passed: loader skip/write/failure, full rollback order, failed table/metadata rollback, SH0S mismatch, uncertainty lock.')
