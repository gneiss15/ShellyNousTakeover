# CMakeLists.txt, Version: 1.00
set(ROOT "${CMAKE_CURRENT_LIST_DIR}/../../..")
set(GENERATED "${ROOT}/generated/NousTakeover/App")
idf_component_register(SRCS "main.c" "Platform.c" "${ROOT}/common/Takeover/Flow.c"
  "${ROOT}/common/Takeover/Network.c" "${ROOT}/NousTakeover/LoaderWriter/LoaderWriter.c"
  EMBED_FILES "${GENERATED}/CandidateLoader.bin" "${GENERATED}/Rescue.bin" "${GENERATED}/ExpectedTable.bin"
  INCLUDE_DIRS "." "${GENERATED}" "${ROOT}/common/Takeover" "${ROOT}/NousTakeover/LoaderWriter"
  REQUIRES app_update esp_wifi esp_http_server json mbedtls spi_flash bootloader_support)
