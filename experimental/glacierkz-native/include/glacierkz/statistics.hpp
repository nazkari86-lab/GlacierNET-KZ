#pragma once

#include <vector>
#include <cstddef>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <stdexcept>
#include <optional>

namespace glacierkz {

struct BasicStats {
    size_t count = 0;
    float min = 0.0f;
    float max = 0.0f;
    float mean = 0.0f;
    float variance = 0.0f;
    float std_dev = 0.0f;
    float sum = 0.0f;
};

struct PercentileResult {
    float value = 0.0f;
    float rank = 0.0f;
};

class StreamingStatistics {
public:
    StreamingStatistics();

    void reset();
    void add(float value);

    size_t count() const;
    float mean() const;
    float variance() const;
    float std_dev() const;
    float min() const;
    float max() const;
    float sum() const;

    BasicStats compute() const;

private:
    size_t count_ = 0;
    float min_ = std::numeric_limits<float>::max();
    float max_ = std::numeric_limits<float>::lowest();
    float sum_ = 0.0f;
    float m2_ = 0.0f;
    float mean_ = 0.0f;
};

class Histogram {
public:
    Histogram() = default;
    Histogram(float min_val, float max_val, size_t num_bins);

    void add(float value);
    void add_batch(const float* values, size_t count);

    size_t bin_count() const { return bins_.size(); }
    size_t total_count() const { return total_count_; }
    size_t count_in_bin(size_t bin_index) const;
    float bin_edge_low(size_t bin_index) const;
    float bin_edge_high(size_t bin_index) const;

    std::vector<size_t> counts() const { return bins_; }
    std::vector<float> bin_edges() const;

    void set_nodata(float nodata) { nodata_ = nodata; has_nodata_ = true; }
    float mode() const;
    float median() const;

    std::vector<float> compute_percentiles(
        const std::vector<float>& percentiles) const;

private:
    float min_ = 0.0f;
    float max_ = 1.0f;
    size_t num_bins_ = 256;
    std::vector<size_t> bins_;
    size_t total_count_ = 0;
    bool has_nodata_ = false;
    float nodata_ = 0.0f;

    size_t compute_bin(float value) const;
};

BasicStats compute_basic_stats(const float* data, size_t n,
                                float nodata = std::numeric_limits<float>::quiet_NaN(),
                                bool skip_nodata = false);

float compute_percentile(const float* data, size_t n, float percentile);

std::vector<float> compute_percentiles(const float* data, size_t n,
                                        const std::vector<float>& percentiles);

std::vector<float> z_score_normalize(const float* data, size_t n,
                                      float nodata = std::numeric_limits<float>::quiet_NaN(),
                                      bool skip_nodata = false);

std::vector<float> min_max_normalize(const float* data, size_t n,
                                      float nodata = std::numeric_limits<float>::quiet_NaN(),
                                      bool skip_nodata = false);

std::vector<float> robust_scale(const float* data, size_t n,
                                 float nodata = std::numeric_limits<float>::quiet_NaN(),
                                 bool skip_nodata = false);

float compute_correlation(const float* a, const float* b, size_t n);

std::pair<float, float> linear_regression(const float* x, const float* y, size_t n);

} // namespace glacierkz
