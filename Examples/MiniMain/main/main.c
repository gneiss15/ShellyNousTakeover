// main.c, Version: 1.00
#include "sdkconfig.h"
#include "Platform.h"
#include "DeviceType.inc.h"
#include "driver/gpio.h"
#include "esp_chip_info.h"
#include "esp_flash.h"
#include "esp_flash_encrypt.h"
#include "esp_secure_boot.h"
#include "esp_http_server.h"
#include "esp_ota_ops.h"
#include "esp_system.h"
#include "nvs_flash.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdio.h>
#include <stdatomic.h>

_Static_assert(CONFIG_PARTITION_TABLE_OFFSET == RESCUE_TABLE_OFFSET, "Wrong SDK partition-table offset");
void TakeoverNetworkStart(void);
bool TakeoverNetworkReady(void);
void TakeoverNetworkRetry(void);
static atomic_bool RestartPending;

static bool PartitionMatches(esp_partition_type_t Type, esp_partition_subtype_t Subtype,
  const char * Label, uint32_t Offset, uint32_t Size)
 {
  const esp_partition_t * Part = esp_partition_find_first(Type, Subtype, Label);
  return Part && !Part->readonly && Part->address == Offset && Part->size == Size;
 }

static bool GeometryValid(void)
 {
  esp_chip_info_t Chip = {0};
  uint32_t FlashSize = 0;
  esp_chip_info(&Chip);
  const esp_partition_t * Running = esp_ota_get_running_partition();
  if( Chip.model != RESCUE_CHIP || esp_flash_get_physical_size(NULL, &FlashSize) != ESP_OK ||
      FlashSize != RESCUE_FLASH_SIZE || esp_secure_boot_enabled() || esp_flash_encryption_enabled() ||
      !Running || Running->readonly || Running->type != ESP_PARTITION_TYPE_APP ||
      Running->subtype != ESP_PARTITION_SUBTYPE_APP_OTA_0 ||
      Running->address != RESCUE_MAIN_OFFSET || Running->size != RESCUE_MAIN_SIZE ) return false;
#if CONFIG_IDF_TARGET_ESP32C3
  if( Chip.revision != 4 ) return false;
#endif
  return PartitionMatches(ESP_PARTITION_TYPE_APP, ESP_PARTITION_SUBTYPE_APP_FACTORY,
    "safeboot", RESCUE_RESCUE_OFFSET, RESCUE_RESCUE_SIZE) &&
    PartitionMatches(ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_DATA_SPIFFS,
    "spiffs", RESCUE_FS_OFFSET, RESCUE_FS_SIZE) &&
    PartitionMatches(ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_DATA_NVS,
    "nvs", RESCUE_NVS_OFFSET, RESCUE_NVS_SIZE) &&
    PartitionMatches(ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_DATA_OTA,
    "otadata", RESCUE_OTA_OFFSET, 0x2000);
 }

static esp_err_t Page(httpd_req_t * Request)
 {
  httpd_resp_set_type(Request, "text/html; charset=utf-8");
  return httpd_resp_sendstr(Request,
    "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><title>MiniMain</title>"
    "<h1>MiniMain</h1><p>DeviceType: " ESP_UPDATE_DEVICE_TYPE "</p>"
    "<p>Relay stays OFF. No filesystem is required.</p><p><a href=\"/status\">Status</a></p>"
    "<form action=\"/Rescue\" method=\"post\"><button>Start Rescue</button></form></html>");
 }

static esp_err_t Status(httpd_req_t * Request)
 {
  char Json[192];
  const int Length = snprintf(Json, sizeof(Json),
    "{\"Application\":\"MiniMain\",\"DeviceType\":\"%s\",\"GeometryValid\":true,"
    "\"RelayOn\":false,\"StationReady\":%s}", ESP_UPDATE_DEVICE_TYPE,
    TakeoverNetworkReady() ? "true" : "false");
  if( Length < 0 || Length >= sizeof(Json) ) return ESP_FAIL;
  httpd_resp_set_type(Request, "application/json");
  return httpd_resp_sendstr(Request, Json);
 }

static esp_err_t StartRescue(httpd_req_t * Request)
 {
  const esp_partition_t * Rescue = esp_partition_find_first(ESP_PARTITION_TYPE_APP,
    ESP_PARTITION_SUBTYPE_APP_FACTORY, "safeboot");
  if( !GeometryValid() || !Rescue || esp_ota_set_boot_partition(Rescue) != ESP_OK )
    return httpd_resp_send_err(Request, HTTPD_500_INTERNAL_SERVER_ERROR, "Rescue selection failed");
  const esp_err_t Result = httpd_resp_sendstr(Request, "Starting Rescue...");
  // Boot selection succeeded even when the HTTP reply is lost; never repeat a write.
  atomic_store(&RestartPending, true);
  return Result;
 }

void app_main(void)
 {
  if( !GeometryValid() )
   {
    printf("MiniMain: geometry/security rejected; no outputs or flash initialized. Use KEY Safe Boot.\n");
    return;
   }
#if CONFIG_IDF_TARGET_ESP32C3
  const gpio_num_t Relay = GPIO_NUM_0;
#else
  const gpio_num_t Relay = GPIO_NUM_13;
#endif
  // Set the OFF latch before enabling the output. Neither example switches it ON.
  ESP_ERROR_CHECK(gpio_set_level(Relay, 0));
  ESP_ERROR_CHECK(gpio_set_direction(Relay, GPIO_MODE_OUTPUT));
  // Preserve NVS: initialization errors must never trigger an automatic erase.
  ESP_ERROR_CHECK(nvs_flash_init());
  TakeoverNetworkStart();
  httpd_handle_t Server = NULL;
  httpd_config_t Config = HTTPD_DEFAULT_CONFIG();
  ESP_ERROR_CHECK(httpd_start(&Server, &Config));
  const httpd_uri_t Routes[] = {
    { .uri="/", .method=HTTP_GET, .handler=Page },
    { .uri="/status", .method=HTTP_GET, .handler=Status },
    { .uri="/Rescue", .method=HTTP_POST, .handler=StartRescue }
  };
  for( unsigned Index = 0; Index < sizeof(Routes)/sizeof(Routes[0]); ++Index )
    ESP_ERROR_CHECK(httpd_register_uri_handler(Server, &Routes[Index]));
  unsigned Retry = 0;
  for(;;)
   {
    vTaskDelay(pdMS_TO_TICKS(250));
    if( atomic_load(&RestartPending) ) esp_restart();
    if( ++Retry == 40 ) { Retry = 0; TakeoverNetworkRetry(); }
   }
 }
