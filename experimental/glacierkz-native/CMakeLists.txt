cmake_minimum_required(VERSION 3.20)

project(glacierkz-native
    VERSION 1.0.0
    DESCRIPTION "High-performance raster processing library for glacier monitoring satellite imagery"
    LANGUAGES CXX C
)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(GLACIERKZ_BUILD_TESTS "Build unit tests" ON)
option(GLACIERKZ_BUILD_PYTHON "Build Python bindings" OFF)
option(GLACIERKZ_USE_CUDA "Enable CUDA GPU acceleration" OFF)
option(GLACIERKZ_USE_OPENMP "Enable OpenMP parallelism" ON)

set(CMAKE_POSITION_INDEPENDENT_CODE ON)

find_package(GDAL REQUIRED)
find_package(fmt REQUIRED)
find_package(spdlog REQUIRED)

if(GLACIERKZ_USE_OPENMP)
    find_package(OpenMP)
endif()

if(GLACIERKZ_USE_CUDA)
    find_package(CUDAToolkit REQUIRED)
endif()

set(GLACIERKZ_SOURCES
    src/raster_io.cpp
    src/spectral_indices.cpp
    src/sliding_window.cpp
    src/simd_ops.cpp
    src/tile_cache.cpp
    src/thread_pool.cpp
    src/statistics.cpp
    src/resampling.cpp
    src/band_math.cpp
)

add_library(glacierkz STATIC ${GLACIERKZ_SOURCES})

target_include_directories(glacierkz
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(glacierkz
    PUBLIC
        GDAL::GDAL
        fmt::fmt
        spdlog::spdlog
)

target_compile_features(glacierkz PUBLIC cxx_std_17)

if(OpenMP_CXX_FOUND AND GLACIERKZ_USE_OPENMP)
    target_link_libraries(glacierkz PUBLIC OpenMP::OpenMP_CXX)
    target_compile_definitions(glacierkz PUBLIC GLACIERKZ_HAS_OPENMP)
endif()

if(GLACIERKZ_USE_CUDA)
    target_sources(glacierkz PRIVATE src/cuda_kernels.cu)
    target_link_libraries(glacierkz PUBLIC CUDA::cudart)
    target_compile_definitions(glacierkz PUBLIC GLACIERKZ_HAS_CUDA)
endif()

if(MSVC)
    target_compile_options(glacierkz PRIVATE /W4 /MP)
else()
    target_compile_options(glacierkz PRIVATE -Wall -Wextra -Wpedantic -Wno-unused-parameter)
    if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
        target_compile_options(glacierkz PRIVATE -march=native)
    endif()
endif()

set_target_properties(glacierkz PROPERTIES
    OUTPUT_NAME glacierkz
    DEBUG_POSTFIX d
    VERSION ${PROJECT_VERSION}
    SOVERSION 1
)

if(GLACIERKZ_BUILD_TESTS)
    find_package(GTest REQUIRED)
    enable_testing()
    add_subdirectory(tests)
endif()

if(GLACIERKZ_BUILD_PYTHON)
    find_package(pybind11 REQUIRED)
    add_subdirectory(bindings)
endif()

install(TARGETS glacierkz
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
)

install(DIRECTORY include/glacierkz DESTINATION include)

include(GNUInstallDirs)
install(FILES include/glacierkz/raster_io.hpp DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/glacierkz)
install(FILES include/glacierkz/spectral_indices.hpp DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/glacierkz)
install(FILES include/glacierkz/sliding_window.hpp DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/glacierkz)
install(FILES include/glacierkz/simd_ops.hpp DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/glacierkz)
install(FILES include/glacierkz/tile_cache.hpp DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/glacierkz)
install(FILES include/glacierkz/thread_pool.hpp DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/glacierkz)
install(FILES include/glacierkz/cuda_kernels.cuh DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/glacierkz)
install(FILES include/glacierkz/statistics.hpp DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/glacierkz)
install(FILES include/glacierkz/resampling.hpp DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/glacierkz)
install(FILES include/glacierkz/band_math.hpp DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/glacierkz)
