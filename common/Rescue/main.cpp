// main.cpp, Version: 1.00
#include "Arduino.h"
#include "Platform.h"
#include "RescueGuard.h"
#include "esp_chip_info.h"
#include "esp_flash.h"
#include "esp_flash_encrypt.h"
#include "esp_secure_boot.h"
#include "esp_ota_ops.h"
#include "esp_image_format.h"
#include "nvs_flash.h"
#include "sdkconfig.h"
#include <cstdio>
#include <cstring>
static_assert(CONFIG_PARTITION_TABLE_OFFSET == RESCUE_TABLE_OFFSET, "Wrong SDK partition-table offset");
namespace
 {
  bool GeometryValid = false;
  bool PartitionMatches(esp_partition_type_t Type, esp_partition_subtype_t Subtype,
    const char * Label, uint32_t Address, uint32_t Size)
   {
    const esp_partition_t * Part = esp_partition_find_first(Type, Subtype, Label);
    return Part && !Part->readonly && Part->address == Address && Part->size == Size;
   }
 }
bool RescueGeometryValid(void) { return GeometryValid; }
char const * RescueMainError(void)
 {
  if( !GeometryValid ) return "Geometry rejected; Main disabled";
  const esp_partition_t * Main = esp_partition_find_first(ESP_PARTITION_TYPE_APP, ESP_PARTITION_SUBTYPE_APP_OTA_0, nullptr);
  esp_app_desc_t Description = {};
  if( !Main || esp_ota_get_partition_description(Main, &Description) != ESP_OK )
    return "Main is not installed";
  // Transition apps remain physically present after takeover, but are not Main.
  if( strncmp(Description.project_name, "ShellyTakeover", 14) == 0 ||
      strncmp(Description.project_name, "NousTakeover", 12) == 0 ||
      strncmp(Description.project_name, "ShellyReadout", 13) == 0 ||
      strncmp(Description.project_name, "TmrSwA8TTasmotaMigration", 23) == 0 )
    return "Main is not installed; transition image rejected";
  esp_partition_pos_t Position = { Main->address, Main->size };
  esp_image_metadata_t Image = {};
  return esp_image_verify(ESP_IMAGE_VERIFY, &Position, &Image) == ESP_OK ? nullptr : "Main image invalid";
 }
void setup(void);
void loop(void);
extern "C" void app_main(void)
 {
  esp_chip_info_t Chip = {};
  esp_chip_info(&Chip);
  uint32_t Size = 0;
  const esp_partition_t * Running = esp_ota_get_running_partition();
  GeometryValid = Chip.model == RESCUE_CHIP && esp_flash_get_physical_size(nullptr, &Size) == ESP_OK &&
    Size == RESCUE_FLASH_SIZE && !esp_secure_boot_enabled() && !esp_flash_encryption_enabled() &&
    Running && Running->type == ESP_PARTITION_TYPE_APP && Running->subtype == ESP_PARTITION_SUBTYPE_APP_FACTORY &&
    !Running->readonly && Running->address == RESCUE_RESCUE_OFFSET && Running->size == RESCUE_RESCUE_SIZE &&
    PartitionMatches(ESP_PARTITION_TYPE_APP, ESP_PARTITION_SUBTYPE_APP_OTA_0, nullptr, RESCUE_MAIN_OFFSET, RESCUE_MAIN_SIZE) &&
    PartitionMatches(ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_DATA_SPIFFS, nullptr, RESCUE_FS_OFFSET, RESCUE_FS_SIZE) &&
    PartitionMatches(ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_DATA_NVS, "nvs", RESCUE_NVS_OFFSET, RESCUE_NVS_SIZE) &&
    PartitionMatches(ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_DATA_OTA, nullptr, RESCUE_OTA_OFFSET, 0x2000);
#if CONFIG_IDF_TARGET_ESP32C3
  GeometryValid = GeometryValid && Chip.revision == 4;
#endif
  if( GeometryValid && nvs_flash_init() != ESP_OK ) GeometryValid = false;
  printf("Rescue geometry: %s\n", GeometryValid ? "verified" : "rejected; diagnostic mode");
#if CONFIG_IDF_TARGET_ESP32C3
  if( GeometryValid )
   {
    for( int Pin : {10, 19} ) { digitalWrite(Pin, HIGH); pinMode(Pin, OUTPUT); }
   }
#endif
  setup();
  for(;;) { loop(); delay(1); }
 }
