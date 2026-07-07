#ifndef GLACIERKZ_ENDIAN_H
#define GLACIERKZ_ENDIAN_H

#include <stdint.h>
#include <stddef.h>

typedef enum {
    GZ_ENDIAN_LITTLE = 0,
    GZ_ENDIAN_BIG = 1,
    GZ_ENDIAN_NATIVE = 2
} gz_endian_t;

gz_endian_t gz_endian_detect(void);
uint16_t    gz_swap16(uint16_t v);
uint32_t    gz_swap32(uint32_t v);
uint64_t    gz_swap64(uint64_t v);
float       gz_swap_float(float v);
double      gz_swap_double(double v);

uint16_t    gz_htobe16(uint16_t v);
uint16_t    gz_betoh16(uint16_t v);
uint32_t    gz_htobe32(uint32_t v);
uint32_t    gz_betoh32(uint32_t v);
uint64_t    gz_htobe64(uint64_t v);
uint64_t    gz_betoh64(uint64_t v);

void gz_endian_swap_array16(uint16_t *arr, size_t count);
void gz_endian_swap_array32(uint32_t *arr, size_t count);
void gz_endian_swap_array64(uint64_t *arr, size_t count);
void gz_endian_swap_buffer(void *buf, size_t elem_size, size_t count);

#endif
