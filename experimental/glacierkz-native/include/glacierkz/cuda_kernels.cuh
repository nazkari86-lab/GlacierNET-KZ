#pragma once

#ifdef GLACIERKZ_HAS_CUDA

#include <cuda_runtime.h>
#include <cstdint>
#include <cstddef>

namespace glacierkz {
namespace cuda {

struct KernelConfig {
    int block_size = 256;
    int grid_size = 0;
    int shared_memory_bytes = 0;
    cudaStream_t stream = nullptr;
};

inline int compute_grid_size(int total_elements, int block_size) {
    return (total_elements + block_size - 1) / block_size;
}

cudaError_t gpu_vector_add(const float* a, const float* b, float* result,
                            size_t n, const KernelConfig& config = {});

cudaError_t gpu_vector_subtract(const float* a, const float* b, float* result,
                                 size_t n, const KernelConfig& config = {});

cudaError_t gpu_vector_multiply(const float* a, const float* b, float* result,
                                 size_t n, const KernelConfig& config = {});

cudaError_t gpu_vector_add_scalar(const float* a, float scalar, float* result,
                                   size_t n, const KernelConfig& config = {});

cudaError_t gpu_vector_normalize(const float* a, float* result, size_t n,
                                  float min_val, float max_val,
                                  const KernelConfig& config = {});

cudaError_t gpu_vector_threshold(const float* a, float* result, size_t n,
                                  float threshold, float low_val, float high_val,
                                  const KernelConfig& config = {});

cudaError_t gpu_compute_ndvi(const float* nir, const float* red,
                              float* result, size_t n,
                              const KernelConfig& config = {});

cudaError_t gpu_compute_ndsi(const float* green, const float* swir,
                              float* result, size_t n,
                              const KernelConfig& config = {});

cudaError_t gpu_compute_ndwi(const float* green, const float* nir,
                              float* result, size_t n,
                              const KernelConfig& config = {});

cudaError_t gpu_compute_evi(const float* nir, const float* red,
                             const float* blue, float* result, size_t n,
                             const KernelConfig& config = {});

cudaError_t gpu_apply_weighted_sum(const float* const* bands,
                                    const float* weights,
                                    float* result,
                                    int num_bands, size_t n,
                                    const KernelConfig& config = {});

cudaError_t gpu_streaming_stats(const float* data, size_t n,
                                 float* out_sum, float* out_sq_sum,
                                 float* out_min, float* out_max,
                                 const KernelConfig& config = {});

void* gpu_alloc(size_t bytes);
void gpu_free(void* ptr);
cudaError_t gpu_memcpy_to_device(void* dst, const void* src, size_t bytes);
cudaError_t gpu_memcpy_from_device(void* dst, const void* src, size_t bytes);

} // namespace cuda
} // namespace glacierkz

#endif // GLACIERKZ_HAS_CUDA
