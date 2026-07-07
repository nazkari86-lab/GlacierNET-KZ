#pragma once

#include <vector>
#include <string>
#include <functional>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <array>
#include <stdexcept>

namespace glacierkz {

struct SpectralBands {
    std::vector<float> blue;
    std::vector<float> green;
    std::vector<float> red;
    std::vector<float> nir;
    std::vector<float> swir1;
    std::vector<float> swir2;
    std::vector<float> red_edge;
    std::vector<float> coastal;
    std::vector<float> cirrus;

    size_t size() const {
        if (!blue.empty()) return blue.size();
        if (!green.empty()) return green.size();
        if (!red.empty()) return red.size();
        if (!nir.empty()) return nir.size();
        return 0;
    }
};

class SpectralIndex {
public:
    virtual ~SpectralIndex() = default;
    virtual std::string name() const = 0;
    virtual std::string formula() const = 0;
    virtual std::vector<float> compute(const SpectralBands& bands) const = 0;
    virtual std::array<float, 2> valid_range() const = 0;

    static constexpr float clamp_value(float v, float lo, float hi) {
        return std::max(lo, std::min(v, hi));
    }
};

class NDSI : public SpectralIndex {
public:
    std::string name() const override { return "NDSI"; }
    std::string formula() const override { return "(Green - SWIR1) / (Green + SWIR1)"; }
    std::array<float, 2> valid_range() const override { return {-1.0f, 1.0f}; }

    std::vector<float> compute(const SpectralBands& bands) const override {
        size_t n = bands.size();
        std::vector<float> result(n);
        for (size_t i = 0; i < n; ++i) {
            float g = bands.green[i];
            float s = bands.swir1[i];
            float denom = g + s;
            result[i] = (std::abs(denom) > 1e-10f) ? (g - s) / denom : 0.0f;
        }
        return result;
    }
};

class NDWI : public SpectralIndex {
public:
    std::string name() const override { return "NDWI"; }
    std::string formula() const override { return "(Green - NIR) / (Green + NIR)"; }
    std::array<float, 2> valid_range() const override { return {-1.0f, 1.0f}; }

    std::vector<float> compute(const SpectralBands& bands) const override {
        size_t n = bands.size();
        std::vector<float> result(n);
        for (size_t i = 0; i < n; ++i) {
            float g = bands.green[i];
            float nir = bands.nir[i];
            float denom = g + nir;
            result[i] = (std::abs(denom) > 1e-10f) ? (g - nir) / denom : 0.0f;
        }
        return result;
    }
};

class NDVI : public SpectralIndex {
public:
    std::string name() const override { return "NDVI"; }
    std::string formula() const override { return "(NIR - Red) / (NIR + Red)"; }
    std::array<float, 2> valid_range() const override { return {-1.0f, 1.0f}; }

    std::vector<float> compute(const SpectralBands& bands) const override {
        size_t n = bands.size();
        std::vector<float> result(n);
        for (size_t i = 0; i < n; ++i) {
            float nir = bands.nir[i];
            float r = bands.red[i];
            float denom = nir + r;
            result[i] = (std::abs(denom) > 1e-10f) ? (nir - r) / denom : 0.0f;
        }
        return result;
    }
};

class EVI : public SpectralIndex {
public:
    std::string name() const override { return "EVI"; }
    std::string formula() const override {
        return "2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)";
    }
    std::array<float, 2> valid_range() const override { return {-1.0f, 1.0f}; }

    std::vector<float> compute(const SpectralBands& bands) const override {
        size_t n = bands.size();
        std::vector<float> result(n);
        const float C1 = 6.0f, C2 = 7.5f, L = 1.0f, G = 2.5f;
        for (size_t i = 0; i < n; ++i) {
            float nir = bands.nir[i];
            float r = bands.red[i];
            float b = bands.blue[i];
            float denom = nir + C1 * r - C2 * b + L;
            result[i] = (std::abs(denom) > 1e-10f)
                         ? G * (nir - r) / denom
                         : 0.0f;
        }
        return result;
    }
};

class BSI : public SpectralIndex {
public:
    std::string name() const override { return "BSI"; }
    std::string formula() const override {
        return "((SWIR1 + Red) - (NIR + Blue)) / ((SWIR1 + Red) + (NIR + Blue))";
    }
    std::array<float, 2> valid_range() const override { return {-1.0f, 1.0f}; }

