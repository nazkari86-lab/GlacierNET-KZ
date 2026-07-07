#include "glacierkz_raster.h"
#include "glacierkz_endian.h"
#include "glacierkz_log.h"
#include <stdlib.h>
#include <string.h>

size_t gz_dtype_size(gz_dtype_t dtype) {
    switch (dtype) {
        case GZ_DTYPE_UINT8:   return 1;
        case GZ_DTYPE_UINT16:  return 2;
        case GZ_DTYPE_INT32:   return 4;
        case GZ_DTYPE_FLOAT32: return 4;
        case GZ_DTYPE_FLOAT64: return 8;
    }
    return 0;
}

const char *gz_dtype_name(gz_dtype_t dtype) {
    switch (dtype) {
        case GZ_DTYPE_UINT8:   return "uint8";
        case GZ_DTYPE_UINT16:  return "uint16";
        case GZ_DTYPE_INT32:   return "int32";
        case GZ_DTYPE_FLOAT32: return "float32";
        case GZ_DTYPE_FLOAT64: return "float64";
    }
    return "unknown";
}

gz_status_t gz_raster_alloc(gz_raster_t *raster, size_t width, size_t height,
                            size_t bands, gz_dtype_t dtype) {
    if (!raster || width == 0 || height == 0 || bands == 0) return GZ_ERR_PARAM;

    size_t ds = gz_dtype_size(dtype);
    if (ds == 0) return GZ_ERR_PARAM;

    size_t total = width * height * bands * ds;
    raster->data = malloc(total);
    if (!raster->data) return GZ_ERR_NOMEM;

    raster->dtype = dtype;
    raster->width = width;
    raster->height = height;
    raster->bands = bands;
    raster->stride = width * ds;
    raster->total_size = total;
    raster->nodata = 0.0;
    raster->has_nodata = 0;

    memset(raster->data, 0, total);
    return GZ_OK;
}

void gz_raster_free(gz_raster_t *raster) {
    if (!raster) return;
    free(raster->data);
    raster->data = NULL;
    raster->width = 0;
    raster->height = 0;
    raster->bands = 0;
    raster->total_size = 0;
}

gz_status_t gz_raster_zero(gz_raster_t *raster) {
    if (!raster || !raster->data) return GZ_ERR_PARAM;
    memset(raster->data, 0, raster->total_size);
    return GZ_OK;
}

static gz_dtype_t tiff_tag_to_dtype(uint16_t bps, uint16_t sample_fmt) {
    if (bps == 8) return GZ_DTYPE_UINT8;
    if (bps == 16) return GZ_DTYPE_UINT16;
    if (bps == 32 && sample_fmt == 3) return GZ_DTYPE_FLOAT32;
    if (bps == 32) return GZ_DTYPE_INT32;
    if (bps == 64) return GZ_DTYPE_FLOAT64;
    return GZ_DTYPE_UINT8;
}

