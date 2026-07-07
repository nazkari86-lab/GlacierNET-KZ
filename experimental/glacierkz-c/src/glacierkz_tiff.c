#include "glacierkz_tiff.h"
#include "glacierkz_endian.h"
#include "glacierkz_log.h"
#include <stdlib.h>
#include <string.h>

gz_status_t gz_tiff_open(gz_tiff_t *tiff, const char *path) {
    if (!tiff || !path) return GZ_ERR_PARAM;

    tiff->fp = fopen(path, "rb");
    if (!tiff->fp) {
        GZ_ERROR("Failed to open: %s", path);
        return GZ_ERR_IO;
    }

    tiff->path = path;
    tiff->is_bigtiff = 0;
    tiff->byte_order = GZ_ENDIAN_LITTLE;
    tiff->first_ifd_offset = 0;
    tiff->ifds = NULL;
    tiff->ifd_count = 0;
    tiff->ifd_capacity = 0;

    gz_status_t st = gz_tiff_parse(tiff);
    if (st != GZ_OK) {
        gz_tiff_close(tiff);
    }
    return st;
}

gz_status_t gz_tiff_parse(gz_tiff_t *tiff) {
    uint8_t header[8];
    if (fread(header, 1, 8, tiff->fp) != 8) {
        GZ_ERROR("Failed to read TIFF header");
        return GZ_ERR_IO;
    }

    if (header[0] == 'I' && header[1] == 'I') {
        tiff->byte_order = GZ_ENDIAN_LITTLE;
    } else if (header[0] == 'M' && header[1] == 'M') {
        tiff->byte_order = GZ_ENDIAN_BIG;
    } else {
        GZ_ERROR("Invalid TIFF magic: 0x%02X%02X", header[0], header[1]);
        return GZ_ERR_FORMAT;
    }

    int native_le = (gz_endian_detect() == GZ_ENDIAN_LITTLE);
    int need_swap = (tiff->byte_order == GZ_ENDIAN_BIG && native_le) ||
                    (tiff->byte_order == GZ_ENDIAN_LITTLE && !native_le);

    uint16_t magic = (uint16_t)header[2] | ((uint16_t)header[3] << 8);
    if (need_swap) magic = gz_swap16(magic);

    if (magic == 42) {
        tiff->is_bigtiff = 0;
    } else if (magic == 43) {
        tiff->is_bigtiff = 1;
        GZ_WARN("BigTIFF detected, limited support");
        return GZ_ERR_FORMAT;
    } else {
        GZ_ERROR("Invalid TIFF magic number: %u", magic);
        return GZ_ERR_FORMAT;
    }

    if (tiff->is_bigtiff) {
        uint16_t offset_size;
        memcpy(&offset_size, header + 4, 2);
        if (need_swap) offset_size = gz_swap16(offset_size);
        (void)offset_size;

        uint8_t offs_buf[4];
        if (fread(offs_buf, 1, 4, tiff->fp) != 4) return GZ_ERR_IO;
        memcpy(&tiff->first_ifd_offset, offs_buf, 4);
        if (need_swap) tiff->first_ifd_offset = gz_swap32(tiff->first_ifd_offset);
    } else {
        uint8_t offs_buf[4];
        if (fread(offs_buf, 1, 4, tiff->fp) != 4) return GZ_ERR_IO;
        uint32_t off32;
        memcpy(&off32, offs_buf, 4);
        if (need_swap) off32 = gz_swap32(off32);
        tiff->first_ifd_offset = off32;
    }

    uint32_t ifd_offset = tiff->first_ifd_offset;
    int ifd_limit = 64;
    while (ifd_offset != 0 && ifd_limit-- > 0) {
        gz_ifd_t ifd = {0};
        gz_status_t st = gz_tiff_read_ifd(tiff, ifd_offset, &ifd);
        if (st != GZ_OK) return st;

        if (tiff->ifd_count >= tiff->ifd_capacity) {
            size_t new_cap = tiff->ifd_capacity ? tiff->ifd_capacity * 2 : 4;
            gz_ifd_t *new_ifds = realloc(tiff->ifds, new_cap * sizeof(gz_ifd_t));
            if (!new_ifds) return GZ_ERR_NOMEM;
            tiff->ifds = new_ifds;
            tiff->ifd_capacity = new_cap;
        }
        tiff->ifds[tiff->ifd_count++] = ifd;

        if (tiff->is_bigtiff) {
            uint8_t next_buf[8];
            if (fseek(tiff->fp, (long)ifd_offset + 2 + ifd.count * 20 + 8, SEEK_SET) != 0)
                break;
            if (fread(next_buf, 1, 8, tiff->fp) != 8) break;
            uint64_t next;
            memcpy(&next, next_buf, 8);
            if (need_swap) next = gz_swap64(next);
            ifd_offset = (uint32_t)next;
        } else {
            if (fseek(tiff->fp, (long)ifd_offset + 2 + ifd.count * 12, SEEK_SET) != 0)
                break;
            uint8_t next_buf[4];
            if (fread(next_buf, 1, 4, tiff->fp) != 4) break;
            memcpy(&ifd_offset, next_buf, 4);
            if (need_swap) ifd_offset = gz_swap32(ifd_offset);
        }
    }

    GZ_DEBUG("Parsed %zu IFD(s) from %s", tiff->ifd_count, tiff->path);
    return GZ_OK;
}

