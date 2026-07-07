#include "glacierkz/resampling.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace glacierkz {

float Resampler::nearest_neighbor(const float* data, int src_w, int src_h,
                                   float dst_x, float dst_y,
                                   int band) {
    int sx = std::clamp(static_cast<int>(std::round(dst_x)), 0, src_w - 1);
    int sy = std::clamp(static_cast<int>(std::round(dst_y)), 0, src_h - 1);
    return data[sy * src_w + sx];
}

float Resampler::bilinear(const float* data, int src_w, int src_h,
                           float dst_x, float dst_y, int band) {
    float x0 = std::floor(dst_x);
    float y0 = std::floor(dst_y);
    int x0i = std::clamp(static_cast<int>(x0), 0, src_w - 2);
    int y0i = std::clamp(static_cast<int>(y0), 0, src_h - 2);

    float fx = dst_x - x0;
    float fy = dst_y - y0;

    fx = std::max(0.0f, std::min(1.0f, fx));
    fy = std::max(0.0f, std::min(1.0f, fy));

    float v00 = data[y0i * src_w + x0i];
    float v10 = data[y0i * src_w + x0i + 1];
    float v01 = data[(y0i + 1) * src_w + x0i];
    float v11 = data[(y0i + 1) * src_w + x0i + 1];

    float top = v00 * (1.0f - fx) + v10 * fx;
    float bot = v01 * (1.0f - fx) + v11 * fx;
    return top * (1.0f - fy) + bot * fy;
}

float Resampler::cubic_kernel(float x) {
    float ax = std::abs(x);
    if (ax <= 1.0f) {
        return (1.5f * ax * ax * ax) - (2.5f * ax * ax) + 1.0f;
    } else if (ax < 2.0f) {
        return (-0.5f * ax * ax * ax) + (2.5f * ax * ax) - (4.0f * ax) + 2.0f;
    }
    return 0.0f;
}

float Resampler::bicubic(const float* data, int src_w, int src_h,
                          float dst_x, float dst_y, int band) {
    int x0 = static_cast<int>(std::floor(dst_x));
    int y0 = static_cast<int>(std::floor(dst_y));
    float fx = dst_x - x0;
    float fy = dst_y - y0;

    float result = 0.0f;
    for (int m = -1; m <= 2; ++m) {
        for (int n = -1; n <= 2; ++n) {
            int sx = std::clamp(x0 + n, 0, src_w - 1);
            int sy = std::clamp(y0 + m, 0, src_h - 1);
            float w = cubic_kernel(static_cast<float>(n) - fx) *
                      cubic_kernel(static_cast<float>(m) - fy);
            result += data[sy * src_w + sx] * w;
        }
    }
    return result;
}

float Resampler::lanczos(const float* data, int src_w, int src_h,
                          float dst_x, float dst_y, int band, int lobes) {
    int x0 = static_cast<int>(std::floor(dst_x));
    int y0 = static_cast<int>(std::floor(dst_y));
    float fx = dst_x - x0;
    float fy = dst_y - y0;

    float result = 0.0f;
    float sum_weights = 0.0f;

    for (int m = -lobes + 1; m <= lobes; ++m) {
        for (int n = -lobes + 1; n <= lobes; ++n) {
            int sx = std::clamp(x0 + n, 0, src_w - 1);
            int sy = std::clamp(y0 + m, 0, src_h - 1);

            float dx = static_cast<float>(n) - fx;
            float dy = static_cast<float>(m) - fy;

            float wx = (std::abs(dx) < 1e-6f) ? 1.0f :
                        (std::sin(dx * static_cast<float>(M_PI)) /
                         (dx * static_cast<float>(M_PI)));
            float wy = (std::abs(dy) < 1e-6f) ? 1.0f :
                        (std::sin(dy * static_cast<float>(M_PI)) /
                         (dy * static_cast<float>(M_PI)));

            if (std::abs(dx) > static_cast<float>(lobes)) wx = 0.0f;
            if (std::abs(dy) > static_cast<float>(lobes)) wy = 0.0f;

            float w = wx * wy;
            result += data[sy * src_w + sx] * w;
            sum_weights += w;
        }
    }

    return (sum_weights > 1e-10f) ? result / sum_weights : result;
}

std::vector<float> Resampler::resample_bilinear(const float* data,
                                                  int src_w, int src_h,
                                                  int dst_w, int dst_h) {
    std::vector<float> result(dst_w * dst_h);
    float x_scale = static_cast<float>(src_w - 1) / static_cast<float>(dst_w - 1);
    float y_scale = static_cast<float>(src_h - 1) / static_cast<float>(dst_h - 1);

    for (int dy = 0; dy < dst_h; ++dy) {
        for (int dx = 0; dx < dst_w; ++dx) {
            float src_x = dx * x_scale;
            float src_y = dy * y_scale;
            result[dy * dst_w + dx] = bilinear(data, src_w, src_h, src_x, src_y, 0);
        }
    }
    return result;
}

