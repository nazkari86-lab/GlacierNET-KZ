#include "glacierkz/sliding_window.hpp"

#include <algorithm>
#include <stdexcept>
#include <cmath>

namespace glacierkz {

WindowExtractor::WindowExtractor(const WindowConfig& config) : config_(config) {
    if (config_.window_size <= 0) {
        throw std::invalid_argument("Window size must be positive");
    }
    if (config_.stride <= 0) {
        throw std::invalid_argument("Stride must be positive");
    }
}

std::vector<float> WindowExtractor::extract(
    const std::vector<float>& raster,
    int raster_width, int raster_height,
    const WindowRegion& region) const {

    int ws = config_.window_size;
    int total_pixels = ws * ws * config_.num_channels;
    std::vector<float> window(total_pixels, 0.0f);

    if (region.is_padded) {
        for (int c = 0; c < config_.num_channels; ++c) {
            for (int wy = 0; wy < ws; ++wy) {
                for (int wx = 0; wx < ws; ++wx) {
                    int src_col = region.x_off + wx - region.pad_left;
                    int src_row = region.y_off + wy - region.pad_top;
                    float val = get_pixel_with_padding(raster, raster_width, raster_height,
                                                        src_col, src_row);
                    size_t idx = static_cast<size_t>(c) * ws * ws + wy * ws + wx;
                    window[idx] = val;
                }
            }
        }
    } else {
        for (int c = 0; c < config_.num_channels; ++c) {
            for (int wy = 0; wy < region.height; ++wy) {
                for (int wx = 0; wx < region.width; ++wx) {
                    int src_col = region.x_off + wx;
                    int src_row = region.y_off + wy;
                    if (src_col >= 0 && src_col < raster_width &&
                        src_row >= 0 && src_row < raster_height) {
                        size_t src_idx = static_cast<size_t>(src_row) * raster_width + src_col;
                        size_t dst_idx = static_cast<size_t>(c) * ws * ws + wy * ws + wx;
                        if (src_idx < raster.size()) {
                            window[dst_idx] = raster[src_idx];
                        }
                    }
                }
            }
        }
    }

    return window;
}

std::vector<std::vector<float>> WindowExtractor::extract_all(
    const std::vector<float>& raster,
    int raster_width, int raster_height) const {

    auto regions = compute_regions(raster_width, raster_height);
    std::vector<std::vector<float>> windows;
    windows.reserve(regions.size());

    for (const auto& region : regions) {
        windows.push_back(extract(raster, raster_width, raster_height, region));
    }

    return windows;
}

std::vector<WindowRegion> WindowExtractor::compute_regions(
    int raster_width, int raster_height) const {

    std::vector<WindowRegion> regions;

    int ws = config_.window_size;
    int stride = config_.stride;
    int pad = config_.padding;

    int effective_w = raster_width;
    int effective_h = raster_height;

    if (!config_.include_partial_windows) {
        int cols = (effective_w - ws + stride) / stride;
        int rows = (effective_h - ws + stride) / stride;

        for (int row = 0; row < rows; ++row) {
            for (int col = 0; col < cols; ++col) {
                WindowRegion region;
                region.x_off = col * stride;
                region.y_off = row * stride;
                region.width = ws;
                region.height = ws;
                region.is_padded = (pad > 0);
                region.pad_left = pad;
                region.pad_top = pad;
                region.pad_right = pad;
                region.pad_bottom = pad;
                regions.push_back(region);
            }
        }
    } else {
        for (int y = 0; y < effective_h; y += stride) {
            for (int x = 0; x < effective_w; x += stride) {
                WindowRegion region;
                region.x_off = x;
                region.y_off = y;
                region.width = std::min(ws, effective_w - x);
                region.height = std::min(ws, effective_h - y);
                region.is_padded = (pad > 0);

                if (pad > 0) {
                    region.pad_left = std::min(pad, x);
                    region.pad_top = std::min(pad, y);
                    region.pad_right = std::min(pad, raster_width - (x + region.width));
                    region.pad_bottom = std::min(pad, raster_height - (y + region.height));
                }

                regions.push_back(region);
            }
        }
    }

    return regions;
}

std::vector<std::pair<int,int>> WindowExtractor::compute_positions(
    int raster_width, int raster_height) const {

    std::vector<std::pair<int,int>> positions;
    int stride = config_.stride;
    int ws = config_.window_size;

    for (int y = 0; y <= raster_height - ws; y += stride) {
        for (int x = 0; x <= raster_width - ws; x += stride) {
            positions.emplace_back(x, y);
        }
    }

    return positions;
}

std::vector<float> WindowExtractor::extract_at(
    const std::vector<float>& raster,
    int raster_width, int raster_height,
    int col, int row) const {

    WindowRegion region;
    region.x_off = col;
    region.y_off = row;
    region.width = config_.window_size;
    region.height = config_.window_size;
    region.is_padded = false;

    return extract(raster, raster_width, raster_height, region);
}

std::vector<float> WindowExtractor::extract_multiband(
    const std::vector<std::vector<float>>& bands,
    int raster_width, int raster_height,
    const WindowRegion& region) const {

    int ws = config_.window_size;
    int num_bands = static_cast<int>(bands.size());
    int total_pixels = ws * ws * num_bands;
    std::vector<float> window(total_pixels, 0.0f);

    for (int c = 0; c < num_bands; ++c) {
        for (int wy = 0; wy < ws; ++wy) {
            for (int wx = 0; wx < ws; ++wx) {
                int src_col = region.x_off + wx;
                int src_row = region.y_off + wy;
                float val = 0.0f;

                if (src_col >= 0 && src_col < raster_width &&
                    src_row >= 0 && src_row < raster_height) {
                    size_t src_idx = static_cast<size_t>(src_row) * raster_width + src_col;
                    if (src_idx < bands[c].size()) {
                        val = bands[c][src_idx];
                    }
                }

                size_t dst_idx = (static_cast<size_t>(c) * ws * ws + wy * ws + wx);
                window[dst_idx] = val;
            }
        }
    }

    return window;
}

float WindowExtractor::get_pixel_with_padding(
    const std::vector<float>& data,
    int raster_width, int raster_height,
    int col, int row) const {

    if (col >= 0 && col < raster_width && row >= 0 && row < raster_height) {
        size_t idx = static_cast<size_t>(row) * raster_width + col;
        if (idx < data.size()) {
            return data[idx];
        }
    }

    switch (config_.padding_mode) {
        case PaddingMode::Zero:
            return 0.0f;

        case PaddingMode::Replicate: {
            int c = std::max(0, std::min(col, raster_width - 1));
            int r = std::max(0, std::min(row, raster_height - 1));
            size_t idx = static_cast<size_t>(r) * raster_width + c;
            return (idx < data.size()) ? data[idx] : 0.0f;
        }

        case PaddingMode::Reflect: {
            int c = col;
            int r = row;
            if (c < 0) c = -c;
            if (c >= raster_width) c = 2 * raster_width - 2 - c;
            if (r < 0) r = -r;
            if (r >= raster_height) r = 2 * raster_height - 2 - r;
            c = std::max(0, std::min(c, raster_width - 1));
            r = std::max(0, std::min(r, raster_height - 1));
            size_t idx = static_cast<size_t>(r) * raster_width + c;
            return (idx < data.size()) ? data[idx] : 0.0f;
        }

        case PaddingMode::Circular: {
            int c = ((col % raster_width) + raster_width) % raster_width;
            int r = ((row % raster_height) + raster_height) % raster_height;
            size_t idx = static_cast<size_t>(r) * raster_width + c;
            return (idx < data.size()) ? data[idx] : 0.0f;
        }

        case PaddingMode::None:
        default:
            return 0.0f;
    }
}

std::vector<float> WindowExtractor::pad_data(
    const std::vector<float>& data,
    int width, int height,
    int pad_left, int pad_top,
    int pad_right, int pad_bottom) const {

    int new_w = width + pad_left + pad_right;
    int new_h = height + pad_top + pad_bottom;
    std::vector<float> padded(static_cast<size_t>(new_w) * new_h, 0.0f);

    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            size_t src_idx = static_cast<size_t>(y) * width + x;
            size_t dst_idx = static_cast<size_t>(y + pad_top) * new_w + (x + pad_left);
            padded[dst_idx] = data[src_idx];
        }
    }

    return padded;
}

SlidingWindowIterator::SlidingWindowIterator(
    const std::vector<float>& data,
    int width, int height,
    const WindowConfig& config)
    : data_(data), width_(width), height_(height),
      config_(config), extractor_(config) {
    regions_ = extractor_.compute_regions(width_, height_);
}

bool SlidingWindowIterator::has_next() const {
    return current_idx_ < regions_.size();
}

SlidingWindowIterator::value_type SlidingWindowIterator::next() {
    if (!has_next()) {
        throw std::runtime_error("No more windows");
    }
    auto& region = regions_[current_idx_];
    auto data = extractor_.extract(data_, width_, height_, region);
    ++current_idx_;
    return {region, std::move(data)};
}

void SlidingWindowIterator::reset() {
    current_idx_ = 0;
}

size_t SlidingWindowIterator::total_windows() const {
    return regions_.size();
}

size_t SlidingWindowIterator::current_index() const {
    return current_idx_;
}

} // namespace glacierkz
