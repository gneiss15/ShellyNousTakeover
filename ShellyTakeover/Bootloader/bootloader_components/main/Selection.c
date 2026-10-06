// Selection.c, Version: 1.01
#include "Selection.h"
#include "BootState.h"

int SelectStockLayoutApp(bool KeyPressed, const uint8_t * Sectors)
 {
  if( KeyPressed || Sectors == 0 )
    return 0;
  const int Selected = SelectBootState(Sectors);
  if( Selected < 0 )
    return 0; // Invalid or ambiguous metadata selects stock conservatively.
  TBootState State;
  const uint8_t * Record = Sectors + Selected * BOOT_STATE_SECTOR_SIZE;
  DecodeBootState(Record, &State);
  if( State.ActiveSlot > 1 || State.ReserveSlot > 1 ||
      State.ActiveSlot == State.ReserveSlot || (Record[0x1D0] & 0x0C) != 0 )
    return 0;
  // Preserve the explicit software stock request used by Readout and its updater.
  if( State.ActiveSlot == 0 )
    return 0;
  return 1; // No countdown. A stock start has a separate metadata consistency gate.
 }