gz_status_t gz_raster_read_from_tiff(gz_tiff_t *tiff, gz_raster_t *raster, size_t band_idx) {
    if (!tiff || !raster || tiff->ifd_count == 0) return GZ_ERR_PARAM;
    if (band_idx >= raster->bands) return GZ_ERR_PARAM;

    const gz_ifd_t *ifd = &tiff->ifds[0];

    uint32_t width = gz_tiff_get_uint(ifd, 256, 0);
    uint32_t height = gz_tiff_get_uint(ifd, 257, 0);
    uint16_t bps = gz_tiff_get_ushort(ifd, 258, 8);
    uint16_t sample_fmt = gz_tiff_get_ushort(ifd, 339, 1);

    if (width == 0 || height == 0) return GZ_ERR_FORMAT;

    gz_dtype_t dtype = tiff_tag_to_dtype(bps, sample_fmt);
    size_t ds = gz_dtype_size(dtype);

    if (!raster->data) {
        raster->dtype = dtype;
        raster->width = width;
        raster->height = height;
        raster->bands = 1;
        raster->stride = width * ds;
        raster->total_size = width * height * ds;
        raster->data = malloc(raster->total_size);
        if (!raster->data) return GZ_ERR_NOMEM;
        memset(raster->data, 0, raster->total_size);
    }

    uint32_t *strip_offsets = NULL;
    uint32_t strip_count = 0;
    gz_status_t st = gz_tiff_read_strip_offsets(ifd, &strip_offsets, &strip_count);
    if (st != GZ_OK) return st;

    uint32_t *strip_sizes = NULL;
    uint32_t sz_count = 0;
    st = gz_tiff_read_strip_byte_counts(ifd, &strip_sizes, &sz_count);
    if (st != GZ_OK) {
        free(strip_offsets);
        return st;
    }

    int native_le = (gz_endian_detect() == GZ_ENDIAN_LITTLE);
    int need_swap = (tiff->byte_order == GZ_ENDIAN_BIG && native_le) ||
                    (tiff->byte_order == GZ_ENDIAN_LITTLE && !native_le);

    uint16_t rows_per_strip_val = gz_tiff_get_ushort(ifd, 278, (uint16_t)height);
    uint32_t rows_per_strip = rows_per_strip_val;

    uint8_t *row_buf = malloc(width * ds);
    if (!row_buf) {
        free(strip_offsets);
        free(strip_sizes);
        return GZ_ERR_NOMEM;
    }

    uint8_t *dst = (uint8_t *)raster->data + band_idx * (size_t)width * (size_t)height * ds;

    for (uint32_t strip = 0; strip < strip_count && strip < height / rows_per_strip + 1; strip++) {
        size_t y_start = strip * rows_per_strip;
        if (y_start >= height) break;

        size_t y_end = y_start + rows_per_strip;
        if (y_end > height) y_end = height;

        if (fseek(tiff->fp, (long)strip_offsets[strip], SEEK_SET) != 0) {
            free(row_buf);
            free(strip_offsets);
            free(strip_sizes);
            return GZ_ERR_IO;
        }

        for (size_t y = y_start; y < y_end; y++) {
            if (fread(row_buf, ds, width, tiff->fp) != width) {
                free(row_buf);
                free(strip_offsets);
                free(strip_sizes);
                return GZ_ERR_IO;
            }

            if (need_swap) {
                if (ds == 2) gz_endian_swap_array16((uint16_t *)row_buf, width);
                else if (ds == 4) gz_endian_swap_array32((uint32_t *)row_buf, width);
                else if (ds == 8) gz_endian_swap_array64((uint64_t *)row_buf, width);
            }

            memcpy(dst + y * width * ds, row_buf, width * ds);
        }
    }

    free(row_buf);
    free(strip_offsets);
    free(strip_sizes);
    return GZ_OK;
}

gz_status_t gz_raster_write_band(const gz_raster_t *raster, size_t band_idx, const void *data) {
    if (!raster || !data) return GZ_ERR_PARAM;
    if (band_idx >= raster->bands) return GZ_ERR_PARAM;

    size_t ds = gz_dtype_size(raster->dtype);
    size_t offset = band_idx * raster->width * raster->height * ds;
    memcpy((uint8_t *)raster->data + offset, data, raster->width * raster->height * ds);
    return GZ_OK;
}

void *gz_raster_get_band(gz_raster_t *raster, size_t band_idx) {
    if (!raster || !raster->data || band_idx >= raster->bands) return NULL;
    size_t ds = gz_dtype_size(raster->dtype);
    return (uint8_t *)raster->data + band_idx * raster->width * raster->height * ds;
}

const void *gz_raster_get_band_const(const gz_raster_t *raster, size_t band_idx) {
    return gz_raster_get_band((gz_raster_t *)raster, band_idx);
}

void *gz_raster_get_pixel(gz_raster_t *raster, size_t x, size_t y, size_t band) {
    if (!raster || !raster->data || band >= raster->bands) return NULL;
    if (x >= raster->width || y >= raster->height) return NULL;
    size_t ds = gz_dtype_size(raster->dtype);
    size_t offset = band * raster->width * raster->height * ds +
                    y * raster->width * ds + x * ds;
    return (uint8_t *)raster->data + offset;
}

const void *gz_raster_get_pixel_const(const gz_raster_t *raster, size_t x, size_t y, size_t band) {
    return gz_raster_get_pixel((gz_raster_t *)raster, x, y, band);
}

