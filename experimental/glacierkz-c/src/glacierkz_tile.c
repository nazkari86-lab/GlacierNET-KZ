#include "glacierkz_tile.h"
#include "glacierkz_memory.h"
#include "glacierkz_log.h"
#include <stdlib.h>
#include <string.h>

gz_status_t gz_tiler_init(gz_tiler_t *tiler, size_t raster_width,
                          size_t raster_height, size_t tile_width,
                          size_t tile_height, size_t overlap) {
    if (!tiler || tile_width == 0 || tile_height == 0) return GZ_ERR_PARAM;
    if (tile_width > raster_width || tile_height > raster_height) return GZ_ERR_PARAM;

    tiler->tile_width = tile_width;
    tiler->tile_height = tile_height;
    tiler->overlap = overlap;

    tiler->tiles_x = (raster_width + tile_width - 1) / tile_width;
    tiler->tiles_y = (raster_height + tile_height - 1) / tile_height;
    tiler->tile_count = tiler->tiles_x * tiler->tiles_y;

    tiler->tiles = calloc(tiler->tile_count, sizeof(gz_tile_t));
    if (!tiler->tiles) return GZ_ERR_NOMEM;

    size_t idx = 0;
    for (size_t ty = 0; ty < tiler->tiles_y; ty++) {
        for (size_t tx = 0; tx < tiler->tiles_x; tx++) {
            gz_tile_t *t = &tiler->tiles[idx];
            t->x = tx * tile_width;
            t->y = ty * tile_height;
            t->width = tile_width;
            t->height = tile_height;

            if (t->x + t->width > raster_width) {
                t->width = raster_width - t->x;
            }
            if (t->y + t->height > raster_height) {
                t->height = raster_height - t->y;
            }
            t->data = NULL;
            t->band = 0;
            idx++;
        }
    }

    GZ_DEBUG("Tiler initialized: %zux%zu tiles (%zu total), overlap=%zu",
             tiler->tiles_x, tiler->tiles_y, tiler->tile_count, overlap);
    return GZ_OK;
}

void gz_tiler_free(gz_tiler_t *tiler) {
    if (!tiler) return;
    for (size_t i = 0; i < tiler->tile_count; i++) {
        free(tiler->tiles[i].data);
    }
    free(tiler->tiles);
    tiler->tiles = NULL;
    tiler->tile_count = 0;
}

static gz_status_t extract_tile_data(const gz_raster_t *raster, size_t band,
                                     size_t x0, size_t y0, size_t w, size_t h,
                                     size_t overlap, gz_tile_t *tile) {
    size_t ds = gz_dtype_size(raster->dtype);
    size_t pitch = raster->width * ds;
    size_t tile_pitch = w * ds;

    size_t ox = (x0 >= overlap) ? overlap : x0;
    size_t oy = (y0 >= overlap) ? overlap : y0;

    size_t src_x0 = x0 - ox;
    size_t src_y0 = y0 - oy;
    size_t full_w = w + ox;
    size_t full_h = h + oy;

    size_t rem_x = raster->width - (x0 + w);
    size_t rem_y = raster->height - (y0 + h);
    size_t right_pad = (rem_x < overlap) ? (overlap - rem_x) : 0;
    size_t bottom_pad = (rem_y < overlap) ? (overlap - rem_y) : 0;

    full_w += right_pad;
    full_h += bottom_pad;

    if (src_x0 + full_w > raster->width) full_w = raster->width - src_x0;
    if (src_y0 + full_h > raster->height) full_h = raster->height - src_y0;

    size_t tile_size = full_w * full_h * ds;
    tile->data = malloc(tile_size);
    if (!tile->data) return GZ_ERR_NOMEM;

    tile->x = x0;
    tile->y = y0;
    tile->width = full_w;
    tile->height = full_h;
    tile->band = band;

    const uint8_t *src_band = (const uint8_t *)raster->data +
                              band * raster->width * raster->height * ds;

    for (size_t row = 0; row < full_h; row++) {
        size_t sy = src_y0 + row;
        if (sy >= raster->height) break;
        memcpy((uint8_t *)tile->data + row * full_w * ds,
               src_band + sy * pitch + src_x0 * ds,
               full_w * ds);
    }

    return GZ_OK;
}

