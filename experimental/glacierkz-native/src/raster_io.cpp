#include "glacierkz/raster_io.hpp"
#include "glacierkz/statistics.hpp"

#include <gdal.h>
#include <gdal_priv.h>
#include <ogr_spatialref.h>

#include <spdlog/spdlog.h>

#include <filesystem>

#include <cstring>
#include <algorithm>
#include <sstream>

namespace glacierkz {

struct RasterDataset::Impl {
    GDALDataset* dataset = nullptr;
    GDALDataset* write_dataset = nullptr;
    bool read_only = true;
    std::string filepath;
    RasterMetadata meta;

    ~Impl() {
        close();
    }

    void close() {
        if (dataset) {
            GDALClose(dataset);
            dataset = nullptr;
        }
        if (write_dataset && write_dataset != dataset) {
            GDALClose(write_dataset);
            write_dataset = nullptr;
        }
    }

    void load_metadata() {
        if (!dataset) return;

        meta.width = dataset->GetRasterXSize();
        meta.height = dataset->GetRasterYSize();
        meta.band_count = dataset->GetRasterCount();

        double gt[6];
        if (dataset->GetGeoTransform(gt) == CE_None) {
            meta.geo_transform.origin_x = gt[0];
            meta.geo_transform.pixel_width = gt[1];
            meta.geo_transform.rotation_x = gt[2];
            meta.geo_transform.origin_y = gt[3];
            meta.geo_transform.rotation_y = gt[4];
            meta.geo_transform.pixel_height = gt[5];
        }

        char* proj_wkt = nullptr;
        if (dataset->GetProjectionRef()) {
            meta.projection_wkt = dataset->GetProjectionRef();
        }

        GDALDriver* driver = dataset->GetDriver();
        if (driver) {
            meta.driver_name = driver->GetDescription();
        }

        meta.bands.resize(meta.band_count);
        for (int i = 0; i < meta.band_count; ++i) {
            GDALRasterBand* band = dataset->GetRasterBand(i + 1);
            auto& bi = meta.bands[i];
            bi.band_index = i + 1;
            bi.width = band->GetXSize();
            bi.height = band->GetYSize();
            bi.data_type = band->GetRasterDataType();

            int has_nodata = 0;
            double nd = band->GetNoDataValue(&has_nodata);
            bi.has_nodata = (has_nodata != 0);
            bi.nodata_value = static_cast<float>(nd);

            const char* desc = band->GetDescription();
            if (desc) bi.description = desc;
        }
    }
};

RasterDataset::RasterDataset() : impl_(std::make_unique<Impl>()) {}

RasterDataset::~RasterDataset() = default;

RasterDataset::RasterDataset(RasterDataset&& other) noexcept = default;
RasterDataset& RasterDataset::operator=(RasterDataset&& other) noexcept = default;

std::unique_ptr<RasterDataset> RasterDataset::open(const std::string& filepath,
                                                      bool read_only) {
    GDALAllRegister();

    auto ds = std::make_unique<RasterDataset>();
    ds->impl_->filepath = filepath;
    ds->impl_->read_only = read_only;

    const char* access = read_only ? "GA_ReadOnly" : "GA_Update";
    ds->impl_->dataset = static_cast<GDALDataset*>(
        GDALOpenEx(filepath.c_str(), GDAL_OF_RASTER | (read_only ? GA_ReadOnly : GA_Update),
                   nullptr, nullptr, nullptr)
    );

    if (!ds->impl_->dataset) {
        spdlog::error("Failed to open raster: {}", filepath);
        return nullptr;
    }

    if (!read_only) {
        ds->impl_->write_dataset = ds->impl_->dataset;
    }

    ds->impl_->load_metadata();
    spdlog::info("Opened raster: {} ({}x{}, {} bands)",
                 filepath, ds->meta.width, ds->meta.height, ds->meta.band_count);

    return ds;
}

std::unique_ptr<RasterDataset> RasterDataset::create(
    const std::string& filepath, int width, int height, int band_count,
    const std::string& driver_name, int data_type,
    const GeoTransform& gt, const std::string& projection) {

    GDALAllRegister();

    GDALDriver* driver = GetGDALDriverManager()->GetDriverByName(driver_name.c_str());
    if (!driver) {
        spdlog::error("Unknown GDAL driver: {}", driver_name);
        return nullptr;
    }

    char** papszOptions = nullptr;
    GDALDataset* raw_ds = driver->Create(filepath.c_str(), width, height, band_count,
                                          static_cast<GDALDataType>(data_type),
                                          papszOptions);

    if (!raw_ds) {
        spdlog::error("Failed to create raster: {}", filepath);
        return nullptr;
    }

    double gdal_gt[6] = {
        gt.origin_x, gt.pixel_width, gt.rotation_x,
        gt.origin_y, gt.rotation_x, gt.pixel_height
    };
    raw_ds->SetGeoTransform(gdal_gt);

    if (!projection.empty()) {
        raw_ds->SetProjection(projection.c_str());
    }

    auto ds = std::make_unique<RasterDataset>();
    ds->impl_->dataset = raw_ds;
    ds->impl_->write_dataset = raw_ds;
    ds->impl_->filepath = filepath;
    ds->impl_->read_only = false;
    ds->impl_->load_metadata();

    spdlog::info("Created raster: {} ({}x{}, {} bands)",
                 filepath, width, height, band_count);

    return ds;
}

void RasterDataset::close() {
    impl_->close();
}

bool RasterDataset::is_open() const {
    return impl_->dataset != nullptr;
}

int RasterDataset::width() const { return impl_->meta.width; }
int RasterDataset::height() const { return impl_->meta.height; }
int RasterDataset::band_count() const { return impl_->meta.band_count; }

GeoTransform RasterDataset::geo_transform() const {
    return impl_->meta.geo_transform;
}

void RasterDataset::set_geo_transform(const GeoTransform& gt) {
    impl_->meta.geo_transform = gt;
    if (impl_->dataset) {
        double gdal_gt[6] = {
            gt.origin_x, gt.pixel_width, gt.rotation_x,
            gt.origin_y, gt.rotation_x, gt.pixel_height
        };
        impl_->dataset->SetGeoTransform(gdal_gt);
    }
}

std::string RasterDataset::projection() const {
    return impl_->meta.projection_wkt;
}

void RasterDataset::set_projection(const std::string& wkt) {
    impl_->meta.projection_wkt = wkt;
    if (impl_->dataset) {
        impl_->dataset->SetProjection(wkt.c_str());
    }
}

BandInfo RasterDataset::band_info(int band_index) const {
    if (band_index < 1 || band_index > impl_->meta.band_count) {
        throw std::out_of_range("Band index out of range: " + std::to_string(band_index));
    }
    return impl_->meta.bands[band_index - 1];
}

std::vector<float> RasterDataset::read_band(int band_index, int x_off, int y_off,
                                               int x_size, int y_size) const {
    if (band_index < 1 || band_index > impl_->meta.band_count) {
        throw std::out_of_range("Band index out of range");
    }

    GDALRasterBand* band = impl_->dataset->GetRasterBand(band_index);

    if (x_size <= 0) x_size = band->GetXSize();
    if (y_size <= 0) y_size = band->GetYSize();

    if (x_off < 0 || y_off < 0 ||
        x_off + x_size > band->GetXSize() ||
        y_off + y_size > band->GetYSize()) {
        throw std::out_of_range("Read region out of bounds");
    }

    std::vector<float> buffer(static_cast<size_t>(x_size) * y_size);
    GDALDataType gdal_type = band->GetRasterDataType();

    std::vector<uint8_t> raw_buffer(buffer.size() * GDALGetDataTypeSizeBytes(gdal_type));
    CPLErr err = band->RasterIO(GF_Read, x_off, y_off, x_size, y_size,
                                 raw_buffer.data(), x_size, y_size,
                                 gdal_type, 0, 0);

    if (err != CE_None) {
        throw std::runtime_error("GDAL RasterIO failed for band " +
                                  std::to_string(band_index));
    }

    switch (gdal_type) {
        case GDT_Byte: {
            auto* src = reinterpret_cast<uint8_t*>(raw_buffer.data());
            for (size_t i = 0; i < buffer.size(); ++i)
                buffer[i] = static_cast<float>(src[i]);
            break;
        }
        case GDT_Int16: {
            auto* src = reinterpret_cast<int16_t*>(raw_buffer.data());
            for (size_t i = 0; i < buffer.size(); ++i)
                buffer[i] = static_cast<float>(src[i]);
            break;
        }
        case GDT_UInt16: {
            auto* src = reinterpret_cast<uint16_t*>(raw_buffer.data());
            for (size_t i = 0; i < buffer.size(); ++i)
                buffer[i] = static_cast<float>(src[i]);
            break;
        }
        case GDT_Int32: {
            auto* src = reinterpret_cast<int32_t*>(raw_buffer.data());
            for (size_t i = 0; i < buffer.size(); ++i)
                buffer[i] = static_cast<float>(src[i]);
            break;
        }
        case GDT_Float32: {
            std::memcpy(buffer.data(), raw_buffer.data(), raw_buffer.size());
            break;
        }
        case GDT_Float64: {
            auto* src = reinterpret_cast<double*>(raw_buffer.data());
            for (size_t i = 0; i < buffer.size(); ++i)
                buffer[i] = static_cast<float>(src[i]);
            break;
        }
        default:
            throw std::runtime_error("Unsupported GDAL data type");
    }

    return buffer;
}

void RasterDataset::write_band(int band_index, const std::vector<float>& data,
                                  int x_off, int y_off, int x_size, int y_size) {
    if (band_index < 1 || band_index > impl_->meta.band_count) {
        throw std::out_of_range("Band index out of range");
    }

    GDALRasterBand* band = impl_->dataset->GetRasterBand(band_index);

    if (x_size <= 0) x_size = band->GetXSize();
    if (y_size <= 0) y_size = band->GetYSize();

    size_t expected = static_cast<size_t>(x_size) * y_size;
    if (data.size() < expected) {
        throw std::invalid_argument("Data buffer too small for write region");
    }

    CPLErr err = band->RasterIO(GF_Write, x_off, y_off, x_size, y_size,
                                 const_cast<float*>(data.data()),
                                 x_size, y_size, GDT_Float32, 0, 0);

    if (err != CE_None) {
        throw std::runtime_error("GDAL write failed for band " +
                                  std::to_string(band_index));
    }
}

std::vector<std::vector<float>> RasterDataset::read_all_bands() const {
    std::vector<std::vector<float>> bands(impl_->meta.band_count);
    for (int i = 0; i < impl_->meta.band_count; ++i) {
        bands[i] = read_band(i + 1);
    }
    return bands;
}

void RasterDataset::write_all_bands(const std::vector<std::vector<float>>& bands) {
    if (bands.size() != static_cast<size_t>(impl_->meta.band_count)) {
        throw std::invalid_argument("Band count mismatch");
    }
    for (size_t i = 0; i < bands.size(); ++i) {
        write_band(static_cast<int>(i + 1), bands[i]);
    }
}

std::optional<float> RasterDataset::nodata(int band_index) const {
    if (band_index < 1 || band_index > impl_->meta.band_count) {
        return std::nullopt;
    }
    const auto& bi = impl_->meta.bands[band_index - 1];
    if (bi.has_nodata) {
        return static_cast<float>(bi.nodata_value);
    }
    return std::nullopt;
}

void RasterDataset::set_nodata(int band_index, float value) {
    if (band_index < 1 || band_index > impl_->meta.band_count) {
        throw std::out_of_range("Band index out of range");
    }
    auto& bi = impl_->meta.bands[band_index - 1];
    bi.has_nodata = true;
    bi.nodata_value = value;

    GDALRasterBand* band = impl_->dataset->GetRasterBand(band_index);
    band->SetNoDataValue(value);
}

std::vector<float> RasterDataset::pixel_values(int col, int row) const {
    if (col < 0 || col >= impl_->meta.width || row < 0 || row >= impl_->meta.height) {
        throw std::out_of_range("Pixel coordinate out of range");
    }
    std::vector<float> values(impl_->meta.band_count);
    for (int b = 0; b < impl_->meta.band_count; ++b) {
        std::vector<float> single = read_band(b + 1, col, row, 1, 1);
        values[b] = single[0];
    }
    return values;
}

std::array<double, 2> RasterDataset::pixel_to_coord(int col, int row) const {
    const auto& gt = impl_->meta.geo_transform;
    double x = gt.apply_x(col, row);
    double y = gt.apply_y(col, row);
    return {x, y};
}

std::array<int, 2> RasterDataset::coord_to_pixel(double x, double y) const {
    const auto& gt = impl_->meta.geo_transform;
    double det = gt.pixel_width * gt.pixel_height - gt.rotation_x * gt.rotation_x;
    if (std::abs(det) < 1e-12) {
        throw std::runtime_error("Singular geotransform");
    }
    double dx = x - gt.origin_x;
    double dy = y - gt.origin_y;
    int col = static_cast<int>(std::round((dx * gt.pixel_height - dy * gt.rotation_x) / det));
    int row = static_cast<int>(std::round((dy * gt.pixel_width - dx * gt.rotation_x) / det));
    return {col, row};
}

std::string RasterDataset::metadata(const std::string& domain) const {
    if (domain.empty()) {
        char** md = impl_->dataset->GetMetadata();
        if (!md) return "";
        std::ostringstream oss;
        for (int i = 0; md[i]; ++i) {
            oss << md[i] << "\n";
        }
        return oss.str();
    }
    char** md = impl_->dataset->GetMetadata(domain.c_str());
    if (!md) return "";
    std::ostringstream oss;
    for (int i = 0; md[i]; ++i) {
        oss << md[i] << "\n";
    }
    return oss.str();
}

void RasterDataset::set_metadata(const std::string& key, const std::string& value,
                                   const std::string& domain) {
    impl_->dataset->SetMetadataItem(key.c_str(), value.c_str(),
                                     domain.empty() ? nullptr : domain.c_str());
}

bool RasterDataset::has_overviews() const {
    if (!impl_->dataset) return false;
    GDALRasterBand* band = impl_->dataset->GetRasterBand(1);
    return band->GetOverviewCount() > 0;
}

void RasterDataset::build_overviews(const std::vector<int>& levels) {
    if (impl_->read_only) {
        throw std::runtime_error("Cannot build overviews on read-only dataset");
    }
    impl_->dataset->BuildOverviews("NEAREST", static_cast<int>(levels.size()),
                                    const_cast<int*>(levels.data()));
}

std::unique_ptr<RasterDataset> RasterDataset::subset(int x_off, int y_off,
                                                        int x_size, int y_size) const {
    std::vector<std::vector<float>> bands;
    for (int b = 1; b <= band_count(); ++b) {
        bands.push_back(read_band(b, x_off, y_off, x_size, y_size));
    }

    GeoTransform sub_gt = geo_transform();
    auto [px, py] = pixel_to_coord(x_off, y_off);
    sub_gt.origin_x = px;
    sub_gt.origin_y = py;

    auto sub_ds = create(impl_->filepath + "_subset.tif",
                         x_size, y_size, band_count(),
                         "GTiff", 6, sub_gt, projection());

    for (int b = 1; b <= band_count(); ++b) {
        sub_ds->write_band(b, bands[b - 1]);
    }

    return sub_ds;
}

std::string RasterDataset::driver_name() const {
    return impl_->meta.driver_name;
}

} // namespace glacierkz
