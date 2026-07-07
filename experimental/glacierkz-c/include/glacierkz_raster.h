#ifndef GLACIERKZ_RASTER_H
#define GLACIERKZ_RASTER_H

#include <stdint.h>
#include <stddef.h>
#include "glacierkz_tiff.h"

typedef enum {
    GZ_DTYPE_UINT8  = 0,
    GZ_DTYPE_UINT16 = 1,
    GZ_DTYPE_INT32  = 2,
    GZ_DTYPE_FLOAT32 = 3,
    GZ_DTYPE_FLOAT64 = 4
} gz_dtype_t;

typedef struct {
    gz_dtype_t type;
    size_t     size;
    double     nodata;
    int        has_nodata;
} gz_band_info_t;

typedef struct {
    void       *data;
    gz_dtype_t  dtype;
    size_t      width;
    size_t      height;
    size_t      bands;
    size_t      stride;
    size_t      total_size;
    double      nodata;
    int         has_nodata;
} gz_raster_t;

gz_status_t gz_raster_alloc(gz_raster_t *raster, size_t width, size_t height,
                            size_t bands, gz_dtype_t dtype);
void        gz_raster_free(gz_raster_t *raster);
gz_status_t gz_raster_zero(gz_raster_t *raster);

gz_status_t gz_raster_read_from_tiff(gz_tiff_t *tiff, gz_raster_t *raster, size_t band_idx);
gz_status_t gz_raster_write_band(const gz_raster_t *raster, size_t band_idx, const void *data);
void       *gz_raster_get_band(gz_raster_t *raster, size_t band_idx);
const void *gz_raster_get_band_const(const gz_raster_t *raster, size_t band_idx);
void       *gz_raster_get_pixel(gz_raster_t *raster, size_t x, size_t y, size_t band);
const void *gz_raster_get_pixel_const(const gz_raster_t *raster, size_t x, size_t y, size_t band);

void  gz_raster_set_nodata(gz_raster_t *raster, double nodata);
int   gz_raster_is_nodata(const gz_raster_t *raster, size_t x, size_t y, size_t band);
size_t gz_raster_pixel_count(const gz_raster_t *raster);
size_t gz_raster_band_size(const gz_raster_t *raster);

gz_status_t gz_raster_promote(gz_raster_t *src, gz_raster_t *dst, gz_dtype_t target);
gz_status_t gz_raster_mask_nodata(gz_raster_t *raster, uint8_t *mask);

size_t gz_dtype_size(gz_dtype_t dtype);
const char *gz_dtype_name(gz_dtype_t dtype);

#endif
