cmake_minimum_required(VERSION 3.14)
project(glacierkz C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(GZ_BUILD_TESTS "Build unit tests" ON)
option(GZ_BUILD_CLI "Build CLI tools" ON)

add_library(glacierkz STATIC
    src/glacierkz_tiff.c
    src/glacierkz_raster.c
    src/glacierkz_thread.c
    src/glacierkz_tile.c
    src/glacierkz_checksum.c
    src/glacierkz_memory.c
    src/glacierkz_endian.c
    src/glacierkz_args.c
    src/glacierkz_log.c
)

target_include_directories(glacierkz PUBLIC include)
target_link_libraries(glacierkz PRIVATE m pthread)

if(GZ_BUILD_CLI)
    add_executable(gzinfo src/cli/gzinfo.c)
    target_link_libraries(gzinfo glacierkz)

    add_executable(gzcat src/cli/gzcat.c)
    target_link_libraries(gzcat glacierkz)

    add_executable(gzverify src/cli/gzverify.c)
    target_link_libraries(gzverify glacierkz)

    add_executable(gztile src/cli/gztile.c)
    target_link_libraries(gztile glacierkz)
endif()

if(GZ_BUILD_TESTS)
    include(FetchContent)
    FetchContent_Declare(
        googletest
        URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.tar.gz
    )
    FetchContent_MakeAvailable(googletest)

    enable_testing()

    add_executable(test_tiff tests/test_tiff.c)
    target_link_libraries(test_tiff glacierkz GTest::gtest_main)
    add_test(NAME test_tiff COMMAND test_tiff)

    add_executable(test_raster tests/test_raster.c)
    target_link_libraries(test_raster glacierkz GTest::gtest_main)
    add_test(NAME test_raster COMMAND test_raster)

    add_executable(test_thread tests/test_thread.c)
    target_link_libraries(test_thread glacierkz GTest::gtest_main)
    add_test(NAME test_thread COMMAND test_thread)

    add_executable(test_checksum tests/test_checksum.c)
    target_link_libraries(test_checksum glacierkz GTest::gtest_main)
    add_test(NAME test_checksum COMMAND test_checksum)

    add_executable(test_memory tests/test_memory.c)
    target_link_libraries(test_memory glacierkz GTest::gtest_main)
    add_test(NAME test_memory COMMAND test_memory)

    add_executable(test_args tests/test_args.c)
    target_link_libraries(test_args glacierkz GTest::gtest_main)
    add_test(NAME test_args COMMAND test_args)
endif()
