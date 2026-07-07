#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>
#include <list>
#include <unordered_map>
#include <mutex>
#include <condition_variable>
#include <functional>
#include <future>
#include <atomic>
#include <memory>
#include <optional>

namespace glacierkz {

struct TileKey {
    int level;
    int col;
    int row;

    bool operator==(const TileKey& other) const {
        return level == other.level && col == other.col && row == other.row;
    }
};

struct TileKeyHash {
    size_t operator()(const TileKey& k) const {
        size_t h1 = std::hash<int>()(k.level);
        size_t h2 = std::hash<int>()(k.col);
        size_t h3 = std::hash<int>()(k.row);
        return h1 ^ (h2 << 1) ^ (h3 << 2);
    }
};

struct TileData {
    std::vector<float> pixels;
    int width = 0;
    int height = 0;
    int channels = 1;
    size_t memory_bytes() const {
        return pixels.size() * sizeof(float);
    }
};

using TileLoader = std::function<TileData(const TileKey& key)>;

class LRUCache {
public:
    explicit LRUCache(size_t max_memory_bytes);
    ~LRUCache();

    void put(const TileKey& key, TileData tile);
    std::optional<TileData> get(const TileKey& key);
    bool contains(const TileKey& key) const;
    void remove(const TileKey& key);
    void clear();

    size_t current_memory() const;
    size_t max_memory() const;
    size_t size() const;
    size_t hit_count() const;
    size_t miss_count() const;
    void reset_stats();

    std::vector<TileKey> keys() const;

private:
    struct CacheEntry {
        TileKey key;
        TileData data;
    };

    mutable std::mutex mutex_;
    size_t max_memory_;
    std::atomic<size_t> current_memory_{0};
    std::list<CacheEntry> lru_list_;
    std::unordered_map<TileKey, std::list<CacheEntry>::iterator, TileKeyHash> lookup_;
    std::atomic<size_t> hit_count_{0};
    std::atomic<size_t> miss_count_{0};

    void evict();
    void touch(std::list<CacheEntry>::iterator it);
};

class AsyncTileCache {
public:
    AsyncTileCache(size_t max_memory_bytes, size_t num_loader_threads = 2);
    ~AsyncTileCache();

    std::future<TileData> load_async(const TileKey& key, TileLoader loader);
    std::optional<TileData> get(const TileKey& key);

    void cancel_pending();
    size_t pending_count() const;
    size_t loaded_count() const;

    const LRUCache& cache() const { return cache_; }

private:
    LRUCache cache_;
    std::vector<std::thread> loader_threads_;
    std::mutex queue_mutex_;
    std::condition_variable queue_cv_;
    std::atomic<bool> shutdown_{false};
    std::atomic<size_t> pending_count_{0};
    std::atomic<size_t> loaded_count_{0};

    struct LoadRequest {
        TileKey key;
        TileLoader loader;
        std::promise<TileData> promise;
    };

    std::list<LoadRequest> request_queue_;
    void loader_worker();
};

} // namespace glacierkz
