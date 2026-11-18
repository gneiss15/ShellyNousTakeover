# CMakeLists.txt, Version: 1.00
set(ROOT "${CMAKE_CURRENT_LIST_DIR}/../../..")
set(GENERATED "${ROOT}/generated/ShellyTakeover/App")
idf_component_register(SRCS "main.c" "Platform.c" "${ROOT}/common/Takeover/Flow.c"
  "${ROOT}/common/Takeover/Network.c" "${ROOT}/ShellyTakeover/Migration/Migration.c"
  "${ROOT}/ShellyTakeover/LoaderWriter/LoaderWriter.c"
  "${ROOT}/ShellyTakeover/Bootloader/bootloader_components/main/BootState.c"
  EMBED_FILES "${GENERATED}/CandidateLoader.bin" "${GENERATED}/Rescue.bin" "${GENERATED}/OldTable.bin" "${GENERATED}/NewTable.bin"
  "${GENERATED}/LargeLoader.bin" "${GENERATED}/LargeRescue.bin" "${GENERATED}/LargeOldTable.bin" "${GENERATED}/LargeNewTable.bin"
  INCLUDE_DIRS "." "${GENERATED}" "${ROOT}/common/Takeover" "${ROOT}/ShellyTakeover/Migration"
  "${ROOT}/ShellyTakeover/LoaderWriter" "${ROOT}/ShellyTakeover/Bootloader/bootloader_components/main"
  REQUIRES app_update esp_wifi esp_http_server json lwip mbedtls spi_flash bootloader_support)
