#include "glacierkz_endian.h"
#include <string.h>

gz_endian_t gz_endian_detect(void) {
    uint16_t v = 1;
    uint8_t *p = (uint8_t *)&v;
    if (*p == 1) return GZ_ENDIAN_LITTLE;
    return GZ_ENDIAN_BIG;
}

uint16_t gz_swap16(uint16_t v) {
    return (uint16_t)((v >> 8) | (v << 8));
}

uint32_t gz_swap32(uint32_t v) {
    return ((v >> 24) & 0x000000FF) |
           ((v >>  8) & 0x0000FF00) |
           ((v <<  8) & 0x00FF0000) |
           ((v << 24) & 0xFF000000);
}

uint64_t gz_swap64(uint64_t v) {
    return ((v >> 56) & 0x00000000000000FFULL) |
           ((v >> 40) & 0x000000000000FF00ULL) |
           ((v >> 24) & 0x0000000000FF0000ULL) |
           ((v >>  8) & 0x00000000FF000000ULL) |
           ((v <<  8) & 0x000000FF00000000ULL) |
           ((v << 24) & 0x0000FF0000000000ULL) |
           ((v << 40) & 0x00FF000000000000ULL) |
           ((v << 56) & 0xFF00000000000000ULL);
}

float gz_swap_float(float v) {
    uint32_t tmp;
    memcpy(&tmp, &v, sizeof(tmp));
    tmp = gz_swap32(tmp);
    float result;
    memcpy(&result, &tmp, sizeof(result));
    return result;
}

double gz_swap_double(double v) {
    uint64_t tmp;
    memcpy(&tmp, &v, sizeof(tmp));
    tmp = gz_swap64(tmp);
    double result;
    memcpy(&result, &tmp, sizeof(result));
    return result;
}

uint16_t gz_htobe16(uint16_t v) {
    gz_endian_t e = gz_endian_detect();
    return (e == GZ_ENDIAN_BIG) ? v : gz_swap16(v);
}

uint16_t gz_betoh16(uint16_t v) {
    gz_endian_t e = gz_endian_detect();
    return (e == GZ_ENDIAN_BIG) ? v : gz_swap16(v);
}

uint32_t gz_htobe32(uint32_t v) {
    gz_endian_t e = gz_endian_detect();
    return (e == GZ_ENDIAN_BIG) ? v : gz_swap32(v);
}

uint32_t gz_betoh32(uint32_t v) {
    gz_endian_t e = gz_endian_detect();
    return (e == GZ_ENDIAN_BIG) ? v : gz_swap32(v);
}

uint64_t gz_htobe64(uint64_t v) {
    gz_endian_t e = gz_endian_detect();
    return (e == GZ_ENDIAN_BIG) ? v : gz_swap64(v);
}

uint64_t gz_betoh64(uint64_t v) {
    gz_endian_t e = gz_endian_detect();
    return (e == GZ_ENDIAN_BIG) ? v : gz_swap64(v);
}

void gz_endian_swap_array16(uint16_t *arr, size_t count) {
    for (size_t i = 0; i < count; i++) {
        arr[i] = gz_swap16(arr[i]);
    }
}

void gz_endian_swap_array32(uint32_t *arr, size_t count) {
    for (size_t i = 0; i < count; i++) {
        arr[i] = gz_swap32(arr[i]);
    }
}

void gz_endian_swap_array64(uint64_t *arr, size_t count) {
    for (size_t i = 0; i < count; i++) {
        arr[i] = gz_swap64(arr[i]);
    }
}

void gz_endian_swap_buffer(void *buf, size_t elem_size, size_t count) {
    uint8_t *p = (uint8_t *)buf;
    for (size_t i = 0; i < count; i++) {
        uint8_t tmp[8];
        memcpy(tmp, p + i * elem_size, elem_size);
        for (size_t j = 0; j < elem_size / 2; j++) {
            uint8_t t = tmp[j];
            tmp[j] = tmp[elem_size - 1 - j];
            tmp[elem_size - 1 - j] = t;
        }
        memcpy(p + i * elem_size, tmp, elem_size);
    }
}
