#include "glacierkz_checksum.h"
#include <string.h>

static uint32_t crc32_table[256];
static int crc32_table_ready = 0;

static void crc32_build_table(void) {
    for (uint32_t i = 0; i < 256; i++) {
        uint32_t c = i;
        for (int j = 0; j < 8; j++) {
            c = (c & 1) ? (0xEDB88320u ^ (c >> 1)) : (c >> 1);
        }
        crc32_table[i] = c;
    }
    crc32_table_ready = 1;
}

void gz_crc32_init(gz_crc32_t *ctx) {
    if (!crc32_table_ready) crc32_build_table();
    ctx->crc = 0xFFFFFFFFu;
}

void gz_crc32_update(gz_crc32_t *ctx, const void *data, size_t len) {
    const uint8_t *p = (const uint8_t *)data;
    uint32_t c = ctx->crc;
    for (size_t i = 0; i < len; i++) {
        c = crc32_table[(c ^ p[i]) & 0xFF] ^ (c >> 8);
    }
    ctx->crc = c;
}

uint32_t gz_crc32_final(gz_crc32_t ctx) {
    return ctx.crc ^ 0xFFFFFFFFu;
}

uint32_t gz_crc32_compute(const void *data, size_t len) {
    gz_crc32_t ctx;
    gz_crc32_init(&ctx);
    gz_crc32_update(&ctx, data, len);
    return gz_crc32_final(ctx);
}

static const uint32_t adler_mod = 65521u;

void gz_adler32_init(gz_adler32_t *ctx) {
    ctx->state = 1u;
    ctx->length = 0;
}

void gz_adler32_update(gz_adler32_t *ctx, const void *data, size_t len) {
    const uint8_t *p = (const uint8_t *)data;
    uint32_t s = ctx->state;
    uint32_t a = s & 0xFFFF;
    uint32_t b = s >> 16;

    for (size_t i = 0; i < len; i++) {
        a = (a + p[i]) % adler_mod;
        b = (b + a) % adler_mod;
    }

    ctx->state = (b << 16) | a;
    ctx->length += (uint32_t)len;
}

uint32_t gz_adler32_final(gz_adler32_t ctx) {
    return ctx.state;
}

uint32_t gz_adler32_compute(const void *data, size_t len) {
    gz_adler32_t ctx;
    gz_adler32_init(&ctx);
    gz_adler32_update(&ctx, data, len);
    return gz_adler32_final(ctx);
}

static const uint32_t sha256_k[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
};

#define ROTR32(x, n) (((x) >> (n)) | ((x) << (32 - (n))))
#define CH(x,y,z) (((x) & (y)) ^ (~(x) & (z)))
#define MAJ(x,y,z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))
#define SIGMA0(x) (ROTR32(x,2) ^ ROTR32(x,13) ^ ROTR32(x,22))
#define SIGMA1(x) (ROTR32(x,6) ^ ROTR32(x,11) ^ ROTR32(x,25))
#define sigma0(x) (ROTR32(x,7) ^ ROTR32(x,18) ^ ((x) >> 3))
#define sigma1(x) (ROTR32(x,17) ^ ROTR32(x,19) ^ ((x) >> 10))

static void sha256_compress(uint32_t state[8], const uint8_t block[64]) {
    uint32_t w[64];
    for (int i = 0; i < 16; i++) {
        w[i] = ((uint32_t)block[i*4] << 24) | ((uint32_t)block[i*4+1] << 16) |
               ((uint32_t)block[i*4+2] << 8) | (uint32_t)block[i*4+3];
    }
    for (int i = 16; i < 64; i++) {
        w[i] = sigma1(w[i-2]) + w[i-7] + sigma0(w[i-15]) + w[i-16];
    }

    uint32_t a = state[0], b = state[1], c = state[2], d = state[3];
    uint32_t e = state[4], f = state[5], g = state[6], h = state[7];

    for (int i = 0; i < 64; i++) {
        uint32_t t1 = h + SIGMA1(e) + CH(e,f,g) + sha256_k[i] + w[i];
        uint32_t t2 = SIGMA0(a) + MAJ(a,b,c);
        h = g; g = f; f = e; e = d + t1;
        d = c; c = b; b = a; a = t1 + t2;
    }

    state[0] += a; state[1] += b; state[2] += c; state[3] += d;
    state[4] += e; state[5] += f; state[6] += g; state[7] += h;
}

