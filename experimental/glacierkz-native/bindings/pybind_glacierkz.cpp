#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "glacierkz/raster_io.hpp"
#include "glacierkz/spectral_indices.hpp"
#include "glacierkz/sliding_window.hpp"
#include "glacierkz/simd_ops.hpp"
#include "glacierkz/tile_cache.hpp"
#include "glacierkz/thread_pool.hpp"
#include "glacierkz/statistics.hpp"
#include "glacierkz/resampling.hpp"
#include "glacierkz/band_math.hpp"

namespace py = pybind11;
using namespace glacierkz;

PYBIND11_MODULE(pyglacierkz, m) {
    m.doc() = "GlacierNET-KZ native library for glacier monitoring";

    py::enum_<SIMDBackend>(m, "SIMDBackend")
        .value("Scalar", SIMDBackend::Scalar)
        .value("SSE2", SIMDBackend::SSE2)
        .value("AVX2", SIMDBackend::AVX2)
        .value("Auto", SIMDBackend::Auto)
        .export_values();

    py::class_<SIMDArray>(m, "SIMDArray")
        .def(py::init<size_t>())
        .def(py::init<const std::vector<float>&>())
        .def_property_readonly("size", &SIMDArray::size)
        .def("data", [](SIMDArray& arr) {
            return py::array_t<float>(
                {arr.size()},
                {sizeof(float)},
                arr.data(),
                py::cast(arr));
        });

    m.def("detect_best_backend", &detect_best_backend);
    m.def("vector_add", [](const std::vector<float>& a, const std::vector<float>& b,
                           SIMDBackend backend) {
        if (a.size() != b.size()) throw std::runtime_error("Size mismatch");
        std::vector<float> result(a.size());
        vector_add(a.data(), b.data(), result.data(), a.size(), backend);
        return result;
    }, py::arg("a"), py::arg("b"), py::arg("backend") = SIMDBackend::Auto);

    m.def("vector_subtract", [](const std::vector<float>& a, const std::vector<float>& b,
                                SIMDBackend backend) {
        if (a.size() != b.size()) throw std::runtime_error("Size mismatch");
        std::vector<float> result(a.size());
        vector_subtract(a.data(), b.data(), result.data(), a.size(), backend);
        return result;
    }, py::arg("a"), py::arg("b"), py::arg("backend") = SIMDBackend::Auto);

    m.def("vector_multiply", [](const std::vector<float>& a, const std::vector<float>& b,
                                SIMDBackend backend) {
        if (a.size() != b.size()) throw std::runtime_error("Size mismatch");
        std::vector<float> result(a.size());
        vector_multiply(a.data(), b.data(), result.data(), a.size(), backend);
        return result;
    }, py::arg("a"), py::arg("b"), py::arg("backend") = SIMDBackend::Auto);

    m.def("vector_normalize", [](const std::vector<float>& a, float min_val, float max_val,
                                 SIMDBackend backend) {
        std::vector<float> result(a.size());
        vector_normalize(a.data(), result.data(), a.size(), min_val, max_val, backend);
        return result;
    }, py::arg("a"), py::arg("min_val") = 0.0f, py::arg("max_val") = 1.0f,
       py::arg("backend") = SIMDBackend::Auto);

    m.def("vector_sum", [](const std::vector<float>& a, SIMDBackend backend) {
        return vector_sum(a.data(), a.size(), backend);
    }, py::arg("a"), py::arg("backend") = SIMDBackend::Auto);

    m.def("vector_mean", [](const std::vector<float>& a, SIMDBackend backend) {
        return vector_mean(a.data(), a.size(), backend);
    }, py::arg("a"), py::arg("backend") = SIMDBackend::Auto);

    py::class_<TileKey>(m, "TileKey")
        .def(py::init<int, int, int>(), py::arg("level"), py::arg("col"), py::arg("row"))
        .def_readwrite("level", &TileKey::level)
        .def_readwrite("col", &TileKey::col)
        .def_readwrite("row", &TileKey::row)
        .def("__eq__", &TileKey::operator==)
        .def("__hash__", [](const TileKey& k) {
            return std::hash<int>()(k.level) ^ std::hash<int>()(k.col) ^ std::hash<int>()(k.row);
        });

    py::class_<TileData>(m, "TileData")
        .def(py::init<>())
        .def_readwrite("data", &TileData::data)
        .def_readwrite("width", &TileData::width)
        .def_readwrite("height", &TileData::height)
        .def_readwrite("bands", &TileData::bands)
        .def("memory_bytes", &TileData::memory_bytes);

    py::class_<LRUCache>(m, "LRUCache")
        .def(py::init<size_t>(), py::arg("max_memory_bytes"))
        .def("put", &LRUCache::put)
        .def("get", [](LRUCache& c, const TileKey& k) {
            auto v = c.get(k);
            return v.has_value() ? py::cast(*v) : py::none();
        })
        .def("contains", &LRUCache::contains)
        .def("remove", &LRUCache::remove)
        .def("clear", &LRUCache::clear)
        .def("current_memory", &LRUCache::current_memory)
        .def("max_memory", &LRUCache::max_memory)
        .def("size", &LRUCache::size)
        .def("hit_count", &LRUCache::hit_count)
        .def("miss_count", &LRUCache::miss_count)
        .def("reset_stats", &LRUCache::reset_stats)
        .def("keys", &LRUCache::keys);

    py::class_<AsyncTileCache>(m, "AsyncTileCache")
        .def(py::init<size_t, size_t>(),
             py::arg("max_memory_bytes"),
             py::arg("num_loader_threads") = 2)
        .def("get", [](AsyncTileCache& c, const TileKey& k) {
            auto v = c.get(k);
            return v.has_value() ? py::cast(*v) : py::none();
        })
        .def("cancel_pending", &AsyncTileCache::cancel_pending)
        .def("pending_count", &AsyncTileCache::pending_count)
        .def("loaded_count", &AsyncTileCache::loaded_count);

    py::class_<StreamingStatistics>(m, "StreamingStatistics")
        .def(py::init<>())
        .def("update", &StreamingStatistics::update)
        .def_property_readonly("mean", &StreamingStatistics::mean)
        .def_property_readonly("variance", &StreamingStatistics::variance)
        .def_property_readonly("stddev", &StreamingStatistics::stddev)
        .def_property_readonly("min", &StreamingStatistics::min)
        .def_property_readonly("max", &StreamingStatistics::max)
        .def_property_readonly("count", &StreamingStatistics::count)
        .def("reset", &StreamingStatistics::reset);

    py::class_<BasicStats>(m, "BasicStats")
        .def_readwrite("mean", &BasicStats::mean)
        .def_readwrite("stddev", &BasicStats::stddev)
        .def_readwrite("min_val", &BasicStats::min_val)
        .def_readwrite("max_val", &BasicStats::max_val)
        .def_readwrite("valid_count", &BasicStats::valid_count);

    m.def("compute_stats", [](const std::vector<float>& data) {
        if (data.empty()) throw std::runtime_error("Empty data");
        return compute_stats(data.data(), data.size());
    });

    m.def("compute_percentile", [](const std::vector<float>& data, float p) {
        return compute_percentile(data.data(), data.size(), p);
    });

    m.def("compute_median", [](const std::vector<float>& data) {
        return compute_median(data.data(), data.size());
    });

    m.def("z_score_normalize", [](const std::vector<float>& data) {
        return z_score_normalize(data.data(), data.size());
    });

    m.def("compute_rms", [](const std::vector<float>& data) {
        return compute_rms(data.data(), data.size());
    });

    m.def("compute_iqr", [](const std::vector<float>& data) {
        return compute_iqr(data.data(), data.size());
    });

    py::class_<Histogram>(m, "Histogram")
        .def(py::init<size_t, float, float>(),
             py::arg("num_bins"), py::arg("min_val"), py::arg("max_val"))
        .def("update", &Histogram::update)
        .def("counts", &Histogram::counts)
        .def("bin_count", &Histogram::bin_count)
        .def("bin_width", &Histogram::bin_width)
        .def("total_count", &Histogram::total_count)
        .def("reset", &Histogram::reset);

    m.def("nearest_neighbor_resample", [](const std::vector<float>& data,
                                           int src_w, int src_h,
                                           int dst_w, int dst_h) {
        return Resampler::resample_bilinear(data.data(), src_w, src_h, dst_w, dst_h);
    });

    m.def("generate_thumbnail", [](const std::vector<float>& data,
                                    int width, int height,
                                    int thumb_w, int thumb_h,
                                    const std::string& method) {
        if (method == "nearest") {
            return ThumbnailGenerator::generate_nearest(
                data.data(), width, height, thumb_w, thumb_h);
        } else if (method == "bilinear") {
            return ThumbnailGenerator::generate_bilinear(
                data.data(), width, height, thumb_w, thumb_h);
        } else if (method == "average") {
            return ThumbnailGenerator::generate_average(
                data.data(), width, height, thumb_w, thumb_h);
        }
        throw std::invalid_argument("Unknown method: " + method);
    }, py::arg("data"), py::arg("width"), py::arg("height"),
       py::arg("thumb_width"), py::arg("thumb_height"),
       py::arg("method") = "bilinear");

    m.def("build_pyramid", [](const std::vector<float>& data,
                               int width, int height, int num_levels) {
        return PyramidBuilder::build_gaussian_pyramid(
            data.data(), width, height, num_levels);
    });

    py::class_<BandMathEngine>(m, "BandMathEngine")
        .def(py::init([](const std::unordered_map<std::string, std::vector<float>>& bands) {
            std::unordered_map<std::string, const float*> band_ptrs;
            for (auto& [name, vec] : bands) {
                band_ptrs[name] = vec.data();
            }
            size_t px = bands.empty() ? 0 : bands.begin()->second.size();
            return BandMathEngine(band_ptrs, px);
        }), py::arg("bands"))
        .def("compute", [](BandMathEngine& eng, const std::string& expr,
                           const std::unordered_map<std::string, std::vector<float>>& extra) {
            return eng.compute_custom(expr, extra);
        }, py::arg("expression"), py::arg("extra_variables") =
            std::unordered_map<std::string, std::vector<float>>{})
        .def("list_bands", &BandMathEngine::list_bands);

    m.def("ndsi", [](const std::vector<float>& green, const std::vector<float>& swir) {
        std::vector<float> result(green.size());
        for (size_t i = 0; i < green.size(); ++i) {
            float denom = green[i] + swir[i];
            result[i] = (std::abs(denom) > 1e-10f) ? (green[i] - swir[i]) / denom : 0.0f;
        }
        return result;
    });

    m.def("ndwi", [](const std::vector<float>& green, const std::vector<float>& nir) {
        std::vector<float> result(green.size());
        for (size_t i = 0; i < green.size(); ++i) {
            float denom = green[i] + nir[i];
            result[i] = (std::abs(denom) > 1e-10f) ? (green[i] - nir[i]) / denom : 0.0f;
        }
        return result;
    });

    m.def("ndvi", [](const std::vector<float>& nir, const std::vector<float>& red) {
        std::vector<float> result(nir.size());
        for (size_t i = 0; i < nir.size(); ++i) {
            float denom = nir[i] + red[i];
            result[i] = (std::abs(denom) > 1e-10f) ? (nir[i] - red[i]) / denom : 0.0f;
        }
        return result;
    });

    m.def("thread_pool_status", []() {
        return "glacierkz native module loaded";
    });
}
