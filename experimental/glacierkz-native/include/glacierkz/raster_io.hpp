#pragma once

#include <cstdint>
#include <string>
#include <vector>
#include <memory>
#include <optional>
#include <stdexcept>
#include <functional>
#include <array>
#include <cmath>

namespace glacierkz {

struct GeoTransform {
    double origin_x = 0.0;
    double origin_y = 0.0;
    double pixel_width = 1.0;
    double pixel_height = 1.0;
    double rotation_x = 0.0;
    double rotation_y = 0.0;

    double apply_x(int col, int row) const {
        return origin_x + col * pixel_width + row * rotation_x;
    }

    double apply_y(int col, int row) const {
        return origin_y + col * rotation_x + row * pixel_height;
    }
};

struct BandInfo {
    int band_index = 0;
    int width = 0;
    int height = 0;
    int data_type = 0;
    double nodata_value = 0.0;
    bool has_nodata = false;
    std::string description;
    double scale = 1.0;
    double offset = 0.0;
};

struct RasterMetadata {
    int width = 0;
    int height = 0;
    int band_count = 0;
    GeoTransform geo_transform;
    std::string projection_wkt;
    std::string driver_name;
    std::unordered_map<std::string, std::string> domain_metadata;
    std::vector<BandInfo> bands;
};

class RasterDataset {
public:
    RasterDataset();
    ~RasterDataset();

    RasterDataset(const RasterDataset&) = delete;
    RasterDataset& operator=(const RasterDataset&) = delete;
    RasterDataset(RasterDataset&& other) noexcept;
    RasterDataset& operator=(RasterDataset&& other) noexcept;

    static std::unique_ptr<RasterDataset> open(const std::string& filepath,
                                                bool read_only = true);

    static std::unique_ptr<RasterDataset> create(const std::string& filepath,
                                                 int width, int height, int band_count,
                                                 const std::string& driver = "GTiff",
                                                 int data_type = 6,
                                                 const GeoTransform& gt = {},
                                                 const std::string& projection = "");

    void close();
    bool is_open() const;

    int width() const;
    int height() const;
    int band_count() const;

    GeoTransform geo_transform() const;
    void set_geo_transform(const GeoTransform& gt);

    std::string projection() const;
    void set_projection(const std::string& wkt);

    BandInfo band_info(int band_index) const;

    std::vector<float> read_band(int band_index,
                                  int x_off = 0, int y_off = 0,
                                  int x_size = -1, int y_size = -1) const;

    void write_band(int band_index, const std::vector<float>& data,
                    int x_off = 0, int y_off = 0,
                    int x_size = -1, int y_size = -1);

    std::vector<std::vector<float>> read_all_bands() const;

    void write_all_bands(const std::vector<std::vector<float>>& bands);

    std::optional<float> nodata(int band_index) const;

    void set_nodata(int band_index, float value);

    std::vector<float> pixel_values(int col, int row) const;

    std::array<double, 2> pixel_to_coord(int col, int row) const;
    std::array<int, 2> coord_to_pixel(double x, double y) const;

    std::string metadata(const std::string& domain = "") const;
    void set_metadata(const std::string& key, const std::string& value,
                      const std::string& domain = "");

    bool has_overviews() const;
    void build_overviews(const std::vector<int>& levels);

    std::unique_ptr<RasterDataset> subset(int x_off, int y_off,
                                           int x_size, int y_size) const;

    std::string driver_name() const;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace glacierkz