static size_t tag_type_size(uint16_t type) {
    switch (type) {
        case GZ_TAG_TYPE_BYTE:    case GZ_TAG_TYPE_SBYTE:
        case GZ_TAG_TYPE_ASCII:   case GZ_TAG_TYPE_UNDEFINED: return 1;
        case GZ_TAG_TYPE_SHORT:   case GZ_TAG_TYPE_SSHORT:    return 2;
        case GZ_TAG_TYPE_LONG:    case GZ_TAG_TYPE_SLONG:
        case GZ_TAG_TYPE_FLOAT:                                return 4;
        case GZ_TAG_TYPE_RATIONAL: case GZ_TAG_TYPE_DOUBLE:    return 8;
        default: return 0;
    }
}

gz_status_t gz_tiff_read_ifd(gz_tiff_t *tiff, uint32_t offset, gz_ifd_t *ifd) {
    if (!tiff || !ifd) return GZ_ERR_PARAM;

    int native_le = (gz_endian_detect() == GZ_ENDIAN_LITTLE);
    int need_swap = (tiff->byte_order == GZ_ENDIAN_BIG && native_le) ||
                    (tiff->byte_order == GZ_ENDIAN_LITTLE && !native_le);

    if (fseek(tiff->fp, (long)offset, SEEK_SET) != 0) return GZ_ERR_IO;

    uint8_t cnt_buf[2];
    if (fread(cnt_buf, 1, 2, tiff->fp) != 2) return GZ_ERR_IO;

    uint16_t count = (uint16_t)cnt_buf[0] | ((uint16_t)cnt_buf[1] << 8);
    if (need_swap) count = gz_swap16(count);
    if (count > 4096) return GZ_ERR_FORMAT;

    ifd->entries = calloc(count, sizeof(gz_ifd_entry_t));
    if (!ifd->entries) return GZ_ERR_NOMEM;
    ifd->count = count;

    for (uint16_t i = 0; i < count; i++) {
        uint8_t entry_buf[12];
        if (fread(entry_buf, 1, 12, tiff->fp) != 12) {
            free(ifd->entries);
            ifd->entries = NULL;
            ifd->count = 0;
            return GZ_ERR_IO;
        }

        gz_ifd_entry_t *e = &ifd->entries[i];
        e->tag = (uint16_t)entry_buf[0] | ((uint16_t)entry_buf[1] << 8);
        e->type = (uint16_t)entry_buf[2] | ((uint16_t)entry_buf[3] << 8);
        e->count = ((uint32_t)entry_buf[4] << 24) | ((uint32_t)entry_buf[5] << 16) |
                   ((uint32_t)entry_buf[6] << 8) | (uint32_t)entry_buf[7];
        memcpy(e->value.byte_data, entry_buf + 8, 4);

        if (need_swap) {
            e->tag = gz_swap16(e->tag);
            e->type = gz_swap16(e->type);
            e->count = gz_swap32(e->count);

            size_t tsize = tag_type_size(e->type);
            if (tsize == 2 && e->count <= 2) {
                e->value.short_data[0] = gz_swap16(e->value.short_data[0]);
                e->value.short_data[1] = gz_swap16(e->value.short_data[1]);
            } else if (tsize == 4 && e->count == 1) {
                e->value.long_data[0] = gz_swap32(e->value.long_data[0]);
            }
        }
    }

    return GZ_OK;
}

