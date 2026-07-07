#include <stdio.h>
#include <stdlib.h>
#include "glacierkz_tiff.h"
#include "glacierkz_raster.h"
#include "glacierkz_args.h"
#include "glacierkz_log.h"
#include "glacierkz_endian.h"

static void print_usage(const char *prog) {
    fprintf(stderr, "Usage: %s [options] <file.tif>\n", prog);
    fprintf(stderr, "  -v, --verbose    Show verbose output\n");
    fprintf(stderr, "  -q, --quiet      Suppress info messages\n");
    fprintf(stderr, "  -h, --help       Show this help\n");
}

int main(int argc, char **argv) {
    gz_arg_def_t defs[] = {
        { "-v", "--verbose", "Verbose output", GZ_ARG_FLAG, 0, 0, NULL, 0, 0.0 },
        { "-q", "--quiet", "Quiet mode", GZ_ARG_FLAG, 0, 0, NULL, 0, 0.0 },
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

    if (gz_args_positional_count(&args) < 1) {
        fprintf(stderr, "Error: no input file specified\n");
        print_usage(argv[0]);
        gz_args_free(&args);
        return 1;
    }

    const char *path = gz_args_positional(&args, 0);
    int verbose = gz_args_found(&args, "--verbose");

    gz_logger_t logger;
    gz_log_init(&logger);
    gz_log_set_level(&logger, verbose ? GZ_LOG_DEBUG : GZ_LOG_INFO);
    g_gz_logger = logger;

    gz_tiff_t tiff;
    gz_status_t st = gz_tiff_open(&tiff, path);
    if (st != GZ_OK) {
        fprintf(stderr, "Error: failed to open TIFF: %s (code %d)\n", path, st);
        gz_args_free(&args);
        return 1;
    }

    printf("File: %s\n", path);
    printf("Format: %s\n", tiff.is_bigtiff ? "BigTIFF" : "TIFF");
    printf("Byte order: %s\n", tiff.byte_order == GZ_ENDIAN_LITTLE ? "Little-endian" : "Big-endian");
    printf("IFD count: %zu\n", tiff.ifd_count);

    for (size_t i = 0; i < tiff.ifd_count; i++) {
        const gz_ifd_t *ifd = &tiff.ifds[i];
        printf("\n--- IFD %zu (%u entries) ---\n", i, ifd->count);

        uint32_t width = gz_tiff_get_uint(ifd, 256, 0);
        uint32_t height = gz_tiff_get_uint(ifd, 257, 0);
        uint16_t bps = gz_tiff_get_ushort(ifd, 258, 0);
        uint16_t spp = gz_tiff_get_ushort(ifd, 277, 1);
        uint16_t compression = gz_tiff_get_ushort(ifd, 259, 1);
        uint16_t photo = gz_tiff_get_ushort(ifd, 262, 0);
        uint16_t sample_fmt = gz_tiff_get_ushort(ifd, 339, 1);

        printf("  ImageWidth:       %u\n", width);
        printf("  ImageLength:      %u\n", height);
        printf("  BitsPerSample:    %u\n", bps);
        printf("  SamplesPerPixel:  %u\n", spp);
        printf("  Compression:      %u (%s)\n", compression,
               compression == 1 ? "None" :
               compression == 5 ? "LZW" :
               compression == 8 ? "Deflate" :
               compression == 32773 ? "PackBits" : "Unknown");
        printf("  PhotometricInterpretation: %u (%s)\n", photo,
               photo == 0 ? "MinIsBlack" :
               photo == 1 ? "MinIsWhite" :
               photo == 2 ? "RGB" : "Unknown");
        printf("  SampleFormat:     %u (%s)\n", sample_fmt,
               sample_fmt == 1 ? "Uint" :
               sample_fmt == 2 ? "Int" :
               sample_fmt == 3 ? "IEEEFP" : "Unknown");

        uint32_t strip_off = gz_tiff_get_uint(ifd, 273, 0);
        uint32_t strip_cnt = gz_tiff_get_uint(ifd, 279, 0);
        if (strip_off) printf("  StripOffsets:     %u\n", strip_off);
        if (strip_cnt) printf("  StripByteCounts:  %u\n", strip_cnt);

        uint32_t tile_w = gz_tiff_get_uint(ifd, 322, 0);
        uint32_t tile_h = gz_tiff_get_uint(ifd, 323, 0);
        if (tile_w && tile_h) printf("  TileSize:         %ux%u\n", tile_w, tile_h);

        uint32_t rows_per = gz_tiff_get_uint(ifd, 278, 0);
        if (rows_per) printf("  RowsPerStrip:     %u\n", rows_per);

        double xres = gz_tiff_get_double(ifd, 282, 0);
        double yres = gz_tiff_get_double(ifd, 283, 0);
        if (xres > 0) printf("  XResolution:      %.2f\n", xres);
        if (yres > 0) printf("  YResolution:      %.2f\n", yres);

        uint16_t res_unit = gz_tiff_get_ushort(ifd, 296, 0);
        if (res_unit) printf("  ResolutionUnit:   %u\n", res_unit);

        if (verbose) {
            printf("\n  All tags:\n");
            for (uint16_t t = 0; t < ifd->count; t++) {
                const gz_ifd_entry_t *e = &ifd->entries[t];
                printf("    Tag %5u (type=%u, count=%u): ", e->tag, e->type, e->count);
                if (e->type == GZ_TAG_TYPE_SHORT && e->count <= 2) {
                    for (uint32_t c = 0; c < e->count && c < 2; c++)
                        printf("%u ", e->value.short_data[c]);
                } else if (e->type == GZ_TAG_TYPE_LONG && e->count == 1) {
                    printf("%u", e->value.long_data[0]);
                } else if (e->type == GZ_TAG_TYPE_ASCII) {
                    if (e->count <= 4) printf("%.4s", e->value.ascii_data);
                    else printf("(offset=%u)", e->value.offset);
                } else {
                    printf("(offset=%u)", e->value.offset);
                }
                printf("\n");
            }
        }
    }

    gz_tiff_close(&tiff);
    gz_args_free(&args);
    return 0;
}