std::vector<std::vector<float>> PyramidBuilder::build_pyramid(
    const float* data, int width, int height, int num_levels,
    int (*downsample_fn)(const float*, int, int, float*)) {

    std::vector<std::vector<float>> pyramid;
    std::vector<float> current(data, data + width * height);
    int cur_w = width;
    int cur_h = height;

    pyramid.push_back(current);

    for (int level = 1; level < num_levels; ++level) {
        int new_w = cur_w / 2;
        int new_h = cur_h / 2;
        if (new_w < 1 || new_h < 1) break;

        std::vector<float> downsampled(new_w * new_h);
        for (int y = 0; y < new_h; ++y) {
            for (int x = 0; x < new_w; ++x) {
                float sum = 0.0f;
                for (int ky = 0; ky < 2; ++ky) {
                    for (int kx = 0; kx < 2; ++kx) {
                        int sx = std::clamp(x * 2 + kx, 0, cur_w - 1);
                        int sy = std::clamp(y * 2 + ky, 0, cur_h - 1);
                        sum += current[sy * cur_w + sx];
                    }
                }
                downsampled[y * new_w + x] = sum / 4.0f;
            }
        }

        pyramid.push_back(downsampled);
        current = std::move(downsampled);
        cur_w = new_w;
        cur_h = new_h;
    }

    return pyramid;
}

std::vector<std::vector<float>> PyramidBuilder::build_gaussian_pyramid(
    const float* data, int width, int height, int num_levels) {
    return build_pyramid(data, width, height, num_levels, nullptr);
}

std::vector<std::pair<int, int>> PyramidBuilder::level_sizes(
    int width, int height, int num_levels) {
    std::vector<std::pair<int, int>> sizes;
    int cur_w = width;
    int cur_h = height;
    for (int i = 0; i < num_levels && cur_w >= 1 && cur_h >= 1; ++i) {
        sizes.emplace_back(cur_w, cur_h);
        cur_w /= 2;
        cur_h /= 2;
    }
    return sizes;
}

std::vector<float> ThumbnailGenerator::generate_nearest(
    const float* data, int width, int height,
    int thumb_width, int thumb_height) {
    std::vector<float> thumb(thumb_width * thumb_height);
    float x_scale = static_cast<float>(width) / static_cast<float>(thumb_width);
    float y_scale = static_cast<float>(height) / static_cast<float>(thumb_height);

    for (int ty = 0; ty < thumb_height; ++ty) {
        for (int tx = 0; tx < thumb_width; ++tx) {
            int sx = std::clamp(static_cast<int>(tx * x_scale), 0, width - 1);
            int sy = std::clamp(static_cast<int>(ty * y_scale), 0, height - 1);
            thumb[ty * thumb_width + tx] = data[sy * width + sx];
        }
    }
    return thumb;
}

std::vector<float> ThumbnailGenerator::generate_bilinear(
    const float* data, int width, int height,
    int thumb_width, int thumb_height) {
    std::vector<float> thumb(thumb_width * thumb_height);
    float x_scale = static_cast<float>(width - 1) / static_cast<float>(thumb_width - 1);
    float y_scale = static_cast<float>(height - 1) / static_cast<float>(thumb_height - 1);

    for (int ty = 0; ty < thumb_height; ++ty) {
        for (int tx = 0; tx < thumb_width; ++tx) {
            float src_x = tx * x_scale;
            float src_y = ty * y_scale;
            thumb[ty * thumb_width + tx] =
                Resampler::bilinear(data, width, height, src_x, src_y, 0);
        }
    }
    return thumb;
}

std::vector<float> ThumbnailGenerator::generate_average(
    const float* data, int width, int height,
    int thumb_width, int thumb_height) {
    std::vector<float> thumb(thumb_width * thumb_height);
    float x_scale = static_cast<float>(width) / static_cast<float>(thumb_width);
    float y_scale = static_cast<float>(height) / static_cast<float>(thumb_height);

    int block_w = std::max(1, static_cast<int>(x_scale));
    int block_h = std::max(1, static_cast<int>(y_scale));

    for (int ty = 0; ty < thumb_height; ++ty) {
        for (int tx = 0; tx < thumb_width; ++tx) {
            float sum = 0.0f;
            int count = 0;
            for (int by = 0; by < block_h; ++by) {
                for (int bx = 0; bx < block_w; ++bx) {
                    int sx = std::min(tx * block_w + bx, width - 1);
                    int sy = std::min(ty * block_h + by, height - 1);
                    sum += data[sy * width + sx];
                    count++;
                }
            }
            thumb[ty * thumb_width + tx] = (count > 0) ? sum / static_cast<float>(count) : 0.0f;
        }
    }
    return thumb;
}

} // namespace glacierkz
