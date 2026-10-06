# CMakeLists.txt, Version: 1.00
idf_component_register(SRCS main.c "../../../common/Takeover/Network.c"
  INCLUDE_DIRS "$ENV{MINI_GENERATED}"
  REQUIRES esp_wifi esp_http_server app_update nvs_flash driver spi_flash bootloader_support)
