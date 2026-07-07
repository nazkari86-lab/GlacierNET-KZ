#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>
#include <functional>
#include <string>
#include <memory>

namespace glacierkz {

enum class SIMDBackend {
    Scalar,
    SSE2,
    AVX2
};

SIMDBackend detect_best_backend();

class SIMDArray {
public:
    explicit SIMDArray(size_t size);
    SIMDArray(const float* data, size_t size);
    SIMDArray(std::vector<float> data);
    ~SIMDArray();

    SIMDArray(const SIMDArray&) = delete;
    SIMDArray& operator=(const SIMDArray&) = delete;
    SIMDArray(SIMDArray&& other) noexcept;
    SIMDArray& operator=(SIMDArray&& other) noexcept;

    float* data();
    const float* data() const;
    size_t size() const;
    size_t aligned_size() const;

    void zero();

private:
    struct AlignedDeleter {
        void operator()(float* p) const;
    };
    std::unique_ptr<float[], AlignedDeleter> data_;
    size_t size_;
    size_t aligned_size_;
};

void vector_add(const float* a, const float* b, float* result, size_t n,
                SIMDBackend backend = SIMDBackend::Scalar);

void vector_subtract(const float* a, const float* b, float* result, size_t n,
                     SIMDBackend backend = SIMDBackend::Scalar);

void vector_multiply(const float* a, const float* b, float* result, size_t n,
                     SIMDBackend backend = SIMDBackend::Scalar);

void vector_add_scalar(const float* a, float scalar, float* result, size_t n,
                       SIMDBackend backend = SIMDBackend::Scalar);

void vector_multiply_scalar(const float* a, float scalar, float* result, size_t n,
                            SIMDBackend backend = SIMDBackend::Scalar);

void vector_normalize(const float* a, float* result, size_t n,
                      float min_val, float max_val,
                      SIMDBackend backend = SIMDBackend::Scalar);

void vector_threshold(const float* a, float* result, size_t n,
                      float threshold, float low_val, float high_val,
                      SIMDBackend backend = SIMDBackend::Scalar);

float vector_sum(const float* a, size_t n,
                 SIMDBackend backend = SIMDBackend::Scalar);

float vector_mean(const float* a, size_t n,
                  SIMDBackend backend = SIMDBackend::Scalar);

float vector_variance(const float* a, size_t n,
                      SIMDBackend backend = SIMDBackend::Scalar);

float vector_dot_product(const float* a, const float* b, size_t n,
                         SIMDBackend backend = SIMDBackend::Scalar);

void vector_min_max(const float* a, size_t n,
                    float& out_min, float& out_max,
                    SIMDBackend backend = SIMDBackend::Scalar);

void vector_abs(const float* a, float* result, size_t n,
                SIMDBackend backend = SIMDBackend::Scalar);

void vector_clip(const float* a, float* result, size_t n,
                 float low, float high,
                 SIMDBackend backend = SIMDBackend::Scalar);

void vector_blend(const float* a, const float* b, float* result, size_t n,
                  const float* mask,
                  SIMDBackend backend = SIMDBackend::Scalar);

size_t vector_argmax(const float* a, size_t n,
                     SIMDBackend backend = SIMDBackend::Scalar);

size_t vector_argmin(const float* a, size_t n,
                     SIMDBackend backend = SIMDBackend::Scalar);

std::vector<float> apply_spectral_transform(
    const std::vector<std::vector<float>>& bands,
    const std::vector<float>& weights,
    SIMDBackend backend = SIMDBackend::Scalar);

} // namespace glacierkz
