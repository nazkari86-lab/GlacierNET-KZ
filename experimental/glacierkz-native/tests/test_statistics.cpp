#include <gtest/gtest.h>
#include "glacierkz/statistics.hpp"

#include <vector>
#include <cmath>
#include <numeric>

using namespace glacierkz;

TEST(StreamingStatisticsTest, SingleValue) {
    StreamingStatistics s;
    s.update(5.0f);
    EXPECT_FLOAT_EQ(s.mean(), 5.0f);
    EXPECT_EQ(s.count(), 1u);
    EXPECT_FLOAT_EQ(s.min(), 5.0f);
    EXPECT_FLOAT_EQ(s.max(), 5.0f);
}

TEST(StreamingStatisticsTest, MultipleValues) {
    StreamingStatistics s;
    s.update(1.0f);
    s.update(2.0f);
    s.update(3.0f);
    s.update(4.0f);
    s.update(5.0f);
    EXPECT_FLOAT_EQ(s.mean(), 3.0f);
    EXPECT_EQ(s.count(), 5u);
    EXPECT_FLOAT_EQ(s.min(), 1.0f);
    EXPECT_FLOAT_EQ(s.max(), 5.0f);
    EXPECT_NEAR(s.variance(), 2.5f, 0.01f);
    EXPECT_NEAR(s.stddev(), 1.5811f, 0.01f);
}

TEST(StreamingStatisticsTest, Reset) {
    StreamingStatistics s;
    s.update(10.0f);
    s.update(20.0f);
    s.reset();
    EXPECT_EQ(s.count(), 0u);
    EXPECT_FLOAT_EQ(s.mean(), 0.0f);
}

TEST(StreamingStatisticsTest, IgnoresNaN) {
    StreamingStatistics s;
    s.update(1.0f);
    s.update(std::numeric_limits<float>::quiet_NaN());
    s.update(3.0f);
    EXPECT_EQ(s.count(), 2u);
    EXPECT_FLOAT_EQ(s.mean(), 2.0f);
}

TEST(ComputeStatsTest, Basic) {
    std::vector<float> data = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f};
    auto stats = compute_stats(data.data(), data.size());
    EXPECT_FLOAT_EQ(stats.mean, 3.0f);
    EXPECT_NEAR(stats.stddev, 1.5811f, 0.01f);
    EXPECT_FLOAT_EQ(stats.min_val, 1.0f);
    EXPECT_FLOAT_EQ(stats.max_val, 5.0f);
    EXPECT_EQ(stats.valid_count, 5u);
}

TEST(ComputeStatsTest, WithNaN) {
    std::vector<float> data = {1.0f, std::numeric_limits<float>::quiet_NaN(), 3.0f};
    auto stats = compute_stats(data.data(), data.size());
    EXPECT_FLOAT_EQ(stats.mean, 2.0f);
    EXPECT_EQ(stats.valid_count, 2u);
}

TEST(ComputePercentileTest, Median) {
    std::vector<float> data = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f};
    EXPECT_FLOAT_EQ(compute_median(data.data(), data.size()), 3.0f);
}

TEST(ComputePercentileTest, Q25) {
    std::vector<float> data = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f};
    float q25 = compute_percentile(data.data(), data.size(), 25.0f);
    EXPECT_NEAR(q25, 2.0f, 0.5f);
}

TEST(ComputeMinMaxTest, Basic) {
    std::vector<float> data = {3.0f, 1.0f, 4.0f, 1.5f, 9.0f};
    auto [mn, mx] = compute_min_max(data.data(), data.size());
    EXPECT_FLOAT_EQ(mn, 1.0f);
    EXPECT_FLOAT_EQ(mx, 9.0f);
}

TEST(ComputeRMSTest, Basic) {
    std::vector<float> data = {3.0f, 4.0f};
    EXPECT_NEAR(compute_rms(data.data(), data.size()), 3.5355f, 0.01f);
}

TEST(ZScoreTest, Basic) {
    EXPECT_NEAR(compute_z_score(5.0f, 3.0f, 2.0f), 1.0f, 0.01f);
    EXPECT_FLOAT_EQ(compute_z_score(3.0f, 3.0f, 0.0f), 0.0f);
}

TEST(ZScoreNormalizeTest, Basic) {
    std::vector<float> data = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f};
    auto result = z_score_normalize(data.data(), data.size());
    EXPECT_EQ(result.size(), 5u);
    float sum = 0.0f;
    for (auto v : result) sum += v;
    EXPECT_NEAR(sum, 0.0f, 0.01f);
}

TEST(IQRTest, Basic) {
    std::vector<float> data = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f, 6.0f, 7.0f, 8.0f, 9.0f, 10.0f};
    float iqr = compute_iqr(data.data(), data.size());
    EXPECT_GT(iqr, 0.0f);
}

TEST(HistogramTest, Basic) {
    Histogram h(10, 0.0f, 10.0f);
    for (int i = 0; i < 100; ++i) {
        h.update(static_cast<float>(i));
    }
    EXPECT_EQ(h.total_count(), 100.0f);
}

TEST(HistogramTest, Reset) {
    Histogram h(5, 0.0f, 5.0f);
    h.update(2.5f);
    h.reset();
    EXPECT_FLOAT_EQ(h.total_count(), 0.0f);
}
