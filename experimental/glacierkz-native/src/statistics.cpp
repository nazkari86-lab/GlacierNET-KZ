#include "glacierkz/statistics.hpp"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <map>

namespace glacierkz {

void StreamingStatistics::update(float value) {
    if (std::isnan(value) || std::isinf(value)) return;

    count_++;
    if (count_ == 1) {
        mean_ = value;
        m2_ = 0.0f;
        min_ = value;
        max_ = value;
    } else {
        float delta = value - mean_;
        mean_ += delta / static_cast<float>(count_);
        float delta2 = value - mean_;
        m2_ += delta * delta2;
        min_ = std::min(min_, value);
        max_ = std::max(max_, value);
    }
}

float StreamingStatistics::mean() const {
    return mean_;
}

float StreamingStatistics::variance() const {
    if (count_ < 2) return 0.0f;
    return m2_ / static_cast<float>(count_ - 1);
}

float StreamingStatistics::stddev() const {
    return std::sqrt(variance());
}

float StreamingStatistics::min() const {
    return min_;
}

float StreamingStatistics::max() const {
    return max_;
}

size_t StreamingStatistics::count() const {
    return count_;
}

void StreamingStatistics::reset() {
    count_ = 0;
    mean_ = 0.0f;
    m2_ = 0.0f;
    min_ = 0.0f;
    max_ = 0.0f;
}

BasicStats compute_stats(const float* data, size_t n) {
    if (n == 0) throw std::runtime_error("compute_stats: empty data");

    BasicStats stats{};
    stats.min_val = data[0];
    stats.max_val = data[0];
    stats.sum = 0.0f;
    stats.sum_sq = 0.0f;
    stats.valid_count = 0;

    for (size_t i = 0; i < n; ++i) {
        if (std::isnan(data[i])) continue;
        stats.valid_count++;
        stats.sum += data[i];
        stats.sum_sq += data[i] * data[i];
        stats.min_val = std::min(stats.min_val, data[i]);
        stats.max_val = std::max(stats.max_val, data[i]);
    }

    if (stats.valid_count > 0) {
        stats.mean = stats.sum / static_cast<float>(stats.valid_count);
        float variance = (stats.sum_sq / static_cast<float>(stats.valid_count)) -
                          stats.mean * stats.mean;
        stats.stddev = std::sqrt(std::max(0.0f, variance));
    } else {
        stats.mean = 0.0f;
        stats.stddev = 0.0f;
    }

    return stats;
}

float compute_percentile(const float* data, size_t n, float percentile) {
    if (n == 0) throw std::runtime_error("percentile: empty data");
    if (percentile < 0.0f || percentile > 100.0f) {
        throw std::invalid_argument("percentile: must be 0-100");
    }

    std::vector<float> sorted_data(data, data + n);
    std::sort(sorted_data.begin(), sorted_data.end());

    float index = (percentile / 100.0f) * static_cast<float>(n - 1);
    size_t lower = static_cast<size_t>(std::floor(index));
    size_t upper = static_cast<size_t>(std::ceil(index));

    if (lower == upper) return sorted_data[lower];

    float frac = index - static_cast<float>(lower);
    return sorted_data[lower] * (1.0f - frac) + sorted_data[upper] * frac;
}

float compute_median(const float* data, size_t n) {
    if (n == 0) throw std::runtime_error("median: empty data");
    return compute_percentile(data, n, 50.0f);
}

std::pair<float, float> compute_min_max(const float* data, size_t n) {
    if (n == 0) throw std::runtime_error("min_max: empty data");
    float mn = data[0];
    float mx = data[0];
    for (size_t i = 1; i < n; ++i) {
        mn = std::min(mn, data[i]);
        mx = std::max(mx, data[i]);
    }
    return {mn, mx};
}

float compute_rms(const float* data, size_t n) {
    if (n == 0) return 0.0f;
    double sum_sq = 0.0;
    for (size_t i = 0; i < n; ++i) {
        if (!std::isnan(data[i])) {
            sum_sq += static_cast<double>(data[i]) * static_cast<double>(data[i]);
        }
    }
    return static_cast<float>(std::sqrt(sum_sq / static_cast<double>(n)));
}

float compute_z_score(float value, float mean, float stddev) {
    if (stddev < 1e-10f) return 0.0f;
    return (value - mean) / stddev;
}

float compute_iqr(const float* data, size_t n) {
    float q25 = compute_percentile(data, n, 25.0f);
    float q75 = compute_percentile(data, n, 75.0f);
    return q75 - q25;
}

std::vector<float> z_score_normalize(const float* data, size_t n) {
    BasicStats stats = compute_stats(data, n);
    std::vector<float> result(n);
    float inv_sd = (stats.stddev > 1e-10f) ? 1.0f / stats.stddev : 0.0f;
    for (size_t i = 0; i < n; ++i) {
        result[i] = (data[i] - stats.mean) * inv_sd;
    }
    return result;
}

void Histogram::update(float value) {
    float normalized = (value - offset_) * scale_;
    size_t bin = static_cast<size_t>(std::floor(normalized));
    if (bin < counts_.size()) {
        counts_[bin]++;
    }
}

std::vector<size_t> Histogram::counts() const {
    return counts_;
}

size_t Histogram::bin_count() const {
    return num_bins_;
}

float Histogram::bin_width() const {
    return bin_width_;
}

float Histogram::total_count() const {
    return static_cast<float>(std::accumulate(counts_.begin(), counts_.end(), 0ULL));
}

void Histogram::reset() {
    std::fill(counts_.begin(), counts_.end(), 0);
}

} // namespace glacierkz
