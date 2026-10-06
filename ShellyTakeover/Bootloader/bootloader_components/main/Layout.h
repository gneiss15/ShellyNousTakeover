// Layout.h, Version: 1.00
#pragma once
enum { LayoutUnknown, LayoutStock, LayoutRescue };
// Only the explicitly built geometry is accepted. No guessed app addresses.
static inline int DetectLayout(unsigned Count, unsigned MainOffset, unsigned MainSize,
  unsigned SecondOffset, unsigned SecondSize, unsigned FactoryOffset,
  unsigned FactorySize, unsigned OtaOffset, unsigned OtaSize, unsigned TestSize)
 {
  if( TestSize != 0 || OtaSize != 0x2000 ) return LayoutUnknown;
  if( Count == 2 && MainOffset == 0x20000 && MainSize == APP0_SIZE &&
      SecondOffset == APP1_OFFSET && SecondSize == APP1_SIZE &&
      FactorySize == 0 && OtaOffset == 0x11000 ) return LayoutStock;
#ifndef DUAL_LAYOUT_NODE_TEST
  if( Count == 1 && MainOffset == APP1_OFFSET && MainSize == APP1_SIZE &&
#else
  if( Count == 1 && MainOffset == 0xD0000 && MainSize == 0x190000 &&
#endif
      SecondSize == 0 && FactoryOffset == RESCUE_OFFSET &&
      FactorySize == RESCUE_SIZE && OtaOffset == OTA_OFFSET ) return LayoutRescue;
  return LayoutUnknown;
 }
