#include <gtest/gtest.h>
#include "glacierkz/resampling.hpp"

#include <vector>
#include <cmath>

using namespace glacierkz;

TEST(ResamplerTest, NearestNeighbor) {
    std::vector<float> data = {
        1.0f, 2.0f,
        3.0f, 4.0f
    };
    float val = Resampler::nearest_neighbor(data.data(), 2, 2, 0.5f, 0.5f);
    EXPECT_FLOAT_EQ(val, 1.0f);

    val = Resampler::nearest_neighbor(data.data(), 2, 2, 1.0f, 0.0f);
    EXPECT_FLOAT_EQ(val, 2.0f);
}

TEST(ResamplerTest, Bilinear) {
    std::vector<float> data = {
        0.0f, 1.0f,
        2.0f, 3.0f
    };
    float val = Resampler::bilinear(data.data(), 2, 2, 0.5f, 0.5f);
    EXPECT_NEAR(val, 1.5f, 0.01f);
}

TEST(ResamplerTest, BilinearCenter) {
    std::vector<float> data = {
        0.0f, 2.0f,
        4.0f, 6.0f
    };
    float val = Resampler::bilinear(data.data(), 2, 2, 0.5f, 0.5f);
    EXPECT_NEAR(val, 3.0f, 0.01f);
}

TEST(ResamplerTest, CubicKernel) {
    EXPECT_NEAR(Resampler::cubic_kernel(0.0f), 1.0f, 0.01f);
    EXPECT_NEAR(Resampler::cubic_kernel(1.0f), 0.0f, 0.01f);
    EXPECT_NEAR(Resampler::cubic_kernel(2.0f), 0.0f, 0.01f);
}

TEST(ResamplerTest, Bicubic) {
    std::vector<float> data = {
        1.0f, 2.0f, 3.0f, 4.0f,
        5.0f, 6.0f, 7.0f, 8.0f,
        9.0f, 10.0f, 11.0f, 12.0f,
        13.0f, 14.0f, 15.0f, 16.0f
    };
    float val = Resampler::bicubic(data.data(), 4, 4, 1.5f, 1.5f);
    EXPECT_GT(val, 0.0f);
}

TEST(ResamplerTest, Lanczos) {
    std::vector<float> data = {
        1.0f, 2.0f, 3.0f,
        4.0f, 5.0f, 6.0f,
        7.0f, 8.0f, 9.0f
    };
    float val = Resampler::lanczos(data.data(), 3, 3, 1.0f, 1.0f);
    EXPECT_NEAR(val, 5.0f, 1.0f);
}

TEST(ResamplerTest, ResampleBilinear) {
    std::vector<float> data = {
        0.0f, 1.0f,
        2.0f, 3.0f
    };
    auto result = Resampler::resample_bilinear(data.data(), 2, 2, 4, 4);
    EXPECT_EQ(result.size(), 16u);
}

TEST(PyramidBuilderTest, LevelSizes) {
    auto sizes = PyramidBuilder::level_sizes(256, 256, 4);
    EXPECT_EQ(sizes.size(), 4u);
    EXPECT_EQ(sizes[0].first, 256);
    EXPECT_EQ(sizes[1].first, 128);
    EXPECT_EQ(sizes[2].first, 64);
    EXPECT_EQ(sizes[3].first, 32);
}

TEST(PyramidBuilderTest, BuildPyramid) {
    std::vector<float> data(64 * 64, 1.0f);
    auto pyramid = PyramidBuilder::build_gaussian_pyramid(data.data(), 64, 64, 3);
    EXPECT_EQ(pyramid.size(), 3u);
    EXPECT_EQ(pyramid[0].size(), 64u * 64u);
    EXPECT_EQ(pyramid[1].size(), 32u * 32u);
    EXPECT_EQ(pyramid[2].size(), 16u * 16u);
}

TEST(ThumbnailGeneratorTest, NearestNeighbor) {
    std::vector<float> data(100);
    for (int i = 0; i < 100; ++i) data[i] = static_cast<float>(i);
    auto thumb = ThumbnailGenerator::generate_nearest(data.data(), 10, 10, 5, 5);
    EXPECT_EQ(thumb.size(), 25u);
}

TEST(ThumbnailGeneratorTest, Bilinear) {
    std::vector<float> data(100);
    for (int i = 0; i < 100; ++i) data[i] = static_cast<float>(i);
    auto thumb = ThumbnailGenerator::generate_bilinear(data.data(), 10, 10, 5, 5);
    EXPECT_EQ(thumb.size(), 25u);
}

TEST(ThumbnailGeneratorTest, Average) {
    std::vector<float> data(100);
    for (int i = 0; i < 100; ++i) data[i] = static_cast<float>(i);
    auto thumb = ThumbnailGenerator::generate_average(data.data(), 10, 10, 5, 5);
    EXPECT_EQ(thumb.size(), 25u);
}

TEST(ThumbnailGeneratorTest, AverageValues) {
    std::vector<float> data = {
        1.0f, 1.0f, 2.0f, 2.0f,
        1.0f, 1.0f, 2.0f, 2.0f,
        3.0f, 3.0f, 4.0f, 4.0f,
        3.0f, 3.0f, 4.0f, 4.0f
    };
    auto thumb = ThumbnailGenerator::generate_average(data.data(), 4, 4, 2, 2);
    EXPECT_NEAR(thumb[0], 1.0f, 0.01f);
    EXPECT_NEAR(thumb[1], 2.0f, 0.01f);
    EXPECT_NEAR(thumb[2], 3.0f, 0.01f);
    EXPECT_NEAR(thumb[3], 4.0f, 0.01f);
}