gz_status_t gz_tiler_extract_all(gz_tiler_t *tiler, const gz_raster_t *raster, size_t band) {
    if (!tiler || !raster || band >= raster->bands) return GZ_ERR_PARAM;

    for (size_t i = 0; i < tiler->tile_count; i++) {
        gz_tile_t *t = &tiler->tiles[i];
        if (t->data) free(t->data);
        t->data = NULL;

        gz_status_t st = extract_tile_data(raster, band, t->x, t->y,
                                           tiler->tile_width, tiler->tile_height,
                                           tiler->overlap, t);
        if (st != GZ_OK) return st;
        t->band = band;
    }
    return GZ_OK;
}

gz_status_t gz_tiler_extract_tile(const gz_tiler_t *tiler, const gz_raster_t *raster,
                                  size_t tile_idx, size_t band, gz_tile_t *tile) {
    if (!tiler || !raster || !tile) return GZ_ERR_PARAM;
    if (tile_idx >= tiler->tile_count) return GZ_ERR_PARAM;
    if (band >= raster->bands) return GZ_ERR_PARAM;

    const gz_tile_t *src = &tiler->tiles[tile_idx];
    return extract_tile_data(raster, band, src->x, src->y,
                             tiler->tile_width, tiler->tile_height,
                             tiler->overlap, tile);
}

static void paste_tile(gz_raster_t *raster, size_t band,
                       const gz_tile_t *tile, size_t tile_w, size_t tile_h,
                       size_t overlap) {
    size_t ds = gz_dtype_size(raster->dtype);
    size_t pitch = raster->width * ds;
    const uint8_t *src = (const uint8_t *)tile->data;
    uint8_t *dst_band = (uint8_t *)raster->data +
                        band * raster->width * raster->height * ds;

    size_t ox = (tile->x >= overlap) ? overlap : tile->x;
    size_t oy = (tile->y >= overlap) ? overlap : tile->y;
    size_t inner_x = tile->x - ox;
    size_t inner_y = tile->y - oy;
    size_t inner_w = tile->width - ox;
    size_t inner_h = tile->height - oy;

    size_t rem_x = raster->width - (inner_x + inner_w);
    size_t rem_y = raster->height - (inner_y + inner_h);
    if (rem_x < overlap) inner_w += rem_x;
    if (rem_y < overlap) inner_h += rem_y;

    if (inner_x + inner_w > raster->width) inner_w = raster->width - inner_x;
    if (inner_y + inner_h > raster->height) inner_h = raster->height - inner_y;

    for (size_t row = 0; row < inner_h; row++) {
        size_t dy = inner_y + row;
        size_t sy = oy + row;
        if (dy >= raster->height || sy >= tile->height) break;
        memcpy(dst_band + dy * pitch + inner_x * ds,
               src + sy * tile->width * ds + ox * ds,
               inner_w * ds);
    }
}

gz_status_t gz_tiler_merge(const gz_tiler_t *tiler, gz_raster_t *raster, size_t band) {
    if (!tiler || !raster || band >= raster->bands) return GZ_ERR_PARAM;

    gz_raster_zero(raster);

    for (size_t i = 0; i < tiler->tile_count; i++) {
        const gz_tile_t *t = &tiler->tiles[i];
        if (!t->data) continue;
        paste_tile(raster, band, t, tiler->tile_width, tiler->tile_height, tiler->overlap);
    }
    return GZ_OK;
}

gz_status_t gz_tile_extract(const gz_raster_t *raster, size_t band,
                            size_t x, size_t y, size_t w, size_t h,
                            size_t overlap, gz_tile_t *tile) {
    if (!raster || !tile) return GZ_ERR_PARAM;
    if (band >= raster->bands) return GZ_ERR_PARAM;
    if (x + w > raster->width || y + h > raster->height) return GZ_ERR_PARAM;

    return extract_tile_data(raster, band, x, y, w, h, overlap, tile);
}

void gz_tile_free(gz_tile_t *tile) {
    if (!tile) return;
    free(tile->data);
    tile->data = NULL;
}

gz_status_t gz_tile_overlap_merge(const gz_tile_t *tiles, size_t count,
                                  gz_raster_t *raster, size_t band,
                                  size_t tile_width, size_t tile_height,
                                  size_t overlap) {
    if (!tiles || !raster || band >= raster->bands) return GZ_ERR_PARAM;
    if (count == 0) return GZ_OK;

    gz_raster_zero(raster);

    for (size_t i = 0; i < count; i++) {
        if (!tiles[i].data) continue;
        paste_tile(raster, band, &tiles[i], tile_width, tile_height, overlap);
    }
    return GZ_OK;
}
