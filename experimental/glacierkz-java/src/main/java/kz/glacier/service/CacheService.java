package kz.glacier.service;

import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.CacheManager;
import org.springframework.cache.caffeine.CaffeineCache;
import org.springframework.stereotype.Service;

import java.util.Collection;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

@Service
@Slf4j
public class CacheService {

    private final CacheManager cacheManager;
    private final Map<String, Cache<Object, Object>> localCaches = new ConcurrentHashMap<>();

    public CacheService(CacheManager cacheManager) {
        this.cacheManager = cacheManager;
    }

    public void evict(String cacheName, Object key) {
        org.springframework.cache.Cache cache = cacheManager.getCache(cacheName);
        if (cache != null) {
            cache.evict(key);
            log.debug("Evicted key={} from cache={}", key, cacheName);
        }
    }

    public void evictAll(String cacheName) {
        org.springframework.cache.Cache cache = cacheManager.getCache(cacheName);
        if (cache != null) {
            cache.clear();
            log.info("Cleared all entries from cache={}", cacheName);
        }
    }

    public void evictAllCaches() {
        cacheManager.getCacheNames().forEach(name -> {
            org.springframework.cache.Cache cache = cacheManager.getCache(name);
            if (cache != null) {
                cache.clear();
            }
        });
        log.info("Cleared all caches");
    }

    public Map<String, Object> getCacheStats() {
        Map<String, Object> stats = new ConcurrentHashMap<>();
        cacheManager.getCacheNames().forEach(name -> {
            org.springframework.cache.Cache cache = cacheManager.getCache(name);
            if (cache instanceof CaffeineCache caffeineCache) {
                Cache<Object, Object> nativeCache = caffeineCache.getNativeCache();
                stats.put(name, Map.of(
                        "size", nativeCache.estimatedSize(),
                        "hitRate", nativeCache.stats().hitRate(),
                        "missCount", nativeCache.stats().missCount()
                ));
            } else {
                stats.put(name, Map.of("type", cache != null ? cache.getClass().getSimpleName() : "null"));
            }
        });
        return stats;
    }

    public boolean hasKey(String cacheName, Object key) {
        org.springframework.cache.Cache cache = cacheManager.getCache(cacheName);
        if (cache != null) {
            org.springframework.cache.Cache.ValueWrapper wrapper = cache.get(key);
            return wrapper != null;
        }
        return false;
    }

    public Object get(String cacheName, Object key) {
        org.springframework.cache.Cache cache = cacheManager.getCache(cacheName);
        if (cache != null) {
            org.springframework.cache.Cache.ValueWrapper wrapper = cache.get(key);
            return wrapper != null ? wrapper.get() : null;
        }
        return null;
    }

    public void put(String cacheName, Object key, Object value) {
        org.springframework.cache.Cache cache = cacheManager.getCache(cacheName);
        if (cache != null) {
            cache.put(key, value);
            log.debug("Put key={} into cache={}", key, cacheName);
        }
    }

    public long getCacheSize(String cacheName) {
        org.springframework.cache.Cache cache = cacheManager.getCache(cacheName);
        if (cache instanceof CaffeineCache caffeineCache) {
            Cache<Object, Object> nativeCache = caffeineCache.getNativeCache();
            return nativeCache.estimatedSize();
        }
        return 0;
    }

    public void warmCache(String cacheName) {
        log.info("Warming cache: {}", cacheName);
        org.springframework.cache.Cache cache = cacheManager.getCache(cacheName);
        if (cache != null) {
            cache.get("warmup-key");
            log.info("Cache warmup completed: {}", cacheName);
        }
    }

    public void warmAllCaches() {
        cacheManager.getCacheNames().forEach(this::warmCache);
        log.info("All caches warmed up");
    }
}
