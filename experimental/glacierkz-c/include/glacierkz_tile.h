#ifndef GLACIERKZ_TILE_H
#define GLACIERKZ_TILE_H

#include <stddef.h>
#include "glacierkz_raster.h"
#include "glacierkz_tiff.h"

typedef struct {
    size_t x;
    size_t y;
    size_t width;
    size_t height;
    size_t band;
    void  *data;
} gz_tile_t;

typedef struct {
    size_t tile_width;
    size_t tile_height;
    size_t overlap;
    size_t tiles_x;
    size_t tiles_y;
    gz_tile_t *tiles;
    size_t     tile_count;
} gz_tiler_t;

gz_status_t gz_tiler_init(gz_tiler_t *tiler, size_t raster_width,
                          size_t raster_height, size_t tile_width,
                          size_t tile_height, size_t overlap);
void        gz_tiler_free(gz_tiler_t *tiler);
gz_status_t gz_tiler_extract_all(gz_tiler_t *tiler, const gz_raster_t *raster, size_t band);
gz_status_t gz_tiler_extract_tile(const gz_tiler_t *tiler, const gz_raster_t *raster,
                                  size_t tile_idx, size_t band, gz_tile_t *tile);
gz_status_t gz_tiler_merge(const gz_tiler_t *tiler, gz_raster_t *raster, size_t band);

gz_status_t gz_tile_extract(const gz_raster_t *raster, size_t band,
                            size_t x, size_t y, size_t w, size_t h,
                            size_t overlap, gz_tile_t *tile);
void        gz_tile_free(gz_tile_t *tile);
gz_status_t gz_tile_overlap_merge(const gz_tile_t *tiles, size_t count,
                                  gz_raster_t *raster, size_t band,
                                  size_t tile_width, size_t tile_height,
                                  size_t overlap);

#endif
