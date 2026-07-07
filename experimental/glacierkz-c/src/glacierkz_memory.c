#include "glacierkz_memory.h"
#include "glacierkz_log.h"
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

static gz_alloc_block_t *create_block(size_t block_size) {
    gz_alloc_block_t *blk = malloc(sizeof(gz_alloc_block_t) + block_size);
    if (!blk) return NULL;
    blk->next = NULL;
    blk->capacity = block_size;
    blk->used = 0;
    return blk;
}

gz_arena_t *gz_arena_create(size_t block_size, const char *label) {
    if (block_size < 4096) block_size = 4096;

    gz_arena_t *arena = calloc(1, sizeof(gz_arena_t));
    if (!arena) return NULL;

    gz_alloc_block_t *blk = create_block(block_size);
    if (!blk) { free(arena); return NULL; }

    arena->blocks = blk;
    arena->current = blk;
    arena->block_size = block_size;
    arena->total_allocated = 0;
    arena->total_allocations = 0;
    arena->peak_usage = 0;
    arena->label = label ? label : "arena";

    GZ_DEBUG("Arena '%s' created with block size %zu", arena->label, block_size);
    return arena;
}

void *gz_arena_alloc(gz_arena_t *arena, size_t size) {
    return gz_arena_alloc_aligned(arena, size, sizeof(void *));
}

void *gz_arena_alloc_aligned(gz_arena_t *arena, size_t size, size_t alignment) {
    if (!arena || size == 0) return NULL;

    if (alignment < sizeof(void *)) alignment = sizeof(void *);

    size_t pad = (alignment - (arena->current->used % alignment)) % alignment;
    size_t total = size + pad;

    if (arena->current->used + total > arena->current->capacity) {
        size_t new_cap = (total > arena->block_size) ? total : arena->block_size;
        gz_alloc_block_t *blk = create_block(new_cap);
        if (!blk) return NULL;
        blk->next = arena->current;
        arena->current = blk;
        pad = 0;
    }

    void *ptr = (uint8_t *)arena->current + sizeof(gz_alloc_block_t) + arena->current->used + pad;
    arena->current->used += total;
    arena->total_allocated += size;
    arena->total_allocations++;

    size_t current_usage = 0;
    gz_alloc_block_t *b = arena->blocks;
    while (b) {
        current_usage += b->used;
        b = b->next;
    }
    if (current_usage > arena->peak_usage) {
        arena->peak_usage = current_usage;
    }

    return ptr;
}

void *gz_arena_calloc(gz_arena_t *arena, size_t count, size_t size) {
    size_t total = count * size;
    void *ptr = gz_arena_alloc(arena, total);
    if (ptr) memset(ptr, 0, total);
    return ptr;
}

void gz_arena_reset(gz_arena_t *arena) {
    if (!arena) return;

    gz_alloc_block_t *blk = arena->blocks;
    while (blk) {
        blk->used = 0;
        blk = blk->next;
    }
    arena->current = arena->blocks;
    arena->total_allocated = 0;
    arena->total_allocations = 0;
}

void gz_arena_destroy(gz_arena_t *arena) {
    if (!arena) return;

    gz_alloc_block_t *blk = arena->blocks;
    while (blk) {
        gz_alloc_block_t *next = blk->next;
        free(blk);
        blk = next;
    }
    free(arena);
}

void gz_arena_print_stats(const gz_arena_t *arena) {
    if (!arena) return;

    size_t block_count = 0;
    gz_alloc_block_t *blk = arena->blocks;
    while (blk) {
        block_count++;
        blk = blk->next;
    }

    GZ_INFO("Arena '%s': %zu blocks, %zu total allocs, %zu bytes allocated, peak %zu",
            arena->label, block_count, arena->total_allocations,
            arena->total_allocated, arena->peak_usage);
}

#define ALIGN_MAGIC 0xDEADBEEF

typedef struct {
    size_t alignment;
    size_t size;
    uint32_t magic;
} aligned_header_t;

void *gz_aligned_alloc(size_t size, size_t alignment) {
    if (size == 0 || alignment < sizeof(void *)) return NULL;

    size_t header_size = sizeof(aligned_header_t);
    size_t total = header_size + alignment + size;

    void *raw = malloc(total);
    if (!raw) return NULL;

    uintptr_t raw_addr = (uintptr_t)raw + header_size;
    uintptr_t aligned_addr = (raw_addr + alignment - 1) & ~((uintptr_t)alignment - 1);

    aligned_header_t *hdr = (aligned_header_t *)(aligned_addr - header_size);
    hdr->alignment = alignment;
    hdr->size = size;
    hdr->magic = ALIGN_MAGIC;

    return (void *)aligned_addr;
}

void gz_aligned_free(void *ptr) {
    if (!ptr) return;

    aligned_header_t *hdr = (aligned_header_t *)((uint8_t *)ptr - sizeof(aligned_header_t));
    if (hdr->magic != ALIGN_MAGIC) {
        GZ_ERROR("Invalid aligned free: magic mismatch");
        return;
    }
    hdr->magic = 0;
    free(hdr);
}
