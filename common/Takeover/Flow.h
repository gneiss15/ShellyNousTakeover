// Flow.h, Version: 1.01
#pragma once
#include <stdbool.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef enum
 {
  TakeoverWaiting, TakeoverChecking, TakeoverLoader, TakeoverStaging,
  TakeoverPartitionTable, TakeoverFinalCheck, TakeoverRescueReady,
  TakeoverRollingBack, TakeoverFailed, TakeoverSelectingRescue
 } TTakeoverPhase;
typedef struct
 {
  const char * (*Guard)(void);
  bool (*InstallLoader)(void);
  bool (*Stage)(void);
  bool (*Commit)(void);
  bool (*RestartReady)(void);
  bool (*Uncertain)(void);
  bool (*Rollback)(void);
  const char * (*Error)(void);
  void (*PhaseChanged)(TTakeoverPhase Phase);
  bool RescueFirst;
 } TTakeoverOps;
typedef struct
 {
  TTakeoverPhase Phase;
  bool RescueReady, RollbackVerified, DoNotRestart;
  char Error[192];
 } TTakeoverResult;
TTakeoverResult TakeoverRun(const TTakeoverOps * Ops);
const char * TakeoverPhaseName(TTakeoverPhase Phase);
#ifdef __cplusplus
}
#endif
