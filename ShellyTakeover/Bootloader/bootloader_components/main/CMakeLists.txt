# CMakeLists.txt, Version: 1.01
idf_component_register(SRCS "bootloader_start.c" "Selection.c" "StockRequest.c" "BootState.c"
  INCLUDE_DIRS "." "../../../../generated/ShellyTakeover/Bootloader"
  REQUIRES bootloader bootloader_support spi_flash)
idf_build_get_property(scripts BOOTLOADER_LINKER_SCRIPT)
target_linker_script(${COMPONENT_LIB} INTERFACE "${scripts}")
