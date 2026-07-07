#pragma once

#include <vector>
#include <cstddef>
#include <cmath>
#include <algorithm>
#include <stdexcept>

namespace glacierkz {

enum class ResampleMethod {
    Nearest,
    Bilinear,
    Bicubic,
    Lanczos
};

class Resampler {
public:
    explicit Resampler(ResampleMethod method = ResampleMethod::Bilinear);

    std::vector<float> resample(const std::vector<float>& src,
                                 int src_width, int src_height,
                                 int dst_width, int dst_height) const;

    void set_method(ResampleMethod method) { method_ = method; }
    ResampleMethod method() const { return method_; }

    std::vector<float> resample_region(const std::vector<float>& src,
                                        int src_width, int src_height,
                                        double src_x_off, double src_y_off,
                                        double src_x_size, double src_y_size,
                                        int dst_width, int dst_height) const;

    std::vector<std::vector<float>> resample_multiband(
        const std::vector<std::vector<float>>& src_bands,
        int src_width, int src_height,
        int dst_width, int dst_height) const;

private:
    ResampleMethod method_;

    float nearest_neighbor(const float* src, int src_width, int src_height,
                            double x, double y) const;

    float bilinear_interp(const float* src, int src_width, int src_height,
                           double x, double y) const;

    float bicubic_interp(const float* src, int src_width, int src_height,
                          double x, double y) const;

    float lanczos_interp(const float* src, int src_width, int src_height,
                          double x, double y, int a = 3) const;

    static float clamp(float v, float lo, float hi) {
        return std::max(lo, std::min(v, hi));
    }

    static float cubic_kernel(float t);
    static float lanczos_kernel(float t, int a);
};

class PyramidBuilder {
public:
    PyramidBuilder(ResampleMethod method = ResampleMethod::Bilinear,
                   int num_levels = 4);

    std::vector<std::vector<float>> build(const std::vector<float>& src,
                                           int width, int height) const;

    std::vector<std::pair<int,int>> level_sizes(int width, int height) const;

private:
    Resampler resampler_;
    int num_levels_;
};

class ThumbnailGenerator {
public:
    ThumbnailGenerator(int max_dim = 256,
                       ResampleMethod method = ResampleMethod::Bilinear);

    std::vector<float> generate(const std::vector<float>& src,
                                 int width, int height) const;
    std::pair<int,int> thumbnail_size(int width, int height) const;

private:
    Resampler resampler_;
    int max_dim_;
};

} // namespace glacierkz
