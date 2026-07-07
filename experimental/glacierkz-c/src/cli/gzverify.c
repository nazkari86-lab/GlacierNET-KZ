#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "glacierkz_tiff.h"
#include "glacierkz_checksum.h"
#include "glacierkz_args.h"
#include "glacierkz_endian.h"

static gz_status_t compute_file_crc32(const char *path, uint32_t *out) {
    FILE *fp = fopen(path, "rb");
    if (!fp) return GZ_ERR_IO;

    gz_crc32_t ctx;
    gz_crc32_init(&ctx);

    uint8_t buf[8192];
    size_t n;
    while ((n = fread(buf, 1, sizeof(buf), fp)) > 0) {
        gz_crc32_update(&ctx, buf, n);
    }

    *out = gz_crc32_final(ctx);
    fclose(fp);
    return GZ_OK;
}

static gz_status_t compute_file_sha256(const char *path, uint8_t out[32]) {
    FILE *fp = fopen(path, "rb");
    if (!fp) return GZ_ERR_IO;

    gz_sha256_t ctx;
    gz_sha256_init(&ctx);

    uint8_t buf[8192];
    size_t n;
    while ((n = fread(buf, 1, sizeof(buf), fp)) > 0) {
        gz_sha256_update(&ctx, buf, n);
    }

    gz_sha256_final(ctx, out);
    fclose(fp);
    return GZ_OK;
}

static void print_usage(const char *prog) {
    fprintf(stderr, "Usage: %s [options] <file.tif>\n", prog);
    fprintf(stderr, "  -v, --verbose     Show detailed verification\n");
    fprintf(stderr, "  -c, --compute     Compute CRC32 checksum\n");
    fprintf(stderr, "  -s, --sha256      Compute SHA-256 hash\n");
    fprintf(stderr, "  -h, --help        Show this help\n");
}

int main(int argc, char **argv) {
    gz_arg_def_t defs[] = {
        { "-v", "--verbose", "Verbose output", GZ_ARG_FLAG, 0, 0, NULL, 0, 0.0 },
        { "-c", "--compute", "Compute checksum", GZ_ARG_FLAG, 0, 0, NULL, 0, 0.0 },
        { "-s", "--sha256", "Compute SHA-256", GZ_ARG_FLAG, 0, 0, NULL, 0, 0.0 },
        { "-h", "--help", "Show help", GZ_ARG_FLAG, 0, 0, NULL, 0, 0.0 },
    };

    gz_args_t args;
    gz_args_init(&args, defs, 4);

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
    int compute_crc = gz_args_found(&args, "--compute");
    int compute_sha = gz_args_found(&args, "--sha256");

    if (compute_crc) {
        uint32_t crc;
        gz_status_t st = compute_file_crc32(path, &crc);
        if (st != GZ_OK) {
            fprintf(stderr, "Error: failed to compute CRC32 (code %d)\n", st);
            gz_args_free(&args);
            return 1;
        }
        printf("CRC32: %08x\n", crc);
    }

    if (compute_sha) {
        uint8_t hash[32];
        gz_status_t st = compute_file_sha256(path, hash);
        if (st != GZ_OK) {
            fprintf(stderr, "Error: failed to compute SHA-256 (code %d)\n", st);
            gz_args_free(&args);
            return 1;
        }
        printf("SHA-256: %s\n", gz_hex_string(hash, 32));
    }

    gz_tiff_t tiff;
    gz_status_t st = gz_tiff_open(&tiff, path);
    if (st != GZ_OK) {
        fprintf(stderr, "Error: failed to open TIFF: %s (code %d)\n", path, st);
        gz_args_free(&args);
        return 1;
    }

    int errors = 0;
    int warnings = 0;

    printf("Verifying: %s\n", path);

    if (tiff.byte_order != GZ_ENDIAN_LITTLE && tiff.byte_order != GZ_ENDIAN_BIG) {
        fprintf(stderr, "  [ERROR] Invalid byte order: %d\n", tiff.byte_order);
        errors++;
    } else if (verbose) {
        printf("  Byte order: %s\n", tiff.byte_order == GZ_ENDIAN_LITTLE ? "Little-endian" : "Big-endian");
    }

    if (tiff.ifd_count == 0) {
        fprintf(stderr, "  [ERROR] No IFDs found\n");
        errors++;
    } else if (verbose) {
        printf("  IFD count: %zu\n", tiff.ifd_count);
    }

    for (size_t i = 0; i < tiff.ifd_count; i++) {
        const gz_ifd_t *ifd = &tiff.ifds[i];

        uint32_t width = gz_tiff_get_uint(ifd, 256, 0);
        uint32_t height = gz_tiff_get_uint(ifd, 257, 0);
        uint16_t bps = gz_tiff_get_ushort(ifd, 258, 0);
        uint16_t spp = gz_tiff_get_ushort(ifd, 277, 1);

        if (width == 0 || height == 0) {
            fprintf(stderr, "  [ERROR] IFD %zu: invalid dimensions %ux%u\n", i, width, height);
            errors++;
        } else if (verbose) {
            printf("  IFD %zu: %ux%u, bps=%u, spp=%u\n", i, width, height, bps, spp);
        }

        if (bps == 0 || bps > 64) {
            fprintf(stderr, "  [ERROR] IFD %zu: invalid BitsPerSample %u\n", i, bps);
            errors++;
        } else if (verbose) {
            printf("    BitsPerSample: %u OK\n", bps);
        }

        uint16_t compression = gz_tiff_get_ushort(ifd, 259, 1);
        if (compression != 1 && compression != 5 && compression != 8 &&
            compression != 32773) {
            fprintf(stderr, "  [WARN]  IFD %zu: unsupported compression %u\n", i, compression);
            warnings++;
        } else if (verbose) {
            printf("    Compression: %u supported\n", compression);
        }

        uint32_t strip_off = gz_tiff_get_uint(ifd, 273, 0);
        uint32_t strip_cnt = gz_tiff_get_uint(ifd, 279, 0);
        if (strip_off && strip_cnt) {
            if (verbose) {
                printf("    Strips: offset=%u, bytecount=%u\n", strip_off, strip_cnt);
            }
        }

        uint32_t tile_w = gz_tiff_get_uint(ifd, 322, 0);
        uint32_t tile_h = gz_tiff_get_uint(ifd, 323, 0);
        if (tile_w && tile_h) {
            if (tile_w % 16 != 0 || tile_h % 16 != 0) {
                fprintf(stderr, "  [WARN]  IFD %zu: tile size %ux%u not 16-aligned\n", i, tile_w, tile_h);
                warnings++;
            } else if (verbose) {
                printf("    Tiles: %ux%u\n", tile_w, tile_h);
            }
        }

        uint16_t sample_fmt = gz_tiff_get_ushort(ifd, 339, 1);
        if (sample_fmt == 0 || sample_fmt > 4) {
            fprintf(stderr, "  [WARN]  IFD %zu: unknown SampleFormat %u\n", i, sample_fmt);
            warnings++;
        }
    }

    printf("\nVerification complete: %d error(s), %d warning(s)\n", errors, warnings);

    gz_tiff_close(&tiff);
    gz_args_free(&args);
    return errors > 0 ? 1 : 0;
}