void gz_raster_set_nodata(gz_raster_t *raster, double nodata) {
    if (!raster) return;
    raster->nodata = nodata;
    raster->has_nodata = 1;
}

int gz_raster_is_nodata(const gz_raster_t *raster, size_t x, size_t y, size_t band) {
    if (!raster || !raster->has_nodata) return 0;
    const void *px = gz_raster_get_pixel_const(raster, x, y, band);
    if (!px) return 0;

    double val = 0;
    switch (raster->dtype) {
        case GZ_DTYPE_UINT8:   val = (double)*(uint8_t *)px; break;
        case GZ_DTYPE_UINT16:  val = (double)*(uint16_t *)px; break;
        case GZ_DTYPE_INT32:   val = (double)*(int32_t *)px; break;
        case GZ_DTYPE_FLOAT32: val = (double)*(float *)px; break;
        case GZ_DTYPE_FLOAT64: val = *(double *)px; break;
    }
    return (val == raster->nodata);
}

size_t gz_raster_pixel_count(const gz_raster_t *raster) {
    if (!raster) return 0;
    return raster->width * raster->height;
}

size_t gz_raster_band_size(const gz_raster_t *raster) {
    if (!raster) return 0;
    return raster->width * raster->height * gz_dtype_size(raster->dtype);
}

static double read_val(const void *ptr, gz_dtype_t dtype) {
    switch (dtype) {
        case GZ_DTYPE_UINT8:   return (double)*(uint8_t *)ptr;
        case GZ_DTYPE_UINT16:  return (double)*(uint16_t *)ptr;
        case GZ_DTYPE_INT32:   return (double)*(int32_t *)ptr;
        case GZ_DTYPE_FLOAT32: return (double)*(float *)ptr;
        case GZ_DTYPE_FLOAT64: return *(double *)ptr;
    }
    return 0;
}

static void write_val(void *ptr, gz_dtype_t dtype, double val) {
    switch (dtype) {
        case GZ_DTYPE_UINT8:   *(uint8_t *)ptr = (uint8_t)val; break;
        case GZ_DTYPE_UINT16:  *(uint16_t *)ptr = (uint16_t)val; break;
        case GZ_DTYPE_INT32:   *(int32_t *)ptr = (int32_t)val; break;
        case GZ_DTYPE_FLOAT32: *(float *)ptr = (float)val; break;
        case GZ_DTYPE_FLOAT64: *(double *)ptr = val; break;
    }
}

gz_status_t gz_raster_promote(gz_raster_t *src, gz_raster_t *dst, gz_dtype_t target) {
    if (!src || !src->data) return GZ_ERR_PARAM;

    gz_status_t st = gz_raster_alloc(dst, src->width, src->height, src->bands, target);
    if (st != GZ_OK) return st;

    size_t pixels = src->width * src->height;
    size_t ds_src = gz_dtype_size(src->dtype);

    for (size_t b = 0; b < src->bands; b++) {
        const uint8_t *src_band = (const uint8_t *)src->data + b * pixels * ds_src;
        uint8_t *dst_band = (uint8_t *)dst->data + b * pixels * gz_dtype_size(target);

        for (size_t i = 0; i < pixels; i++) {
            double val = read_val(src_band + i * ds_src, src->dtype);
            write_val(dst_band + i * gz_dtype_size(target), target, val);
        }
    }

    dst->nodata = src->nodata;
    dst->has_nodata = src->has_nodata;
    return GZ_OK;
}

gz_status_t gz_raster_mask_nodata(gz_raster_t *raster, uint8_t *mask) {
    if (!raster || !mask) return GZ_ERR_PARAM;
    if (!raster->has_nodata) {
        memset(mask, 0, raster->width * raster->height * raster->bands);
        return GZ_OK;
    }

    size_t pixels = raster->width * raster->height;
    size_t ds = gz_dtype_size(raster->dtype);

    for (size_t b = 0; b < raster->bands; b++) {
        const uint8_t *band = (const uint8_t *)raster->data + b * pixels * ds;
        for (size_t i = 0; i < pixels; i++) {
            mask[b * pixels + i] = gz_raster_is_nodata(raster, i % raster->width, i / raster->width, b) ? 1 : 0;
        }
    }
    return GZ_OK;
}
