#include "glacierkz/spectral_indices.hpp"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <functional>

namespace glacierkz {

void apply_cloud_mask(std::vector<float>& index,
                        const std::vector<float>& cloud_prob,
                        float threshold = 0.5f) {
    for (size_t i = 0; i < index.size(); ++i) {
        if (i < cloud_prob.size() && cloud_prob[i] > threshold) {
            index[i] = std::numeric_limits<float>::quiet_NaN();
        }
    }
}

void apply_nodata_mask(std::vector<float>& index,
                        const std::vector<float>& nodata_mask) {
    for (size_t i = 0; i < index.size(); ++i) {
        if (i < nodata_mask.size() && nodata_mask[i] == 0.0f) {
            index[i] = std::numeric_limits<float>::quiet_NaN();
        }
    }
}

std::vector<float> compute_glacier_area(const std::vector<float>& ndsi,
                                          float threshold = 0.4f) {
    std::vector<float> binary(ndsi.size());
    for (size_t i = 0; i < ndsi.size(); ++i) {
        bool is_water = !std::isnan(ndsi[i]) && ndsi[i] > threshold;
        bool is_snow = !std::isnan(ndsi[i]) && ndsi[i] > threshold;
        binary[i] = (is_snow || is_water) ? 1.0f : 0.0f;
    }
    return binary;
}

float compute_snow_line_elevation(const std::vector<float>& ndsi,
                                    const std::vector<float>& elevation,
                                    float ndsi_threshold = 0.4f) {
    std::vector<float> snow_elevations;
    snow_elevations.reserve(ndsi.size() / 4);

    for (size_t i = 0; i < ndsi.size(); ++i) {
        if (!std::isnan(ndsi[i]) && ndsi[i] > ndsi_threshold &&
            !std::isnan(elevation[i])) {
            snow_elevations.push_back(elevation[i]);
        }
    }

    if (snow_elevations.empty()) return 0.0f;

    std::sort(snow_elevations.begin(), snow_elevations.end());
    size_t median_idx = snow_elevations.size() / 2;
    return snow_elevations[median_idx];
}

class GlacierClassification {
public:
    enum class SurfaceType {
        Snow,
        Ice,
        Rock,
        Water,
        Vegetation,
        Debris
    };

    struct ClassificationResult {
        std::vector<SurfaceType> classes;
        std::vector<float> confidence;
    };

    ClassificationResult classify(const SpectralBands& bands) const {
        size_t n = bands.size();
        ClassificationResult result;
        result.classes.resize(n);
        result.confidence.resize(n);

        NDVI ndvi_computer;
        NDSI ndsi_computer;
        NDWI ndwi_computer;

        auto ndvi = ndvi_computer.compute(bands);
        auto ndsi = ndsi_computer.compute(bands);
        auto ndwi = ndwi_computer.compute(bands);

        for (size_t i = 0; i < n; ++i) {
            if (ndsi[i] > 0.4f) {
                result.classes[i] = SurfaceType::Snow;
                result.confidence[i] = ndsi[i];
            } else if (ndwi[i] > 0.3f) {
                result.classes[i] = SurfaceType::Water;
                result.confidence[i] = ndwi[i];
            } else if (ndvi[i] > 0.3f) {
                result.classes[i] = SurfaceType::Vegetation;
                result.confidence[i] = ndvi[i];
            } else if (ndvi[i] < 0.1f && ndsi[i] < 0.0f) {
                float swir_ratio = 0.0f;
                if (!bands.swir1.empty() && !bands.swir2.empty()) {
                    float s1 = bands.swir1[i];
                    float s2 = bands.swir2[i];
                    float den = s1 + s2;
                    swir_ratio = (std::abs(den) > 1e-10f) ? (s1 - s2) / den : 0.0f;
                }
                if (swir_ratio < -0.1f) {
                    result.classes[i] = SurfaceType::Debris;
                    result.confidence[i] = 0.5f + std::abs(swir_ratio);
                } else {
                    result.classes[i] = SurfaceType::Rock;
                    result.confidence[i] = 1.0f - std::abs(ndvi[i]);
                }
            } else {
                result.classes[i] = SurfaceType::Rock;
                result.confidence[i] = 0.3f;
            }
        }

        return result;
    }
};

std::vector<float> compute_glacier_velocity(
    const std::vector<float>& feature_x,
    const std::vector<float>& feature_y,
    const std::vector<float>& displ_x,
    const std::vector<float>& displ_y,
    float pixel_size, float time_interval) {

    size_t n = feature_x.size();
    std::vector<float> velocity(n);

    for (size_t i = 0; i < n; ++i) {
        float dx = displ_x[i] * pixel_size;
        float dy = displ_y[i] * pixel_size;
        float dist = std::sqrt(dx * dx + dy * dy);
        velocity[i] = dist / time_interval;
    }

    return velocity;
}

std::vector<float> compute_terminus_position(
    const std::vector<float>& ndsi,
    int width, int height,
    float ndsi_threshold = 0.4f) {

    std::vector<float> terminus_elevations;
    terminus_elevations.reserve(height);

    for (int row = 0; row < height; ++row) {
        for (int col = width - 1; col >= 0; --col) {
            size_t idx = static_cast<size_t>(row) * width + col;
            if (!std::isnan(ndsi[idx]) && ndsi[idx] > ndsi_threshold) {
                terminus_elevations.push_back(static_cast<float>(row));
                break;
            }
        }
    }

    if (terminus_elevations.empty()) {
        return {static_cast<float>(height)};
    }

    float sum = std::accumulate(terminus_elevations.begin(),
                                 terminus_elevations.end(), 0.0f);
    return {sum / static_cast<float>(terminus_elevations.size())};
}

float compute_albedo(const SpectralBands& bands, const std::vector<float>& reflectance_scale) {
    size_t n = bands.size();
    if (n == 0) return 0.0f;

    std::vector<float> albedo(n);
    const float weights[] = {0.356f, 0.130f, 0.373f, 0.085f, 0.072f};

    for (size_t i = 0; i < n; ++i) {
        float w_sum = 0.0f;
        float a = 0.0f;

        if (!bands.blue.empty()) {
            a += weights[0] * bands.blue[i] * (reflectance_scale.size() > 0 ? reflectance_scale[i] : 1.0f);
            w_sum += weights[0];
        }
        if (!bands.green.empty()) {
            a += weights[1] * bands.green[i] * (reflectance_scale.size() > 0 ? reflectance_scale[i] : 1.0f);
            w_sum += weights[1];
        }
        if (!bands.red.empty()) {
            a += weights[2] * bands.red[i] * (reflectance_scale.size() > 0 ? reflectance_scale[i] : 1.0f);
            w_sum += weights[2];
        }
        if (!bands.nir.empty()) {
            a += weights[3] * bands.nir[i] * (reflectance_scale.size() > 0 ? reflectance_scale[i] : 1.0f);
            w_sum += weights[3];
        }
        if (!bands.swir1.empty()) {
            a += weights[4] * bands.swir1[i] * (reflectance_scale.size() > 0 ? reflectance_scale[i] : 1.0f);
            w_sum += weights[4];
        }

        albedo[i] = (w_sum > 1e-10f) ? a / w_sum : 0.0f;
    }

    float total = std::accumulate(albedo.begin(), albedo.end(), 0.0f);
    return total / static_cast<float>(n);
}

} // namespace glacierkz