void gz_sha256_init(gz_sha256_t *ctx) {
    ctx->state[0] = 0x6a09e667;
    ctx->state[1] = 0xbb67ae85;
    ctx->state[2] = 0x3c6ef372;
    ctx->state[3] = 0xa54ff53a;
    ctx->state[4] = 0x510e527f;
    ctx->state[5] = 0x9b05688c;
    ctx->state[6] = 0x1f83d9ab;
    ctx->state[7] = 0x5be0cd19;
    ctx->total_len = 0;
    ctx->buf_len = 0;
}

void gz_sha256_update(gz_sha256_t *ctx, const void *data, size_t len) {
    const uint8_t *p = (const uint8_t *)data;
    size_t remaining = len;

    if (ctx->buf_len > 0) {
        size_t needed = 64 - ctx->buf_len;
        size_t to_copy = (remaining < needed) ? remaining : needed;
        memcpy(ctx->buffer + ctx->buf_len, p, to_copy);
        ctx->buf_len += to_copy;
        p += to_copy;
        remaining -= to_copy;
        if (ctx->buf_len == 64) {
            sha256_compress(ctx->state, ctx->buffer);
            ctx->buf_len = 0;
            ctx->total_len += 64;
        }
    }

    while (remaining >= 64) {
        sha256_compress(ctx->state, p);
        p += 64;
        remaining -= 64;
        ctx->total_len += 64;
    }

    if (remaining > 0) {
        memcpy(ctx->buffer, p, remaining);
        ctx->buf_len = remaining;
    }
    ctx->total_len += (len - remaining - (ctx->buf_len == 0 ? 0 : 0));
}

void gz_sha256_final(gz_sha256_t ctx, uint8_t out[32]) {
    uint64_t total_bits = (ctx.total_len + ctx.buf_len) * 8;
    ctx.buffer[ctx.buf_len++] = 0x80;

    if (ctx.buf_len > 56) {
        while (ctx.buf_len < 64) ctx.buffer[ctx.buf_len++] = 0;
        sha256_compress(ctx.state, ctx.buffer);
        ctx.buf_len = 0;
    }
    while (ctx.buf_len < 56) ctx.buffer[ctx.buf_len++] = 0;

    for (int i = 7; i >= 0; i--) {
        ctx.buffer[ctx.buf_len++] = (uint8_t)(total_bits >> (i * 8));
    }
    sha256_compress(ctx.state, ctx.buffer);

    for (int i = 0; i < 8; i++) {
        out[i*4]   = (uint8_t)(ctx.state[i] >> 24);
        out[i*4+1] = (uint8_t)(ctx.state[i] >> 16);
        out[i*4+2] = (uint8_t)(ctx.state[i] >> 8);
        out[i*4+3] = (uint8_t)(ctx.state[i]);
    }
}

void gz_sha256_compute(const void *data, size_t len, uint8_t out[32]) {
    gz_sha256_t ctx;
    gz_sha256_init(&ctx);
    gz_sha256_update(&ctx, data, len);
    gz_sha256_final(ctx, out);
}

static const char hex_chars[] = "0123456789abcdef";

const char *gz_hex_string(const uint8_t *data, size_t len) {
    static char buf[129];
    size_t max = (len < 64) ? len : 64;
    for (size_t i = 0; i < max; i++) {
        buf[i*2]   = hex_chars[(data[i] >> 4) & 0x0F];
        buf[i*2+1] = hex_chars[data[i] & 0x0F];
    }
    buf[max*2] = '\0';
    return buf;
}
