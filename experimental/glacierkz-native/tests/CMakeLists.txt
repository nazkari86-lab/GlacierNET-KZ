find_package(GTest REQUIRED)

add_executable(glacierkz_tests
    test_band_math.cpp
    test_color_map.cpp
    test_dem_parser.cpp
    test_georef.cpp
    test_io.cpp
    test_math.cpp
    test_quadtree.cpp
    test_tile_cache.cpp
    test_simd_ops.cpp
    test_statistics.cpp
    test_thread_pool.cpp
    test_resampling.cpp
)

target_link_libraries(glacierkz_tests
    PRIVATE
        GTest::GTest
        GTest::Main
        glacierkz
)

target_include_directories(glacierkz_tests PRIVATE ${CMAKE_SOURCE_DIR}/include)

include(GoogleTest)
gtest_discover_tests(glacierkz_tests)
