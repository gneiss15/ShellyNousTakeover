# CMakeLists.txt, Version: 1.01
cmake_minimum_required(VERSION 3.16)
set(MINIMAL_BUILD ON)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
include("${CMAKE_CURRENT_LIST_DIR}/../../common/ProjectVersion.cmake")
LoadTakeoverProjectVersion(NousApp)
project(NousTakeover)
