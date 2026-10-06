// bootloader_start.c, Version: 1.01
#include <sys/reent.h>
#include <string.h>
#include "ExpectedTables.h"
#include "sdkconfig.h"
#include "bootloader_init.h"
#include "bootloader_utility.h"
#include "bootloader_common.h"
#include "bootloader_flash_priv.h"
#include "esp_rom_sys.h"
#include "esp_secure_boot.h"
#include "esp_flash_encrypt.h"
#include "Selection.h"
#include "BootState.h"
#include "StockRequest.h"

#ifndef DUAL_LAYOUT_NODE_TEST
#define APP0_SIZE 0x2A0000
#define APP1_OFFSET 0x3A0000
#define APP1_SIZE 0x2A0000
#define RESCUE_OFFSET 0x640000
#define RESCUE_SIZE 0x180000
#define OTA_OFFSET 0x7E0000
#else
#define APP0_SIZE 0x100000
#define APP1_OFFSET 0x130000
#define APP1_SIZE 0x100000
#define RESCUE_OFFSET 0x260000
#define RESCUE_SIZE 0x140000
#define OTA_OFFSET 0x3C0000
#endif
#include "Layout.h"

static uint8_t BootSectors[2 * BOOT_STATE_SECTOR_SIZE] __attribute__((aligned(4)));

void __attribute__((noreturn)) call_start_cpu0(void)
 {
  if( bootloader_init() != ESP_OK )
    bootloader_reset();
  if( esp_secure_boot_enabled() || esp_flash_encryption_enabled() )
    bootloader_reset();
  bootloader_state_t State = { 0 };
  if( !bootloader_utility_load_partition_table(&State) )
    bootloader_reset();
  const int Layout = DetectLayout(State.app_count, State.ota[0].offset,
    State.ota[0].size, State.ota[1].offset, State.ota[1].size,
    State.factory.offset, State.factory.size, State.ota_info.offset,
    State.ota_info.size, State.test.size);
  if( Layout == LayoutUnknown )
    bootloader_reset();
  if( bootloader_flash_read(0x10000, BootSectors, 4096, false) != ESP_OK )
    bootloader_reset();
  const unsigned char * Expected = Layout == LayoutStock ? StockTable : RescueTable;
  const unsigned Length = Layout == LayoutStock ? sizeof(StockTable) : sizeof(RescueTable);
  if( memcmp(BootSectors, Expected, Length) != 0 ) bootloader_reset();
  for( unsigned Index = Length; Index < 4096; ++Index )
    if( BootSectors[Index] != 0xFF ) bootloader_reset();
  // GPIO input with pull-up; LOW must persist for one second.
  const bool KeyPressed = bootloader_common_check_long_hold_gpio(7, 1) == GPIO_LONG_HOLD;
  if( Layout == LayoutRescue )
   {
    // Validate Rescue before changing boot metadata. Never use retired SH0S.
    esp_image_metadata_t RescueImage = { 0 };
    if( esp_image_verify(ESP_IMAGE_VERIFY, &State.factory, &RescueImage) != ESP_OK )
      bootloader_reset();
    if( KeyPressed )
      for( unsigned Offset = OTA_OFFSET; Offset < OTA_OFFSET + 0x2000; Offset += 4096 )
       {
        if( bootloader_flash_erase_sector(Offset / 4096) != ESP_OK ||
            bootloader_flash_read(Offset, BootSectors, 4096, false) != ESP_OK )
          bootloader_reset();
        for( unsigned Index = 0; Index < 4096; ++Index )
          if( BootSectors[Index] != 0xFF ) bootloader_reset();
       }
    const int Selected = bootloader_utility_get_selected_boot_partition(&State);
    esp_rom_printf("DualLayoutBootloader 0.01: rescue key=%d selected=%d\n", KeyPressed, Selected);
    bootloader_utility_load_boot_image(&State, Selected);
   }
  const bool ReadOk = bootloader_flash_read(0x11000, BootSectors,
    sizeof(BootSectors), false) == ESP_OK;
  if( !ReadOk )
    bootloader_reset();
  int App = SelectStockLayoutApp(KeyPressed, BootSectors);
  esp_image_metadata_t Image = { 0 };
  if( esp_image_verify(ESP_IMAGE_VERIFY, &State.ota[App], &Image) != ESP_OK )
   {
    if( App == 0 || esp_image_verify(ESP_IMAGE_VERIFY, &State.ota[0], &Image) != ESP_OK )
      bootloader_reset();
    App = 0;
   }
  // Stock startup also uses SH0S for previous-slot filesystem handling. Align
  // metadata before a button/fallback start; never boot stock after failed repair.
  if( App == 0 && !EnsureStockBootState(BootSectors) )
    bootloader_reset();
  esp_rom_printf("DualLayoutBootloader 0.01: key=%d app_%d\n", KeyPressed, App);
#ifdef DUAL_LAYOUT_NODE_TEST
  esp_rom_printf("NODE_LOADER_WRITE_TRIAL\n");
#endif
  // Do not call the standard OTA selector: SH0S is not ESP-IDF otadata.
  // Without that call, IDF's ota_has_initial_contents remains false and the
  // image loader does not initialize or overwrite the SH0S sectors.
  // Disable implicit IDF fallback: every stock start must pass the metadata gate.
  State.ota[1 - App].size = 0;
  bootloader_utility_load_boot_image(&State, App);
 }

#if CONFIG_LIBC_NEWLIB
struct _reent * __getreent(void)
 {
  return _GLOBAL_REENT;
 }
#endif
