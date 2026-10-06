// Flow.c, Version: 1.01
#include "Flow.h"
#include <stdio.h>
#include <string.h>
const char * TakeoverPhaseName(TTakeoverPhase Phase)
 {
  static const char * Names[] = { "WaitingForNetwork", "Checking", "WritingBootloader",
    "WritingRescueAndMetadata", "WritingPartitionTable", "CheckingRescueStart",
    "RescueReady", "RollingBack", "Failed", "SelectingRescue" };
  return Phase >= TakeoverWaiting && Phase <= TakeoverSelectingRescue ? Names[Phase] : "Unknown";
 }
static void Phase(TTakeoverResult * Result, const TTakeoverOps * Ops, TTakeoverPhase Value)
 {
  Result->Phase = Value;
  if( Ops->PhaseChanged ) Ops->PhaseChanged(Value);
 }
TTakeoverResult TakeoverRun(const TTakeoverOps * Ops)
 {
  TTakeoverResult Result = { .Phase = TakeoverWaiting, .DoNotRestart = true };
  Phase(&Result, Ops, TakeoverChecking);
  const char * Error = Ops->Guard();
  if( Error )
   {
    snprintf(Result.Error, sizeof(Result.Error), "%s", Error);
    Phase(&Result, Ops, TakeoverFailed);
    return Result;
   }
  bool Ok;
  // Nous already has the final layout: verify Rescue before changing its loader.
  Phase(&Result, Ops, Ops->RescueFirst ? TakeoverStaging : TakeoverLoader);
  Ok = Ops->RescueFirst ? Ops->Stage() : Ops->InstallLoader();
  if( Ok )
   {
    Phase(&Result, Ops, Ops->RescueFirst ? TakeoverLoader : TakeoverStaging);
    Ok = Ops->RescueFirst ? Ops->InstallLoader() : Ops->Stage();
   }
  if( Ok )
   {
    Phase(&Result, Ops, Ops->RescueFirst ? TakeoverSelectingRescue : TakeoverPartitionTable);
    Ok = Ops->Commit();
   }
  if( Ok ) { Phase(&Result, Ops, TakeoverFinalCheck); Ok = Ops->RestartReady(); }
  if( Ok && !Ops->Uncertain() )
   {
    Result.RescueReady = true;
    Result.DoNotRestart = false;
    Phase(&Result, Ops, TakeoverRescueReady);
    return Result;
   }
  Error = Ops->Error();
  snprintf(Result.Error, sizeof(Result.Error), "%s", Error && Error[0] ? Error : "Takeover verification failed");
  // Never ask a normal rollback writer to operate on uncertain flash/protection.
  if( !Ops->Uncertain() )
   {
    Phase(&Result, Ops, TakeoverRollingBack);
    Result.RollbackVerified = Ops->Rollback();
    Result.DoNotRestart = !Result.RollbackVerified || Ops->Uncertain();
   }
  Phase(&Result, Ops, TakeoverFailed);
  return Result;
 }
