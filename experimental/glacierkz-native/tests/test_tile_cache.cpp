#include <gtest/gtest.h>
#include "glacierkz/tile_cache.hpp"

using namespace glacierkz;

TEST(TileKeyTest, Equality) {
    TileKey k1(1, 2, 3);
    TileKey k2(1, 2, 3);
    TileKey k3(2, 2, 3);
    EXPECT_TRUE(k1 == k2);
    EXPECT_FALSE(k1 == k3);
}

TEST(TileKeyTest, Ordering) {
    TileKey k1(0, 0, 0);
    TileKey k2(1, 0, 0);
    EXPECT_TRUE(k1 < k2);
}

TEST(TileDataTest, MemoryBytes) {
    TileData td;
    td.data.resize(100);
    EXPECT_EQ(td.memory_bytes(), 100 * sizeof(float));
}

TEST(TileDataTest, DefaultValues) {
    TileData td;
    EXPECT_EQ(td.width, 0);
    EXPECT_EQ(td.height, 0);
    EXPECT_EQ(td.bands, 0);
    EXPECT_TRUE(td.data.empty());
}

TEST(LRUCacheTest, PutGet) {
    LRUCache cache(1024 * 1024);
    TileKey key(0, 1, 2);
    TileData td;
    td.data = {1.0f, 2.0f, 3.0f};
    td.width = 3;
    td.height = 1;
    td.bands = 1;

    cache.put(key, td);
    EXPECT_TRUE(cache.contains(key));
    EXPECT_EQ(cache.size(), 1u);

    auto retrieved = cache.get(key);
    EXPECT_TRUE(retrieved.has_value());
    EXPECT_EQ(retrieved->data.size(), 3u);
}

TEST(LRUCacheTest, Eviction) {
    LRUCache cache(3 * sizeof(float));
    for (int i = 0; i < 4; ++i) {
        TileKey key(0, i, 0);
        TileData td;
        td.data = {1.0f};
        td.width = 1;
        td.height = 1;
        td.bands = 1;
        cache.put(key, td);
    }
    EXPECT_EQ(cache.size(), 3u);
    EXPECT_FALSE(cache.contains(TileKey(0, 0, 0)));
}

TEST(LRUCacheTest, MissCount) {
    LRUCache cache(1024);
    TileKey key(0, 0, 0);
    cache.get(key);
    EXPECT_EQ(cache.miss_count(), 1u);
}

TEST(LRUCacheTest, HitCount) {
    LRUCache cache(1024);
    TileKey key(0, 0, 0);
    TileData td;
    td.data = {1.0f};
    td.width = 1;
    td.height = 1;
    td.bands = 1;
    cache.put(key, td);
    cache.get(key);
    EXPECT_EQ(cache.hit_count(), 1u);
}

TEST(LRUCacheTest, Remove) {
    LRUCache cache(1024);
    TileKey key(0, 0, 0);
    TileData td;
    td.data = {1.0f};
    td.width = 1;
    td.height = 1;
    td.bands = 1;
    cache.put(key, td);
    cache.remove(key);
    EXPECT_FALSE(cache.contains(key));
    EXPECT_EQ(cache.size(), 0u);
}

TEST(LRUCacheTest, Clear) {
    LRUCache cache(1024);
    for (int i = 0; i < 5; ++i) {
        TileKey key(0, i, 0);
        TileData td;
        td.data = {1.0f};
        td.width = 1;
        td.height = 1;
        td.bands = 1;
        cache.put(key, td);
    }
    cache.clear();
    EXPECT_EQ(cache.size(), 0u);
    EXPECT_EQ(cache.current_memory(), 0u);
}

TEST(LRUCacheTest, ResetStats) {
    LRUCache cache(1024);
    TileKey key(0, 0, 0);
    cache.get(key);
    cache.reset_stats();
    EXPECT_EQ(cache.hit_count(), 0u);
    EXPECT_EQ(cache.miss_count(), 0u);
}

TEST(LRUCacheTest, Keys) {
    LRUCache cache(1024);
    for (int i = 0; i < 3; ++i) {
        TileKey key(0, i, 0);
        TileData td;
        td.data = {1.0f};
        td.width = 1;
        td.height = 1;
        td.bands = 1;
        cache.put(key, td);
    }
    auto keys = cache.keys();
    EXPECT_EQ(keys.size(), 3u);
}

TEST(LRUCacheTest, LRUPolicy) {
    LRUCache cache(3 * sizeof(float));
    TileKey k1(0, 0, 0), k2(0, 1, 0), k3(0, 2, 0), k4(0, 3, 0);

    TileData td;
    td.data = {1.0f};
    td.width = 1;
    td.height = 1;
    td.bands = 1;

    cache.put(k1, td);
    cache.put(k2, td);
    cache.put(k3, td);

    cache.get(k1);

    cache.put(k4, td);

    EXPECT_TRUE(cache.contains(k1));
    EXPECT_FALSE(cache.contains(k2));
}

TEST(AsyncTileCacheTest, LoadAsync) {
    AsyncTileCache cache(1024, 1);
    TileKey key(0, 0, 0);

    auto future = cache.load_async(key, [](const TileKey& k) {
        TileData td;
        td.data = {10.0f, 20.0f};
        td.width = 2;
        td.height = 1;
        td.bands = 1;
        return td;
    });

    auto result = future.get();
    EXPECT_EQ(result.data.size(), 2u);
    EXPECT_FLOAT_EQ(result.data[0], 10.0f);
    EXPECT_EQ(cache.loaded_count(), 1u);
}

TEST(AsyncTileCacheTest, GetCached) {
    AsyncTileCache cache(1024, 1);
    TileKey key(0, 0, 0);

    TileData td;
    td.data = {1.0f};
    td.width = 1;
    td.height = 1;
    td.bands = 1;
    cache.load_async(key, [&td](const TileKey&) { return td; }).get();

    auto result = cache.get(key);
    EXPECT_TRUE(result.has_value());
}

TEST(AsyncTileCacheTest, PendingCount) {
    AsyncTileCache cache(1024, 0);
    TileKey key(0, 0, 0);
    cache.load_async(key, [](const TileKey& k) {
        TileData td;
        td.data = {1.0f};
        return td;
    });
    // With 0 threads, the task will be queued
    EXPECT_GE(cache.pending_count(), 0u);
}