    std::vector<float> compute(const SpectralBands& bands) const override {
        size_t n = bands.size();
        std::vector<float> result(n);
        for (size_t i = 0; i < n; ++i) {
            float num = (bands.swir1[i] + bands.red[i]) - (bands.nir[i] + bands.blue[i]);
            float den = (bands.swir1[i] + bands.red[i]) + (bands.nir[i] + bands.blue[i]);
            result[i] = (std::abs(den) > 1e-10f) ? num / den : 0.0f;
        }
        return result;
    }
};

class NDMI : public SpectralIndex {
public:
    std::string name() const override { return "NDMI"; }
    std::string formula() const override { return "(NIR - SWIR1) / (NIR + SWIR1)"; }
    std::array<float, 2> valid_range() const override { return {-1.0f, 1.0f}; }

    std::vector<float> compute(const SpectralBands& bands) const override {
        size_t n = bands.size();
        std::vector<float> result(n);
        for (size_t i = 0; i < n; ++i) {
            float nir = bands.nir[i];
            float s = bands.swir1[i];
            float denom = nir + s;
            result[i] = (std::abs(denom) > 1e-10f) ? (nir - s) / denom : 0.0f;
        }
        return result;
    }
};

class SAVI : public SpectralIndex {
public:
    explicit SAVI(float L_val = 0.5f) : L_(L_val) {}
    std::string name() const override { return "SAVI"; }
    std::string formula() const override {
        return "((NIR - Red) / (NIR + Red + L)) * (1 + L)";
    }
    std::array<float, 2> valid_range() const override { return {-1.5f, 1.5f}; }

    std::vector<float> compute(const SpectralBands& bands) const override {
        size_t n = bands.size();
        std::vector<float> result(n);
        float factor = 1.0f + L_;
        for (size_t i = 0; i < n; ++i) {
            float nir = bands.nir[i];
            float r = bands.red[i];
            float denom = nir + r + L_;
            result[i] = (std::abs(denom) > 1e-10f)
                         ? ((nir - r) / denom) * factor
                         : 0.0f;
        }
        return result;
    }

private:
    float L_;
};

class MNDWI : public SpectralIndex {
public:
    std::string name() const override { return "MNDWI"; }
    std::string formula() const override { return "(Green - SWIR1) / (Green + SWIR1)"; }
    std::array<float, 2> valid_range() const override { return {-1.0f, 1.0f}; }

    std::vector<float> compute(const SpectralBands& bands) const override {
        size_t n = bands.size();
        std::vector<float> result(n);
        for (size_t i = 0; i < n; ++i) {
            float g = bands.green[i];
            float s = bands.swir1[i];
            float denom = g + s;
            result[i] = (std::abs(denom) > 1e-10f) ? (g - s) / denom : 0.0f;
        }
        return result;
    }
};

class SpectralIndexComputer {
public:
    SpectralIndexComputer() = default;

    void add_index(std::shared_ptr<SpectralIndex> index) {
        indices_.push_back(std::move(index));
    }

    std::vector<std::pair<std::string, std::vector<float>>>
    compute_all(const SpectralBands& bands) const {
        std::vector<std::pair<std::string, std::vector<float>>> results;
        results.reserve(indices_.size());
        for (const auto& idx : indices_) {
            results.emplace_back(idx->name(), idx->compute(bands));
        }
        return results;
    }

    std::vector<float> compute_single(const std::string& name,
                                       const SpectralBands& bands) const {
        for (const auto& idx : indices_) {
            if (idx->name() == name) {
                return idx->compute(bands);
            }
        }
        throw std::runtime_error("Unknown spectral index: " + name);
    }

    std::vector<std::string> available_indices() const {
        std::vector<std::string> names;
        names.reserve(indices_.size());
        for (const auto& idx : indices_) {
            names.push_back(idx->name());
        }
        return names;
    }

private:
    std::vector<std::shared_ptr<SpectralIndex>> indices_;
};

} // namespace glacierkz
