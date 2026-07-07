#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "glacierkz_tiff.h"
#include "glacierkz_raster.h"
#include "glacierkz_args.h"

static void print_usage(const char *prog) {
    fprintf(stderr, "Usage: %s [options] <file.tif> [band]\n", prog);
    fprintf(stderr, "  -b, --band <n>    Band index (0-based)\n");
    fprintf(stderr, "  -f, --format <f>  Output format: raw, uint8, float32\n");
    fprintf(stderr, "  -h, --help        Show this help\n");
}

int main(int argc, char **argv) {
    gz_arg_def_t defs[] = {
        { "-b", "--band", "Band index", GZ_ARG_INT, 0, 0, NULL, 0, 0.0 },
        { "-f", "--format", "Output format", GZ_ARG_STRING, 0, 0, NULL, 0, 0.0 },
        { "-h", "--help", "Show help", GZ_ARG_FLAG, 0, 0, NULL, 0, 0.0 },
    };

    gz_args_t args;
    gz_args_init(&args, defs, 3);

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
    if (npos < 1) {
        fprintf(stderr, "Error: no input file specified\n");
        print_usage(argv[0]);
        gz_args_free(&args);
        return 1;
    }

    const char *path = gz_args_positional(&args, 0);
    int band = gz_args_get_int(&args, "--band", 0);

    if (npos >= 2) {
        band = atoi(gz_args_positional(&args, 1));
    }

    const char *fmt = gz_args_get_string(&args, "--format", "raw");

    gz_tiff_t tiff;
    gz_status_t st = gz_tiff_open(&tiff, path);
    if (st != GZ_OK) {
        fprintf(stderr, "Error: failed to open TIFF: %s\n", path);
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

    if ((size_t)band >= spp) {
        fprintf(stderr, "Error: band %d out of range (0-%u)\n", band, spp - 1);
        gz_tiff_close(&tiff);
        gz_args_free(&args);
        return 1;
    }

    gz_raster_t raster;
    memset(&raster, 0, sizeof(raster));

    st = gz_raster_alloc(&raster, width, height, 1,
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

    size_t pixel_count = (size_t)width * (size_t)height;
    size_t ds = gz_dtype_size(raster.dtype);

    if (strcmp(fmt, "float32") == 0) {
        gz_raster_t promoted;
        memset(&promoted, 0, sizeof(promoted));
        st = gz_raster_promote(&raster, &promoted, GZ_DTYPE_FLOAT32);
        if (st == GZ_OK) {
            float *data = (float *)promoted.data;
            fwrite(data, sizeof(float), pixel_count, stdout);
            gz_raster_free(&promoted);
        }
    } else if (strcmp(fmt, "uint8") == 0) {
        uint8_t *data = (uint8_t *)raster.data;
        fwrite(data, 1, pixel_count, stdout);
    } else {
        fwrite(raster.data, ds, pixel_count, stdout);
    }

    gz_raster_free(&raster);
    gz_tiff_close(&tiff);
    gz_args_free(&args);
    return 0;
}
