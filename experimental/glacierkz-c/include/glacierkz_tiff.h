#ifndef GLACIERKZ_TIFF_H
#define GLACIERKZ_TIFF_H

#include <stdint.h>
#include <stddef.h>
#include <stdio.h>

#define GZ_TIFF_MAGIC_LE 0x4949
#define GZ_TIFF_MAGIC_BE 0x4D4D

typedef enum {
    GZ_OK           = 0,
    GZ_ERR_NOMEM    = 1,
    GZ_ERR_IO       = 2,
    GZ_ERR_FORMAT   = 3,
    GZ_ERR_NOTFOUND = 4,
    GZ_ERR_PARAM    = 5,
    GZ_ERR_LIMIT    = 6
} gz_status_t;

typedef enum {
    GZ_TAG_TYPE_BYTE     = 1,
    GZ_TAG_TYPE_ASCII    = 2,
    GZ_TAG_TYPE_SHORT    = 3,
    GZ_TAG_TYPE_LONG     = 4,
    GZ_TAG_TYPE_RATIONAL = 5,
    GZ_TAG_TYPE_SBYTE    = 6,
    GZ_TAG_TYPE_UNDEFINED= 7,
    GZ_TAG_TYPE_SSHORT   = 8,
    GZ_TAG_TYPE_SLONG    = 9,
    GZ_TAG_TYPE_FLOAT    = 10,
    GZ_TAG_TYPE_DOUBLE   = 11
} gz_tag_type_t;

typedef struct {
    uint16_t tag;
    uint16_t type;
    uint32_t count;
    union {
        uint8_t  byte_data[4];
        char     ascii_data[4];
        uint16_t short_data[2];
        uint32_t long_data[1];
        float    float_data[1];
        double   double_data[1];
        uint32_t offset;
    } value;
} gz_ifd_entry_t;

typedef struct {
    gz_ifd_entry_t *entries;
    uint16_t        count;
} gz_ifd_t;

typedef struct {
    FILE           *fp;
    const char     *path;
    int             is_bigtiff;
    int             byte_order;
    uint32_t        first_ifd_offset;
    gz_ifd_t       *ifds;
    size_t          ifd_count;
    size_t          ifd_capacity;
} gz_tiff_t;

gz_status_t gz_tiff_open(gz_tiff_t *tiff, const char *path);
gz_status_t gz_tiff_parse(gz_tiff_t *tiff);
void        gz_tiff_close(gz_tiff_t *tiff);

gz_status_t gz_tiff_read_ifd(gz_tiff_t *tiff, uint32_t offset, gz_ifd_t *ifd);
void        gz_tiff_free_ifd(gz_ifd_t *ifd);

const gz_ifd_entry_t *gz_tiff_find_tag(const gz_ifd_t *ifd, uint16_t tag);
uint32_t gz_tiff_get_uint(const gz_ifd_t *ifd, uint16_t tag, uint32_t dflt);
uint16_t gz_tiff_get_ushort(const gz_ifd_t *ifd, uint16_t tag, uint16_t dflt);
double   gz_tiff_get_double(const gz_ifd_t *ifd, uint16_t tag, double dflt);
const char *gz_tiff_get_string(const gz_tiff_t *tiff, const gz_ifd_t *ifd, uint16_t tag);

gz_status_t gz_tiff_read_strip_offsets(const gz_ifd_t *ifd, uint32_t **offsets, uint32_t *count);
gz_status_t gz_tiff_read_tile_offsets(const gz_ifd_t *ifd, uint32_t **offsets, uint32_t *count);
gz_status_t gz_tiff_read_strip_byte_counts(const gz_ifd_t *ifd, uint32_t **counts, uint32_t *count);
gz_status_t gz_tiff_read_tile_byte_counts(const gz_ifd_t *ifd, uint32_t **counts, uint32_t *count);

#endif
