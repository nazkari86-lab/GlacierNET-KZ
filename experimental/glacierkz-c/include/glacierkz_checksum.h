#ifndef GLACIERKZ_CHECKSUM_H
#define GLACIERKZ_CHECKSUM_H

#include <stdint.h>
#include <stddef.h>

typedef struct {
    uint32_t state;
    uint32_t length;
} gz_adler32_t;

typedef struct {
    uint32_t crc;
} gz_crc32_t;

typedef struct {
    uint32_t state[8];
    uint64_t total_len;
    uint8_t  buffer[64];
    size_t   buf_len;
} gz_sha256_t;

void     gz_crc32_init(gz_crc32_t *ctx);
void     gz_crc32_update(gz_crc32_t *ctx, const void *data, size_t len);
uint32_t gz_crc32_final(gz_crc32_t ctx);
uint32_t gz_crc32_compute(const void *data, size_t len);

void     gz_adler32_init(gz_adler32_t *ctx);
void     gz_adler32_update(gz_adler32_t *ctx, const void *data, size_t len);
uint32_t gz_adler32_final(gz_adler32_t ctx);
uint32_t gz_adler32_compute(const void *data, size_t len);

void     gz_sha256_init(gz_sha256_t *ctx);
void     gz_sha256_update(gz_sha256_t *ctx, const void *data, size_t len);
void     gz_sha256_final(gz_sha256_t ctx, uint8_t out[32]);
void     gz_sha256_compute(const void *data, size_t len, uint8_t out[32]);

const char *gz_hex_string(const uint8_t *data, size_t len);

#endif
