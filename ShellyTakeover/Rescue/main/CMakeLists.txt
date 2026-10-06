# CMakeLists.txt, Version: 1.00
set(ROOT "${CMAKE_CURRENT_LIST_DIR}/../../..")
set(GENERATED "${ROOT}/generated/ShellyTakeover/Rescue")
idf_component_register(SRCS "${ROOT}/common/Rescue/main.cpp" "${ROOT}/common/Rescue/Rescue.cpp"
  "${ROOT}/common/Rescue/EspRescueUpdater.cpp" "${ROOT}/common/Update/EspSignedArtifact.cpp"
  INCLUDE_DIRS "${GENERATED}" "${ROOT}/common/Rescue" "${ROOT}/common/Update" "${ROOT}/common/IdfAdapter"
  REQUIRES esp_wifi app_update nvs_flash driver esp_timer mbedtls bootloader_support spi_flash)
