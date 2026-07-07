#ifndef GLACIERKZ_MEMORY_H
#define GLACIERKZ_MEMORY_H

#include <stddef.h>
#include <stdint.h>

typedef struct gz_alloc_block {
    struct gz_alloc_block *next;
    size_t capacity;
    size_t used;
} gz_alloc_block_t;

typedef struct {
    gz_alloc_block_t *blocks;
    gz_alloc_block_t *current;
    size_t block_size;
    size_t total_allocated;
    size_t total_allocations;
    size_t peak_usage;
    const char *label;
} gz_arena_t;

gz_arena_t *gz_arena_create(size_t block_size, const char *label);
void       *gz_arena_alloc(gz_arena_t *arena, size_t size);
void       *gz_arena_alloc_aligned(gz_arena_t *arena, size_t size, size_t alignment);
void       *gz_arena_calloc(gz_arena_t *arena, size_t count, size_t size);
void        gz_arena_reset(gz_arena_t *arena);
void        gz_arena_destroy(gz_arena_t *arena);
void        gz_arena_print_stats(const gz_arena_t *arena);

void *gz_aligned_alloc(size_t size, size_t alignment);
void  gz_aligned_free(void *ptr);

#endif