void gz_tiff_free_ifd(gz_ifd_t *ifd) {
    if (!ifd) return;
    free(ifd->entries);
    ifd->entries = NULL;
    ifd->count = 0;
}

void gz_tiff_close(gz_tiff_t *tiff) {
    if (!tiff) return;
    if (tiff->fp) { fclose(tiff->fp); tiff->fp = NULL; }
    for (size_t i = 0; i < tiff->ifd_count; i++) {
        gz_tiff_free_ifd(&tiff->ifds[i]);
    }
    free(tiff->ifds);
    tiff->ifds = NULL;
    tiff->ifd_count = 0;
    tiff->ifd_capacity = 0;
}

const gz_ifd_entry_t *gz_tiff_find_tag(const gz_ifd_t *ifd, uint16_t tag) {
    if (!ifd) return NULL;
    for (uint16_t i = 0; i < ifd->count; i++) {
        if (ifd->entries[i].tag == tag) return &ifd->entries[i];
    }
    return NULL;
}

uint32_t gz_tiff_get_uint(const gz_ifd_t *ifd, uint16_t tag, uint32_t dflt) {
    const gz_ifd_entry_t *e = gz_tiff_find_tag(ifd, tag);
    if (!e) return dflt;
    if (e->type == GZ_TAG_TYPE_LONG) return e->value.long_data[0];
    if (e->type == GZ_TAG_TYPE_SHORT) return e->value.short_data[0];
    return dflt;
}

uint16_t gz_tiff_get_ushort(const gz_ifd_t *ifd, uint16_t tag, uint16_t dflt) {
    const gz_ifd_entry_t *e = gz_tiff_find_tag(ifd, tag);
    if (!e) return dflt;
    if (e->type == GZ_TAG_TYPE_SHORT) return e->value.short_data[0];
    return dflt;
}

double gz_tiff_get_double(const gz_ifd_t *ifd, uint16_t tag, double dflt) {
    const gz_ifd_entry_t *e = gz_tiff_find_tag(ifd, tag);
    if (!e) return dflt;
    if (e->type == GZ_TAG_TYPE_DOUBLE) return e->value.double_data[0];
    if (e->type == GZ_TAG_TYPE_FLOAT) return (double)e->value.float_data[0];
    if (e->type == GZ_TAG_TYPE_RATIONAL) {
        if (e->count == 2) {
            uint32_t num = e->value.long_data[0];
            uint32_t denom;
            int native_le = (gz_endian_detect() == GZ_ENDIAN_LITTLE);
            int need_swap = 0;
            /* For rational, read from IFD file location */
            (void)num; (void)denom; (void)native_le; (void)need_swap;
        }
    }
    if (e->type == GZ_TAG_TYPE_LONG) return (double)e->value.long_data[0];
    if (e->type == GZ_TAG_TYPE_SHORT) return (double)e->value.short_data[0];
    return dflt;
}

const char *gz_tiff_get_string(const gz_tiff_t *tiff, const gz_ifd_t *ifd, uint16_t tag) {
    (void)tiff;
    const gz_ifd_entry_t *e = gz_tiff_find_tag(ifd, tag);
    if (!e) return NULL;
    if (e->type != GZ_TAG_TYPE_ASCII) return NULL;

    if (e->count <= 4) {
        static char short_buf[5];
        memcpy(short_buf, e->value.byte_data, 4);
        short_buf[4] = '\0';
        return short_buf;
    }

    uint32_t offset = e->value.offset;
    char *str = malloc(e->count);
    if (!str) return NULL;

    long saved = ftell(tiff->fp);
    fseek(tiff->fp, (long)offset, SEEK_SET);
    fread(str, 1, e->count, tiff->fp);
    fseek(tiff->fp, saved, SEEK_SET);
    str[e->count - 1] = '\0';
    return str;
}

