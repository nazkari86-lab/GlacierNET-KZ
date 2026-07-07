#include <gtest/gtest.h>
#include "glacierkz_memory.h"
#include <string.h>

class MemoryTest : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

TEST_F(MemoryTest, ArenaCreateDestroy) {
    gz_arena_t arena;
    gz_status_t st = gz_arena_create(&arena, 4096);
    EXPECT_EQ(st, GZ_OK);

    gz_arena_destroy(&arena);
}

TEST_F(MemoryTest, ArenaAllocSimple) {
    gz_arena_t arena;
    gz_status_t st = gz_arena_create(&arena, 4096);
    EXPECT_EQ(st, GZ_OK);

    void *ptr = gz_arena_alloc(&arena, 64);
    EXPECT_NE(ptr, nullptr);

    gz_arena_destroy(&arena);
}

TEST_F(MemoryTest, ArenaAllocMultiple) {
    gz_arena_t arena;
    gz_status_t st = gz_arena_create(&arena, 4096);
    EXPECT_EQ(st, GZ_OK);

    void *p1 = gz_arena_alloc(&arena, 128);
    void *p2 = gz_arena_alloc(&arena, 256);
    void *p3 = gz_arena_alloc(&arena, 512);

    EXPECT_NE(p1, nullptr);
    EXPECT_NE(p2, nullptr);
    EXPECT_NE(p3, nullptr);
    EXPECT_NE(p1, p2);
    EXPECT_NE(p2, p3);

    gz_arena_destroy(&arena);
}

TEST_F(MemoryTest, ArenaReset) {
    gz_arena_t arena;
    gz_status_t st = gz_arena_create(&arena, 4096);
    EXPECT_EQ(st, GZ_OK);

    gz_arena_alloc(&arena, 128);
    gz_arena_alloc(&arena, 256);

    gz_arena_reset(&arena);

    void *p = gz_arena_alloc(&arena, 64);
    EXPECT_NE(p, nullptr);

    gz_arena_destroy(&arena);
}

TEST_F(MemoryTest, ArenaLargeAlloc) {
    gz_arena_t arena;
    gz_status_t st = gz_arena_create(&arena, 256);
    EXPECT_EQ(st, GZ_OK);

    void *p = gz_arena_alloc(&arena, 2048);
    EXPECT_NE(p, nullptr);

    gz_arena_destroy(&arena);
}

TEST_F(MemoryTest, PoolCreateDestroy) {
    gz_pool_t pool;
    gz_status_t st = gz_pool_create(&pool, 64, 16);
    EXPECT_EQ(st, GZ_OK);

    gz_pool_destroy(&pool);
}

TEST_F(MemoryTest, PoolAllocFree) {
    gz_pool_t pool;
    gz_status_t st = gz_pool_create(&pool, 64, 16);
    EXPECT_EQ(st, GZ_OK);

    void *ptr = gz_pool_alloc(&pool);
    EXPECT_NE(ptr, nullptr);

    gz_pool_free(&pool, ptr);

    gz_pool_destroy(&pool);
}

TEST_F(MemoryTest, PoolMultipleAlloc) {
    gz_pool_t pool;
    gz_status_t st = gz_pool_create(&pool, 64, 8);
    EXPECT_EQ(st, GZ_OK);

    void *ptrs[8];
    for (int i = 0; i < 8; i++) {
        ptrs[i] = gz_pool_alloc(&pool);
        EXPECT_NE(ptrs[i], nullptr);
    }

    for (int i = 0; i < 8; i++) {
        gz_pool_free(&pool, ptrs[i]);
    }

    gz_pool_destroy(&pool);
}

TEST_F(MemoryTest, PoolFreeNullSafe) {
    gz_pool_t pool;
    gz_status_t st = gz_pool_create(&pool, 64, 16);
    EXPECT_EQ(st, GZ_OK);

    gz_pool_free(&pool, NULL);

    gz_pool_destroy(&pool);
}

TEST_F(MemoryTest, ArenaAllocZeroSize) {
    gz_arena_t arena;
    gz_status_t st = gz_arena_create(&arena, 4096);
    EXPECT_EQ(st, GZ_OK);

    void *p = gz_arena_alloc(&arena, 0);
    EXPECT_EQ(p, nullptr);

    gz_arena_destroy(&arena);
}

TEST_F(MemoryTest, PoolCreateZeroSizeFails) {
    gz_pool_t pool;
    gz_status_t st = gz_pool_create(&pool, 0, 16);
    EXPECT_EQ(st, GZ_ERR_PARAM);
}

TEST_F(MemoryTest, PoolCreateZeroCountFails) {
    gz_pool_t pool;
    gz_status_t st = gz_pool_create(&pool, 64, 0);
    EXPECT_EQ(st, GZ_ERR_PARAM);
}

TEST_F(MemoryTest, ArenaDestroyNullSafe) {
    gz_arena_destroy(NULL);
}

TEST_F(MemoryTest, PoolDestroyNullSafe) {
    gz_pool_destroy(NULL);
}
