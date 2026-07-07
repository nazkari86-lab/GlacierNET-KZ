#include "glacierkz/tile_cache.hpp"

#include <algorithm>
#include <stdexcept>
#include <spdlog/spdlog.h>

namespace glacierkz {

LRUCache::LRUCache(size_t max_memory_bytes)
    : max_memory_(max_memory_bytes) {}

LRUCache::~LRUCache() {
    clear();
}

void LRUCache::put(const TileKey& key, TileData tile) {
    std::lock_guard lock(mutex_);

    auto it = lookup_.find(key);
    if (it != lookup_.end()) {
        current_memory_ -= it->second->data.memory_bytes();
        lru_list_.erase(it->second);
        lookup_.erase(it);
    }

    while (current_memory_ + tile.memory_bytes() > max_memory_ && !lru_list_.empty()) {
        evict();
    }

    CacheEntry entry{key, std::move(tile)};
    lru_list_.push_front(std::move(entry));
    auto front_it = lru_list_.begin();
    current_memory_ += front_it->data.memory_bytes();
    lookup_[key] = front_it;
}

std::optional<TileData> LRUCache::get(const TileKey& key) {
    std::lock_guard lock(mutex_);

    auto it = lookup_.find(key);
    if (it == lookup_.end()) {
        miss_count_.fetch_add(1, std::memory_order_relaxed);
        return std::nullopt;
    }

    hit_count_.fetch_add(1, std::memory_order_relaxed);
    touch(it->second);
    return it->second->data;
}

bool LRUCache::contains(const TileKey& key) const {
    std::lock_guard lock(mutex_);
    return lookup_.find(key) != lookup_.end();
}

void LRUCache::remove(const TileKey& key) {
    std::lock_guard lock(mutex_);

    auto it = lookup_.find(key);
    if (it != lookup_.end()) {
        current_memory_ -= it->second->data.memory_bytes();
        lru_list_.erase(it->second);
        lookup_.erase(it);
    }
}

void LRUCache::clear() {
    std::lock_guard lock(mutex_);
    lru_list_.clear();
    lookup_.clear();
    current_memory_ = 0;
}

size_t LRUCache::current_memory() const {
    return current_memory_.load(std::memory_order_relaxed);
}

size_t LRUCache::max_memory() const {
    return max_memory_;
}

size_t LRUCache::size() const {
    std::lock_guard lock(mutex_);
    return lookup_.size();
}

size_t LRUCache::hit_count() const {
    return hit_count_.load(std::memory_order_relaxed);
}

size_t LRUCache::miss_count() const {
    return miss_count_.load(std::memory_order_relaxed);
}

void LRUCache::reset_stats() {
    hit_count_ = 0;
    miss_count_ = 0;
}

std::vector<TileKey> LRUCache::keys() const {
    std::lock_guard lock(mutex_);
    std::vector<TileKey> result;
    result.reserve(lookup_.size());
    for (const auto& [key, _] : lookup_) {
        result.push_back(key);
    }
    return result;
}

void LRUCache::evict() {
    if (lru_list_.empty()) return;

    auto& back = lru_list_.back();
    current_memory_ -= back.data.memory_bytes();
    lookup_.erase(back.key);
    lru_list_.pop_back();

    spdlog::debug("Evicted tile ({},{},{})", back.key.level, back.key.col, back.key.row);
}

void LRUCache::touch(std::list<CacheEntry>::iterator it) {
    if (it == lru_list_.begin()) return;
    lru_list_.splice(lru_list_.begin(), lru_list_, it);
}

AsyncTileCache::AsyncTileCache(size_t max_memory_bytes, size_t num_loader_threads)
    : cache_(max_memory_bytes) {
    for (size_t i = 0; i < num_loader_threads; ++i) {
        loader_threads_.emplace_back(&AsyncTileCache::loader_worker, this);
    }
}

AsyncTileCache::~AsyncTileCache() {
    cancel_pending();
    shutdown_ = true;
    queue_cv_.notify_all();
    for (auto& t : loader_threads_) {
        if (t.joinable()) t.join();
    }
}

std::future<TileData> AsyncTileCache::load_async(const TileKey& key,
                                                    TileLoader loader) {
    auto cached = cache_.get(key);
    if (cached.has_value()) {
        std::promise<TileData> promise;
        promise.set_value(std::move(cached.value()));
        return promise.get_future();
    }

    {
        std::lock_guard lock(queue_mutex_);
        request_queue_.emplace_back(LoadRequest{key, std::move(loader),
                                                 std::promise<TileData>()});
    }

    pending_count_.fetch_add(1, std::memory_order_relaxed);
    auto& back = request_queue_.back();
    auto future = back.promise.get_future();

    queue_cv_.notify_one();
    return future;
}

std::optional<TileData> AsyncTileCache::get(const TileKey& key) {
    return cache_.get(key);
}

void AsyncTileCache::cancel_pending() {
    std::lock_guard lock(queue_mutex_);
    for (auto& req : request_queue_) {
        try {
            req.promise.set_exception(
                std::make_exception_ptr(std::runtime_error("Cancelled")));
        } catch (...) {}
    }
    request_queue_.clear();
    pending_count_ = 0;
}

size_t AsyncTileCache::pending_count() const {
    return pending_count_.load(std::memory_order_relaxed);
}

size_t AsyncTileCache::loaded_count() const {
    return loaded_count_.load(std::memory_order_relaxed);
}

void AsyncTileCache::loader_worker() {
    while (!shutdown_) {
        LoadRequest request;
        {
            std::unique_lock lock(queue_mutex_);
            queue_cv_.wait(lock, [this] {
                return !request_queue_.empty() || shutdown_;
            });

            if (shutdown_ && request_queue_.empty()) return;
            if (request_queue_.empty()) continue;

            request = std::move(request_queue_.front());
            request_queue_.pop_front();
        }

        try {
            TileData data = request.loader(request.key);
            cache_.put(request.key, data);
            request.promise.set_value(std::move(data));
            loaded_count_.fetch_add(1, std::memory_order_relaxed);
        } catch (const std::exception& e) {
            spdlog::error("Tile load failed ({},{},{}): {}",
                         request.key.level, request.key.col, request.key.row, e.what());
            try {
                request.promise.set_exception(std::current_exception());
            } catch (...) {}
        }

        pending_count_.fetch_sub(1, std::memory_order_relaxed);
    }
}

} // namespace glacierkz
