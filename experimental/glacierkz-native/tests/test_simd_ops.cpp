#include <gtest/gtest.h>
#include "glacierkz/simd_ops.hpp"

#include <vector>
#include <cmath>
#include <numeric>

using namespace glacierkz;

TEST(SIMDArrayTest, DefaultConstruction) {
    SIMDArray arr(100);
    EXPECT_EQ(arr.size(), 100u);
    EXPECT_NE(arr.data(), nullptr);
    for (size_t i = 0; i < arr.size(); ++i) {
        EXPECT_FLOAT_EQ(arr.data()[i], 0.0f);
    }
}

TEST(SIMDArrayTest, DataConstruction) {
    std::vector<float> src = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f};
    SIMDArray arr(src.data(), src.size());
    EXPECT_EQ(arr.size(), 5u);
    for (size_t i = 0; i < src.size(); ++i) {
        EXPECT_FLOAT_EQ(arr.data()[i], src[i]);
    }
}

TEST(SIMDArrayTest, VectorConstruction) {
    std::vector<float> src = {1.0f, 2.0f, 3.0f};
    SIMDArray arr(src);
    EXPECT_EQ(arr.size(), 3u);
    EXPECT_FLOAT_EQ(arr.data()[0], 1.0f);
    EXPECT_FLOAT_EQ(arr.data()[2], 3.0f);
}

TEST(SIMDArrayTest, MoveConstruction) {
    SIMDArray arr1(10);
    arr1.data()[0] = 42.0f;
    SIMDArray arr2(std::move(arr1));
    EXPECT_EQ(arr2.size(), 10u);
    EXPECT_FLOAT_EQ(arr2.data()[0], 42.0f);
}

TEST(SIMDArrayTest, Zero) {
    SIMDArray arr(5);
    arr.data()[0] = 1.0f;
    arr.data()[3] = 99.0f;
    arr.zero();
    for (size_t i = 0; i < arr.size(); ++i) {
        EXPECT_FLOAT_EQ(arr.data()[i], 0.0f);
    }
}

TEST(SIMDVectorOpsTest, VectorAdd) {
    std::vector<float> a = {1.0f, 2.0f, 3.0f, 4.0f};
    std::vector<float> b = {5.0f, 6.0f, 7.0f, 8.0f};
    std::vector<float> result(4);
    vector_add(a.data(), b.data(), result.data(), 4, SIMDBackend::Scalar);
    EXPECT_FLOAT_EQ(result[0], 6.0f);
    EXPECT_FLOAT_EQ(result[1], 8.0f);
    EXPECT_FLOAT_EQ(result[2], 10.0f);
    EXPECT_FLOAT_EQ(result[3], 12.0f);
}

TEST(SIMDVectorOpsTest, VectorSubtract) {
    std::vector<float> a = {10.0f, 20.0f, 30.0f};
    std::vector<float> b = {1.0f, 2.0f, 3.0f};
    std::vector<float> result(3);
    vector_subtract(a.data(), b.data(), result.data(), 3, SIMDBackend::Scalar);
    EXPECT_FLOAT_EQ(result[0], 9.0f);
    EXPECT_FLOAT_EQ(result[1], 18.0f);
    EXPECT_FLOAT_EQ(result[2], 27.0f);
}

TEST(SIMDVectorOpsTest, VectorMultiply) {
    std::vector<float> a = {2.0f, 3.0f, 4.0f};
    std::vector<float> b = {5.0f, 6.0f, 7.0f};
    std::vector<float> result(3);
    vector_multiply(a.data(), b.data(), result.data(), 3, SIMDBackend::Scalar);
    EXPECT_FLOAT_EQ(result[0], 10.0f);
    EXPECT_FLOAT_EQ(result[1], 18.0f);
    EXPECT_FLOAT_EQ(result[2], 28.0f);
}

