#pragma once

#include <vector>
#include <functional>
#include <optional>
#include <cstddef>
#include <algorithm>
#include <stdexcept>

namespace glacierkz {

enum class PaddingMode {
    None,
    Zero,
    Reflect,
    Replicate,
    Circular
};

struct WindowConfig {
    int window_size = 256;
    int stride = 256;
    int padding = 0;
    PaddingMode padding_mode = PaddingMode::Zero;
    bool include_partial_windows = false;
    int num_channels = 1;
};

struct WindowRegion {
    int x_off;
    int y_off;
    int width;
    int height;
    bool is_padded;
    int pad_left = 0;
    int pad_top = 0;
    int pad_right = 0;
    int pad_bottom = 0;
};

class WindowExtractor {
public:
    explicit WindowExtractor(const WindowConfig& config);

    std::vector<float> extract(const std::vector<float>& raster,
                                int raster_width, int raster_height,
                                const WindowRegion& region) const;

    std::vector<std::vector<float>> extract_all(
        const std::vector<float>& raster,
        int raster_width, int raster_height) const;

    std::vector<WindowRegion> compute_regions(int raster_width,
                                               int raster_height) const;

    std::vector<std::pair<int,int>> compute_positions(int raster_width,
                                                       int raster_height) const;

    std::vector<float> extract_at(const std::vector<float>& raster,
                                   int raster_width, int raster_height,
                                   int col, int row) const;

    std::vector<float> extract_multiband(
        const std::vector<std::vector<float>>& bands,
        int raster_width, int raster_height,
        const WindowRegion& region) const;

    const WindowConfig& config() const { return config_; }

    void set_window_size(int size) { config_.window_size = size; }
    void set_stride(int s) { config_.stride = s; }
    void set_padding(int p) { config_.padding = p; }
    void set_padding_mode(PaddingMode m) { config_.padding_mode = m; }

private:
    WindowConfig config_;

    float get_pixel_with_padding(const std::vector<float>& data,
                                  int raster_width, int raster_height,
                                  int col, int row) const;

    std::vector<float> pad_data(const std::vector<float>& data,
                                 int width, int height,
                                 int pad_left, int pad_top,
                                 int pad_right, int pad_bottom) const;
};

class SlidingWindowIterator {
public:
    using value_type = std::pair<WindowRegion, std::vector<float>>;

    SlidingWindowIterator(const std::vector<float>& data,
                          int width, int height,
                          const WindowConfig& config);

    bool has_next() const;
    value_type next();

    void reset();
    size_t total_windows() const;
    size_t current_index() const;

private:
    const std::vector<float>& data_;
    int width_;
    int height_;
    WindowConfig config_;
    WindowExtractor extractor_;
    std::vector<WindowRegion> regions_;
    size_t current_idx_ = 0;
};

} // namespace glacierkz
