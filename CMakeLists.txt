cmake_minimum_required(VERSION 3.16)
# https://semver.org/
project(farm_ng_amiga VERSION 0.1.0)


farm_ng_module(farm_ng_amiga)
set(farm_ng_cmake_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../farm_ng_core/cmake)
include(${farm_ng_cmake_DIR}/farm_ng_cmakeConfig.cmake)

# TODO: Where shall this go? Shall we call farm_ng_export_module here?
set(CMAKE_CXX_STANDARD 17)

farm_ng_enable_testing()

add_subdirectory(protos)
