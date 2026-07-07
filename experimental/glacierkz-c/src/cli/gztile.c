#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "glacierkz_tiff.h"
#include "glacierkz_raster.h"
#include "glacierkz_tile.h"
#include "glacierkz_args.h"

static void print_usage(const char *prog) {
    fprintf(stderr, "Usage: %s [options] <file.tif> <col> <row>\n", prog);
    fprintf(stderr, "  -t, --tile-size <n>   Tile size (default: 512)\n");
    fprintf(stderr, "  -b, --band <n>        Band index (default: 0)\n");
    fprintf(stderr, "  -O, --overlap <n>     Tile overlap in pixels (default: 0)\n");
    fprintf(stderr, "  -o, --output <file>   Output file (default: stdout)\n");
    fprintf(stderr, "  -f, --format <f>      Output format: raw, float32\n");
    fprintf(stderr, "  -h, --help            Show this help\n");
}

int main(int argc, char **argv) {
    gz_arg_def_t defs[] = {
        { "-t", "--tile-size", "Tile size", GZ_ARG_INT, 0, 0, NULL, 0, 0.0 },
        { "-b", "--band", "Band index", GZ_ARG_INT, 0, 0, NULL, 0, 0.0 },
        { "-O", "--overlap", "Overlap", GZ_ARG_INT, 0, 0, NULL, 0, 0.0 },
        { "-o", "--output", "Output file", GZ_ARG_STRING, 0, 0, NULL, 0, 0.0 },
        { "-f", "--format", "Output format", GZ_ARG_STRING, 0, 0, NULL, 0, 0.0 },
        { "-h", "--help", "Show help", GZ_ARG_FLAG, 0, 0, NULL, 0, 0.0 },
    };

    gz_args_t args;
    gz_args_init(&args, defs, 6);

    if (gz_args_parse(&args, argc, argv) != 0) {
        gz_args_print_help(&args);
        gz_args_free(&args);
        return 1;
    }

    if (gz_args_found(&args, "--help")) {
        print_usage(argv[0]);
        gz_args_free(&args);
        return 0;
    }

    size_t npos = gz_args_positional_count(&args);
    if (npos < 3) {
        fprintf(stderr, "Error: need file, col, row\n");
        print_usage(argv[0]);
        gz_args_free(&args);
        return 1;
    }

    const char *path = gz_args_positional(&args, 0);
    int col = atoi(gz_args_positional(&args, 1));
    int row = atoi(gz_args_positional(&args, 2));
    int tile_size = gz_args_get_int(&args, "--tile-size", 512);
    int band = gz_args_get_int(&args, "--band", 0);
    int overlap = gz_args_get_int(&args, "--overlap", 0);
    const char *outpath = gz_args_get_string(&args, "--output", NULL);
    const char *fmt = gz_args_get_string(&args, "--format", "raw");

    if (tile_size <= 0 || tile_size > 8192) {
        fprintf(stderr, "Error: invalid tile size %d\n", tile_size);
        gz_args_free(&args);
        return 1;
    }

    if (overlap < 0 || (size_t)overlap >= (size_t)tile_size / 2) {
        fprintf(stderr, "Error: invalid overlap %d (max %d)\n", overlap, tile_size / 2 - 1);
        gz_args_free(&args);
        return 1;
    }

    gz_tiff_t tiff;
    gz_status_t st = gz_tiff_open(&tiff, path);
    if (st != GZ_OK) {
        fprintf(stderr, "Error: failed to open TIFF: %s (code %d)\n", path, st);
        gz_args_free(&args);
        return 1;
    }

    if (tiff.ifd_count == 0) {
        fprintf(stderr, "Error: no IFDs found\n");
        gz_tiff_close(&tiff);
        gz_args_free(&args);
        return 1;
    }

    const gz_ifd_t *ifd = &tiff.ifds[0];
    uint32_t width = gz_tiff_get_uint(ifd, 256, 0);
    uint32_t height = gz_tiff_get_uint(ifd, 257, 0);
    uint16_t bps = gz_tiff_get_ushort(ifd, 258, 8);
    uint16_t spp = gz_tiff_get_ushort(ifd, 277, 1);

    if (width == 0 || height == 0) {
        fprintf(stderr, "Error: invalid image dimensions %ux%u\n", width, height);
        gz_tiff_close(&tiff);
        gz_args_free(&args);
        return 1;
    }

    if ((size_t)band >= spp) {
        fprintf(stderr, "Error: band %d out of range (spp=%u)\n", band, spp);
        gz_tiff_close(&tiff);
        gz_args_free(&args);
        return 1;
    }

    gz_raster_t raster;
    memset(&raster, 0, sizeof(raster));

    st = gz_raster_alloc(&raster, width, height, spp,
                         bps <= 8 ? GZ_DTYPE_UINT8 :
                         bps <= 16 ? GZ_DTYPE_UINT16 :
                         bps == 32 ? GZ_DTYPE_INT32 : GZ_DTYPE_FLOAT32);
    if (st != GZ_OK) {
        fprintf(stderr, "Error: failed to allocate raster\n");
        gz_tiff_close(&tiff);
        gz_args_free(&args);
        return 1;
    }

    st = gz_raster_read_from_tiff(&tiff, &raster, 0);
    if (st != GZ_OK) {
        fprintf(stderr, "Error: failed to read raster data (code %d)\n", st);
        gz_raster_free(&raster);
        gz_tiff_close(&tiff);
        gz_args_free(&args);
        return 1;
    }

    gz_tile_t tile;
    memset(&tile, 0, sizeof(tile));

    st = gz_tile_extract(&raster, (size_t)band, (size_t)col, (size_t)row,
                         (size_t)tile_size, (size_t)tile_size, (size_t)overlap, &tile);
    if (st != GZ_OK) {
        fprintf(stderr, "Error: failed to extract tile at (%d,%d) (code %d)\n", col, row, st);
        gz_raster_free(&raster);
        gz_tiff_close(&tiff);
        gz_args_free(&args);
        return 1;
    }

    printf("Tile at (%d,%d): %zux%zu pixels, band=%zu\n",
           col, row, tile.width, tile.height, tile.band);

    FILE *out = stdout;
    if (outpath) {
        out = fopen(outpath, "wb");
        if (!out) {
            fprintf(stderr, "Error: cannot open output file %s\n", outpath);
            gz_tile_free(&tile);
            gz_raster_free(&raster);
            gz_tiff_close(&tiff);
            gz_args_free(&args);
            return 1;
        }
    }

    gz_dtype_t tile_dtype = raster.dtype;
    size_t ds = gz_dtype_size(tile_dtype);
    size_t pixel_count = tile.width * tile.height;

    if (strcmp(fmt, "float32") == 0 && tile_dtype != GZ_DTYPE_FLOAT32) {
        gz_raster_t single_band;
        memset(&single_band, 0, sizeof(single_band));
        st = gz_raster_alloc(&single_band, tile.width, tile.height, 1, tile_dtype);
        if (st == GZ_OK) {
            memcpy(single_band.data, tile.data, pixel_count * ds);
            gz_raster_t promoted;
            memset(&promoted, 0, sizeof(promoted));
            st = gz_raster_promote(&single_band, &promoted, GZ_DTYPE_FLOAT32);
            if (st == GZ_OK) {
                fwrite(promoted.data, sizeof(float), pixel_count, out);
                gz_raster_free(&promoted);
            } else {
                fwrite(tile.data, ds, pixel_count, out);
            }
            gz_raster_free(&single_band);
        } else {
            fwrite(tile.data, ds, pixel_count, out);
        }
    } else {
        fwrite(tile.data, ds, pixel_count, out);
    }

    if (outpath) fclose(out);

    gz_tile_free(&tile);
    gz_raster_free(&raster);
    gz_tiff_close(&tiff);
    gz_args_free(&args);
    return 0;
}
