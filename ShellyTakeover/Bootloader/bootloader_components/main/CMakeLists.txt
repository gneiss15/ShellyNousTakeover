# CMakeLists.txt, Version: 1.01
set(TAKEOVER_GENERATED "$ENV{TAKEOVER_BOOTLOADER_GENERATED}")
if(NOT TAKEOVER_GENERATED)
  set(TAKEOVER_GENERATED "../../../../generated/ShellyTakeover/Bootloader")
endif()
idf_component_register(SRCS "bootloader_start.c" "Selection.c" "StockRequest.c" "BootState.c"
  INCLUDE_DIRS "." "${TAKEOVER_GENERATED}"
  REQUIRES bootloader bootloader_support spi_flash)
idf_build_get_property(scripts BOOTLOADER_LINKER_SCRIPT)
target_linker_script(${COMPONENT_LIB} INTERFACE "${scripts}")