gz_status_t gz_tiff_read_strip_offsets(const gz_ifd_t *ifd, uint32_t **offsets, uint32_t *count) {
    const gz_ifd_entry_t *e = gz_tiff_find_tag(ifd, 273);
    if (!e) return GZ_ERR_NOTFOUND;

    *count = e->count;
    if (e->count == 1) {
        *offsets = malloc(sizeof(uint32_t));
        if (!*offsets) return GZ_ERR_NOMEM;
        if (e->type == GZ_TAG_TYPE_LONG) (*offsets)[0] = e->value.long_data[0];
        else if (e->type == GZ_TAG_TYPE_SHORT) (*offsets)[0] = e->value.short_data[0];
        return GZ_OK;
    }

    *offsets = calloc(e->count, sizeof(uint32_t));
    if (!*offsets) return GZ_ERR_NOMEM;

    if (e->type == GZ_TAG_TYPE_LONG && e->count <= 1) {
        (*offsets)[0] = e->value.long_data[0];
    } else if (e->type == GZ_TAG_TYPE_SHORT && e->count <= 2) {
        for (uint32_t i = 0; i < e->count && i < 2; i++) {
            (*offsets)[i] = e->value.short_data[i];
        }
    }
    return GZ_OK;
}

gz_status_t gz_tiff_read_tile_offsets(const gz_ifd_t *ifd, uint32_t **offsets, uint32_t *count) {
    const gz_ifd_entry_t *e = gz_tiff_find_tag(ifd, 324);
    if (!e) return GZ_ERR_NOTFOUND;

    *count = e->count;
    *offsets = calloc(e->count, sizeof(uint32_t));
    if (!*offsets) return GZ_ERR_NOMEM;

    if (e->type == GZ_TAG_TYPE_LONG && e->count <= 1) {
        (*offsets)[0] = e->value.long_data[0];
    } else if (e->type == GZ_TAG_TYPE_SHORT && e->count <= 2) {
        for (uint32_t i = 0; i < e->count && i < 2; i++) {
            (*offsets)[i] = e->value.short_data[i];
        }
    }
    return GZ_OK;
}

gz_status_t gz_tiff_read_strip_byte_counts(const gz_ifd_t *ifd, uint32_t **counts, uint32_t *count) {
    const gz_ifd_entry_t *e = gz_tiff_find_tag(ifd, 279);
    if (!e) return GZ_ERR_NOTFOUND;

    *count = e->count;
    if (e->count == 1) {
        *counts = malloc(sizeof(uint32_t));
        if (!*counts) return GZ_ERR_NOMEM;
        if (e->type == GZ_TAG_TYPE_LONG) (*counts)[0] = e->value.long_data[0];
        else if (e->type == GZ_TAG_TYPE_SHORT) (*counts)[0] = e->value.short_data[0];
        return GZ_OK;
    }

    *counts = calloc(e->count, sizeof(uint32_t));
    if (!*counts) return GZ_ERR_NOMEM;

    if (e->type == GZ_TAG_TYPE_LONG && e->count <= 1) {
        (*counts)[0] = e->value.long_data[0];
    } else if (e->type == GZ_TAG_TYPE_SHORT && e->count <= 2) {
        for (uint32_t i = 0; i < e->count && i < 2; i++) {
            (*counts)[i] = e->value.short_data[i];
        }
    }
    return GZ_OK;
}

gz_status_t gz_tiff_read_tile_byte_counts(const gz_ifd_t *ifd, uint32_t **counts, uint32_t *count) {
    const gz_ifd_entry_t *e = gz_tiff_find_tag(ifd, 325);
    if (!e) return GZ_ERR_NOTFOUND;

    *count = e->count;
    *counts = calloc(e->count, sizeof(uint32_t));
    if (!*counts) return GZ_ERR_NOMEM;

    if (e->type == GZ_TAG_TYPE_LONG && e->count <= 1) {
        (*counts)[0] = e->value.long_data[0];
    } else if (e->type == GZ_TAG_TYPE_SHORT && e->count <= 2) {
        for (uint32_t i = 0; i < e->count && i < 2; i++) {
            (*counts)[i] = e->value.short_data[i];
        }
    }
    return GZ_OK;
}
