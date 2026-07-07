#include "glacierkz/simd_ops.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <stdexcept>
#include <numeric>
#include <limits>

#ifdef __SSE2__
#include <emmintrin.h>
#endif

#ifdef __AVX2__
#include <immintrin.h>
#endif

#ifdef _OPENMP
#include <omp.h>
#endif

namespace glacierkz {

SIMDBackend detect_best_backend() {
#ifdef __AVX2__
    return SIMDBackend::AVX2;
#elif defined(__SSE2__)
    return SIMDBackend::SSE2;
#else
    return SIMDBackend::Scalar;
#endif
}

static constexpr size_t SIMDAlignment = 32;

static float* aligned_alloc_float(size_t n) {
    size_t aligned_n = (n + 7) & ~size_t(7);
    void* ptr = nullptr;
#ifdef _WIN32
    ptr = _aligned_malloc(aligned_n * sizeof(float), SIMDAlignment);
#else
    if (posix_memalign(&ptr, SIMDAlignment, aligned_n * sizeof(float)) != 0) {
        ptr = nullptr;
    }
#endif
    if (!ptr) throw std::bad_alloc();
    return static_cast<float*>(ptr);
}

static void aligned_free_float(float* ptr) {
#ifdef _WIN32
    _aligned_free(ptr);
#else
    free(ptr);
#endif
}

void SIMDArray::AlignedDeleter::operator()(float* p) const {
    aligned_free_float(p);
}

SIMDArray::SIMDArray(size_t size)
    : data_(aligned_alloc_float(size), AlignedDeleter{}),
      size_(size),
      aligned_size_((size + 7) & ~size_t(7)) {
    zero();
}

SIMDArray::SIMDArray(const float* data, size_t size)
    : data_(aligned_alloc_float(size), AlignedDeleter{}),
      size_(size),
      aligned_size_((size + 7) & ~size_t(7)) {
    std::memcpy(data_.get(), data, size * sizeof(float));
    std::memset(data_.get() + size, 0, (aligned_size_ - size) * sizeof(float));
}

SIMDArray::SIMDArray(std::vector<float> data_vec)
    : SIMDArray(data_vec.data(), data_vec.size()) {}

SIMDArray::SIMDArray(SIMDArray&& other) noexcept = default;
SIMDArray& SIMDArray::operator=(SIMDArray&& other) noexcept = default;

SIMDArray::~SIMDArray() = default;

float* SIMDArray::data() { return data_.get(); }
const float* SIMDArray::data() const { return data_.get(); }
size_t SIMDArray::size() const { return size_; }
size_t SIMDArray::aligned_size() const { return aligned_size_; }

void SIMDArray::zero() {
    std::memset(data_.get(), 0, aligned_size_ * sizeof(float));
}

void vector_add(const float* a, const float* b, float* result, size_t n,
                SIMDBackend backend) {
    if (backend == SIMDBackend::Scalar || n < 8) {
        for (size_t i = 0; i < n; ++i) {
            result[i] = a[i] + b[i];
        }
        return;
    }

#ifdef __SSE2__
    if (backend == SIMDBackend::SSE2 || backend == SIMDBackend::Scalar) {
        size_t i = 0;
        for (; i + 4 <= n; i += 4) {
            __m128 va = _mm_loadu_ps(a + i);
            __m128 vb = _mm_loadu_ps(b + i);
            __m128 vr = _mm_add_ps(va, vb);
            _mm_storeu_ps(result + i, vr);
        }
        for (; i < n; ++i) {
            result[i] = a[i] + b[i];
        }
        return;
    }
#endif

#ifdef __AVX2__
    if (backend == SIMDBackend::AVX2) {
        size_t i = 0;
        for (; i + 8 <= n; i += 8) {
            __m256 va = _mm256_loadu_ps(a + i);
            __m256 vb = _mm256_loadu_ps(b + i);
            __m256 vr = _mm256_add_ps(va, vb);
            _mm256_storeu_ps(result + i, vr);
        }
        for (; i < n; ++i) {
            result[i] = a[i] + b[i];
        }
        return;
    }
#endif

    for (size_t i = 0; i < n; ++i) {
        result[i] = a[i] + b[i];
    }
}

void vector_subtract(const float* a, const float* b, float* result, size_t n,
                     SIMDBackend backend) {
    if (backend == SIMDBackend::Scalar || n < 8) {
        for (size_t i = 0; i < n; ++i) {
            result[i] = a[i] - b[i];
        }
        return;
    }

#ifdef __AVX2__
    if (backend == SIMDBackend::AVX2) {
        size_t i = 0;
        for (; i + 8 <= n; i += 8) {
            __m256 va = _mm256_loadu_ps(a + i);
            __m256 vb = _mm256_loadu_ps(b + i);
            _mm256_storeu_ps(result + i, _mm256_sub_ps(va, vb));
        }
        for (; i < n; ++i) result[i] = a[i] - b[i];
        return;
    }
#endif

#ifdef __SSE2__
    if (backend == SIMDBackend::SSE2) {
        size_t i = 0;
        for (; i + 4 <= n; i += 4) {
            __m128 va = _mm_loadu_ps(a + i);
            __m128 vb = _mm_loadu_ps(b + i);
            _mm_storeu_ps(result + i, _mm_sub_ps(va, vb));
        }
        for (; i < n; ++i) result[i] = a[i] - b[i];
        return;
    }
#endif

    for (size_t i = 0; i < n; ++i) {
        result[i] = a[i] - b[i];
    }
}

void vector_multiply(const float* a, const float* b, float* result, size_t n,
                     SIMDBackend backend) {
    if (backend == SIMDBackend::Scalar || n < 8) {
        for (size_t i = 0; i < n; ++i) {
            result[i] = a[i] * b[i];
        }
        return;
    }

#ifdef __AVX2__
    if (backend == SIMDBackend::AVX2) {
        size_t i = 0;
        for (; i + 8 <= n; i += 8) {
            __m256 va = _mm256_loadu_ps(a + i);
            __m256 vb = _mm256_loadu_ps(b + i);
            _mm256_storeu_ps(result + i, _mm256_mul_ps(va, vb));
        }
        for (; i < n; ++i) result[i] = a[i] * b[i];
        return;
    }
#endif

#ifdef __SSE2__
    if (backend == SIMDBackend::SSE2) {
        size_t i = 0;
        for (; i + 4 <= n; i += 4) {
            __m128 va = _mm_loadu_ps(a + i);
            __m128 vb = _mm_loadu_ps(b + i);
            _mm_storeu_ps(result + i, _mm_mul_ps(va, vb));
        }
        for (; i < n; ++i) result[i] = a[i] * b[i];
        return;
    }
#endif

    for (size_t i = 0; i < n; ++i) {
        result[i] = a[i] * b[i];
    }
}

void vector_add_scalar(const float* a, float scalar, float* result, size_t n,
                       SIMDBackend backend) {
    if (backend == SIMDBackend::Scalar || n < 8) {
        for (size_t i = 0; i < n; ++i) {
            result[i] = a[i] + scalar;
        }
        return;
    }

#ifdef __AVX2__
    if (backend == SIMDBackend::AVX2) {
        __m256 vs = _mm256_set1_ps(scalar);
        size_t i = 0;
        for (; i + 8 <= n; i += 8) {
            __m256 va = _mm256_loadu_ps(a + i);
            _mm256_storeu_ps(result + i, _mm256_add_ps(va, vs));
        }
        for (; i < n; ++i) result[i] = a[i] + scalar;
        return;
    }
#endif

#ifdef __SSE2__
    if (backend == SIMDBackend::SSE2) {
        __m128 vs = _mm_set1_ps(scalar);
        size_t i = 0;
        for (; i + 4 <= n; i += 4) {
            __m128 va = _mm_loadu_ps(a + i);
            _mm_storeu_ps(result + i, _mm_add_ps(va, vs));
        }
        for (; i < n; ++i) result[i] = a[i] + scalar;
        return;
    }
#endif

    for (size_t i = 0; i < n; ++i) {
        result[i] = a[i] + scalar;
    }
}

void vector_multiply_scalar(const float* a, float scalar, float* result, size_t n,
                            SIMDBackend backend) {
    if (backend == SIMDBackend::Scalar || n < 8) {
        for (size_t i = 0; i < n; ++i) {
            result[i] = a[i] * scalar;
        }
        return;
    }

#ifdef __AVX2__
    if (backend == SIMDBackend::AVX2) {
        __m256 vs = _mm256_set1_ps(scalar);
        size_t i = 0;
        for (; i + 8 <= n; i += 8) {
            _mm256_storeu_ps(result + i, _mm256_mul_ps(_mm256_loadu_ps(a + i), vs));
        }
        for (; i < n; ++i) result[i] = a[i] * scalar;
        return;
    }
#endif

#ifdef __SSE2__
    if (backend == SIMDBackend::SSE2) {
        __m128 vs = _mm_set1_ps(scalar);
        size_t i = 0;
        for (; i + 4 <= n; i += 4) {
            _mm_storeu_ps(result + i, _mm_mul_ps(_mm_loadu_ps(a + i), vs));
        }
        for (; i < n; ++i) result[i] = a[i] * scalar;
        return;
    }
#endif

    for (size_t i = 0; i < n; ++i) {
        result[i] = a[i] * scalar;
    }
}

void vector_normalize(const float* a, float* result, size_t n,
                      float min_val, float max_val,
                      SIMDBackend backend) {
    float range = max_val - min_val;
    if (std::abs(range) < 1e-10f) {
        std::memset(result, 0, n * sizeof(float));
        return;
    }
    float inv_range = 1.0f / range;

    if (backend == SIMDBackend::Scalar || n < 8) {
        for (size_t i = 0; i < n; ++i) {
            result[i] = (a[i] - min_val) * inv_range;
        }
        return;
    }

#ifdef __AVX2__
    if (backend == SIMDBackend::AVX2) {
        __m256 vmin = _mm256_set1_ps(min_val);
        __m256 vinv = _mm256_set1_ps(inv_range);
        size_t i = 0;
        for (; i + 8 <= n; i += 8) {
            __m256 va = _mm256_loadu_ps(a + i);
            __m256 vsub = _mm256_sub_ps(va, vmin);
            _mm256_storeu_ps(result + i, _mm256_mul_ps(vsub, vinv));
        }
        for (; i < n; ++i) result[i] = (a[i] - min_val) * inv_range;
        return;
    }
#endif

#ifdef __SSE2__
    if (backend == SIMDBackend::SSE2) {
        __m128 vmin = _mm_set1_ps(min_val);
        __m128 vinv = _mm_set1_ps(inv_range);
        size_t i = 0;
        for (; i + 4 <= n; i += 4) {
            __m128 va = _mm_loadu_ps(a + i);
            __m128 vsub = _mm_sub_ps(va, vmin);
            _mm_storeu_ps(result + i, _mm_mul_ps(vsub, vinv));
        }
        for (; i < n; ++i) result[i] = (a[i] - min_val) * inv_range;
        return;
    }
#endif

    for (size_t i = 0; i < n; ++i) {
        result[i] = (a[i] - min_val) * inv_range;
    }
}

void vector_threshold(const float* a, float* result, size_t n,
                      float threshold, float low_val, float high_val,
                      SIMDBackend backend) {
    if (backend == SIMDBackend::Scalar || n < 8) {
        for (size_t i = 0; i < n; ++i) {
            result[i] = (a[i] >= threshold) ? high_val : low_val;
        }
        return;
    }

#ifdef __AVX2__
    if (backend == SIMDBackend::AVX2) {
        __m256 vt = _mm256_set1_ps(threshold);
        __m256 vlo = _mm256_set1_ps(low_val);
        __m256 vhi = _mm256_set1_ps(high_val);
        size_t i = 0;
        for (; i + 8 <= n; i += 8) {
            __m256 va = _mm256_loadu_ps(a + i);
            __m256 cmp = _mm256_cmp_ps(va, vt, _CMP_GE_OQ);
            __m256 vr = _mm256_blendv_ps(vlo, vhi, cmp);
            _mm256_storeu_ps(result + i, vr);
        }
        for (; i < n; ++i) result[i] = (a[i] >= threshold) ? high_val : low_val;
        return;
    }
#endif

#ifdef __SSE2__
    if (backend == SIMDBackend::SSE2) {
        __m128 vt = _mm_set1_ps(threshold);
        __m128 vlo = _mm_set1_ps(low_val);
        __m128 vhi = _mm_set1_ps(high_val);
        size_t i = 0;
        for (; i + 4 <= n; i += 4) {
            __m128 va = _mm_loadu_ps(a + i);
            __m128 cmp = _mm_cmpge_ps(va, vt);
            __m128 mask = _mm_and_ps(cmp, vhi);
            __m128 nmask = _mm_andnot_ps(cmp, vlo);
            _mm_storeu_ps(result + i, _mm_or_ps(mask, nmask));
        }
        for (; i < n; ++i) result[i] = (a[i] >= threshold) ? high_val : low_val;
        return;
    }
#endif

    for (size_t i = 0; i < n; ++i) {
        result[i] = (a[i] >= threshold) ? high_val : low_val;
    }
}

float vector_sum(const float* a, size_t n, SIMDBackend backend) {
    if (backend == SIMDBackend::Scalar || n < 8) {
        return std::accumulate(a, a + n, 0.0f);
    }

#ifdef __AVX2__
    if (backend == SIMDBackend::AVX2) {
        __m256 vsum = _mm256_setzero_ps();
        size_t i = 0;
        for (; i + 8 <= n; i += 8) {
            vsum = _mm256_add_ps(vsum, _mm256_loadu_ps(a + i));
        }
        float arr[8];
        _mm256_storeu_ps(arr, vsum);
        float total = arr[0] + arr[1] + arr[2] + arr[3] +
                       arr[4] + arr[5] + arr[6] + arr[7];
        for (; i < n; ++i) total += a[i];
        return total;
    }
#endif

#ifdef __SSE2__
    if (backend == SIMDBackend::SSE2) {
        __m128 vsum = _mm_setzero_ps();
        size_t i = 0;
        for (; i + 4 <= n; i += 4) {
            vsum = _mm_add_ps(vsum, _mm_loadu_ps(a + i));
        }
        float arr[4];
        _mm_storeu_ps(arr, vsum);
        float total = arr[0] + arr[1] + arr[2] + arr[3];
        for (; i < n; ++i) total += a[i];
        return total;
    }
#endif

    return std::accumulate(a, a + n, 0.0f);
}

float vector_mean(const float* a, size_t n, SIMDBackend backend) {
    if (n == 0) return 0.0f;
    return vector_sum(a, n, backend) / static_cast<float>(n);
}

float vector_variance(const float* a, size_t n, SIMDBackend backend) {
    if (n <= 1) return 0.0f;
    float m = vector_mean(a, n, backend);

    std::vector<float> diff(n);
    vector_add_scalar(a, -m, diff.data(), n, backend);
    vector_multiply(diff.data(), diff.data(), diff.data(), n, backend);

    return vector_sum(diff.data(), n, backend) / static_cast<float>(n - 1);
}

float vector_dot_product(const float* a, const float* b, size_t n,
                         SIMDBackend backend) {
    std::vector<float> tmp(n);
    vector_multiply(a, b, tmp.data(), n, backend);
    return vector_sum(tmp.data(), n, backend);
}

void vector_min_max(const float* a, size_t n,
                    float& out_min, float& out_max,
                    SIMDBackend backend) {
    if (n == 0) {
        out_min = 0.0f;
        out_max = 0.0f;
        return;
    }

    out_min = a[0];
    out_max = a[0];
    for (size_t i = 1; i < n; ++i) {
        out_min = std::min(out_min, a[i]);
        out_max = std::max(out_max, a[i]);
    }
}

void vector_abs(const float* a, float* result, size_t n,
                SIMDBackend backend) {
    if (backend == SIMDBackend::Scalar || n < 8) {
        for (size_t i = 0; i < n; ++i) {
            result[i] = std::abs(a[i]);
        }
        return;
    }

#ifdef __AVX2__
    if (backend == SIMDBackend::AVX2) {
        __m256 vzero = _mm256_setzero_ps();
        __m256 vsign = _mm256_castsi256_ps(_mm256_set1_epi32(0x7FFFFFFF));
        size_t i = 0;
        for (; i + 8 <= n; i += 8) {
            __m256 va = _mm256_loadu_ps(a + i);
            _mm256_storeu_ps(result + i, _mm256_and_ps(va, vsign));
        }
        for (; i < n; ++i) result[i] = std::abs(a[i]);
        return;
    }
#endif

    for (size_t i = 0; i < n; ++i) {
        result[i] = std::abs(a[i]);
    }
}

void vector_clip(const float* a, float* result, size_t n,
                 float low, float high, SIMDBackend backend) {
    for (size_t i = 0; i < n; ++i) {
        result[i] = std::max(low, std::min(high, a[i]));
    }
}

void vector_blend(const float* a, const float* b, float* result, size_t n,
                  const float* mask, SIMDBackend backend) {
    for (size_t i = 0; i < n; ++i) {
        result[i] = (mask[i] != 0.0f) ? a[i] : b[i];
    }
}

size_t vector_argmax(const float* a, size_t n, SIMDBackend backend) {
    if (n == 0) throw std::runtime_error("argmax: empty array");
    size_t best = 0;
    for (size_t i = 1; i < n; ++i) {
        if (a[i] > a[best]) best = i;
    }
    return best;
}

size_t vector_argmin(const float* a, size_t n, SIMDBackend backend) {
    if (n == 0) throw std::runtime_error("argmin: empty array");
    size_t best = 0;
    for (size_t i = 1; i < n; ++i) {
        if (a[i] < a[best]) best = i;
    }
    return best;
}

std::vector<float> apply_spectral_transform(
    const std::vector<std::vector<float>>& bands,
    const std::vector<float>& weights,
    SIMDBackend backend) {

    if (bands.empty()) return {};
    size_t n = bands[0].size();
    std::vector<float> result(n, 0.0f);

    for (size_t b = 0; b < bands.size() && b < weights.size(); ++b) {
        std::vector<float> weighted(n);
        vector_multiply_scalar(bands[b].data(), weights[b], weighted.data(), n, backend);
        vector_add(result.data(), weighted.data(), result.data(), n, backend);
    }

    return result;
}

} // namespace glacierkz