TEST(SIMDVectorOpsTest, VectorAddScalar) {
    std::vector<float> a = {1.0f, 2.0f, 3.0f};
    std::vector<float> result(3);
    vector_add_scalar(a.data(), 10.0f, result.data(), 3, SIMDBackend::Scalar);
    EXPECT_FLOAT_EQ(result[0], 11.0f);
    EXPECT_FLOAT_EQ(result[1], 12.0f);
    EXPECT_FLOAT_EQ(result[2], 13.0f);
}

TEST(SIMDVectorOpsTest, VectorMultiplyScalar) {
    std::vector<float> a = {2.0f, 3.0f, 4.0f};
    std::vector<float> result(3);
    vector_multiply_scalar(a.data(), 5.0f, result.data(), 3, SIMDBackend::Scalar);
    EXPECT_FLOAT_EQ(result[0], 10.0f);
    EXPECT_FLOAT_EQ(result[1], 15.0f);
    EXPECT_FLOAT_EQ(result[2], 20.0f);
}

TEST(SIMDVectorOpsTest, VectorNormalize) {
    std::vector<float> a = {0.0f, 5.0f, 10.0f};
    std::vector<float> result(3);
    vector_normalize(a.data(), result.data(), 3, 0.0f, 10.0f, SIMDBackend::Scalar);
    EXPECT_FLOAT_EQ(result[0], 0.0f);
    EXPECT_FLOAT_EQ(result[1], 0.5f);
    EXPECT_FLOAT_EQ(result[2], 1.0f);
}

TEST(SIMDVectorOpsTest, VectorNormalizeZeroRange) {
    std::vector<float> a = {5.0f, 5.0f, 5.0f};
    std::vector<float> result(3);
    vector_normalize(a.data(), result.data(), 3, 5.0f, 5.0f, SIMDBackend::Scalar);
    for (size_t i = 0; i < 3; ++i) {
        EXPECT_FLOAT_EQ(result[i], 0.0f);
    }
}

TEST(SIMDVectorOpsTest, VectorThreshold) {
    std::vector<float> a = {0.1f, 0.5f, 0.9f, 0.3f};
    std::vector<float> result(4);
    vector_threshold(a.data(), result.data(), 4, 0.5f, 0.0f, 1.0f, SIMDBackend::Scalar);
    EXPECT_FLOAT_EQ(result[0], 0.0f);
    EXPECT_FLOAT_EQ(result[1], 1.0f);
    EXPECT_FLOAT_EQ(result[2], 1.0f);
    EXPECT_FLOAT_EQ(result[3], 0.0f);
}

TEST(SIMDVectorOpsTest, VectorSum) {
    std::vector<float> a = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f};
    float s = vector_sum(a.data(), 5, SIMDBackend::Scalar);
    EXPECT_FLOAT_EQ(s, 15.0f);
}

TEST(SIMDVectorOpsTest, VectorMean) {
    std::vector<float> a = {2.0f, 4.0f, 6.0f};
    float m = vector_mean(a.data(), 3, SIMDBackend::Scalar);
    EXPECT_FLOAT_EQ(m, 4.0f);
}

TEST(SIMDVectorOpsTest, VectorVariance) {
    std::vector<float> a = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f};
    float v = vector_variance(a.data(), 5, SIMDBackend::Scalar);
    EXPECT_NEAR(v, 2.5f, 0.01f);
}

TEST(SIMDVectorOpsTest, VectorDotProduct) {
    std::vector<float> a = {1.0f, 2.0f, 3.0f};
    std::vector<float> b = {4.0f, 5.0f, 6.0f};
    float dp = vector_dot_product(a.data(), b.data(), 3, SIMDBackend::Scalar);
    EXPECT_FLOAT_EQ(dp, 32.0f);
}

