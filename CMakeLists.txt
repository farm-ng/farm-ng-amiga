cmake_minimum_required(VERSION 3.16)
# https://semver.org/
project(amiga_brain_api VERSION 0.1.0)


find_package(farm_ng_cmake 0.1.0 REQUIRED)
farm_ng_module(amiga_brain_api)

find_package(farm_ng_core 0.1.0 REQUIRED)
find_package(Sophus REQUIRED)

# TODO: Where shall this go? Shall we call farm_ng_export_module here?
set(CMAKE_CXX_STANDARD 17)

farm_ng_enable_testing()

add_subdirectory(protos)

farm_ng_export_module(
  NAME amiga_brain_api
  REQUIRED_DEPS farm_ng_core Sophus)