TEST(SIMDVectorOpsTest, VectorMinMax) {
    std::vector<float> a = {3.0f, 1.0f, 4.0f, 1.5f, 9.0f};
    float mn, mx;
    vector_min_max(a.data(), 5, mn, mx, SIMDBackend::Scalar);
    EXPECT_FLOAT_EQ(mn, 1.0f);
    EXPECT_FLOAT_EQ(mx, 9.0f);
}

TEST(SIMDVectorOpsTest, VectorAbs) {
    std::vector<float> a = {-3.0f, 0.0f, 2.5f, -1.0f};
    std::vector<float> result(4);
    vector_abs(a.data(), result.data(), 4, SIMDBackend::Scalar);
    EXPECT_FLOAT_EQ(result[0], 3.0f);
    EXPECT_FLOAT_EQ(result[1], 0.0f);
    EXPECT_FLOAT_EQ(result[2], 2.5f);
    EXPECT_FLOAT_EQ(result[3], 1.0f);
}

TEST(SIMDVectorOpsTest, VectorClip) {
    std::vector<float> a = {-1.0f, 0.5f, 1.5f};
    std::vector<float> result(3);
    vector_clip(a.data(), result.data(), 3, 0.0f, 1.0f, SIMDBackend::Scalar);
    EXPECT_FLOAT_EQ(result[0], 0.0f);
    EXPECT_FLOAT_EQ(result[1], 0.5f);
    EXPECT_FLOAT_EQ(result[2], 1.0f);
}

TEST(SIMDVectorOpsTest, VectorArgmax) {
    std::vector<float> a = {1.0f, 5.0f, 3.0f, 9.0f, 2.0f};
    size_t idx = vector_argmax(a.data(), 5, SIMDBackend::Scalar);
    EXPECT_EQ(idx, 3u);
}

TEST(SIMDVectorOpsTest, VectorArgmin) {
    std::vector<float> a = {5.0f, 1.0f, 3.0f, 9.0f, 2.0f};
    size_t idx = vector_argmin(a.data(), 5, SIMDBackend::Scalar);
    EXPECT_EQ(idx, 1u);
}

TEST(SIMDVectorOpsTest, ApplySpectralTransform) {
    std::vector<std::vector<float>> bands = {
        {1.0f, 2.0f, 3.0f},
        {4.0f, 5.0f, 6.0f}
    };
    std::vector<float> weights = {0.3f, 0.7f};
    auto result = apply_spectral_transform(bands, weights, SIMDBackend::Scalar);
    EXPECT_NEAR(result[0], 1.0f * 0.3f + 4.0f * 0.7f, 0.01f);
    EXPECT_NEAR(result[1], 2.0f * 0.3f + 5.0f * 0.7f, 0.01f);
    EXPECT_NEAR(result[2], 3.0f * 0.3f + 6.0f * 0.7f, 0.01f);
}

TEST(SIMDVectorOpsTest, ApplySpectralTransformEmpty) {
    std::vector<std::vector<float>> bands;
    std::vector<float> weights;
    auto result = apply_spectral_transform(bands, weights, SIMDBackend::Scalar);
    EXPECT_TRUE(result.empty());
}

TEST(SIMDVectorOpsTest, VectorBlend) {
    std::vector<float> a = {10.0f, 20.0f, 30.0f};
    std::vector<float> b = {100.0f, 200.0f, 300.0f};
    std::vector<float> mask = {1.0f, 0.0f, 1.0f};
    std::vector<float> result(3);
    vector_blend(a.data(), b.data(), result.data(), 3, mask.data(), SIMDBackend::Scalar);
    EXPECT_FLOAT_EQ(result[0], 10.0f);
    EXPECT_FLOAT_EQ(result[1], 200.0f);
    EXPECT_FLOAT_EQ(result[2], 30.0f);
}

TEST(SIMDVectorOpsTest, DetectBackend) {
    auto backend = detect_best_backend();
    EXPECT_TRUE(backend == SIMDBackend::Scalar ||
                backend == SIMDBackend::SSE2 ||
                backend == SIMDBackend::AVX2);
}
