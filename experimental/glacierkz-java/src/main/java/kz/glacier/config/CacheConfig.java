package kz.glacier.config;

import com.github.benmanes.caffeine.cache.Caffeine;
import org.springframework.cache.CacheManager;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.cache.caffeine.CaffeineCache;
import org.springframework.cache.support.SimpleCacheManager;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;
import java.util.concurrent.TimeUnit;

@Configuration
@EnableCaching
public class CacheConfig {

    @Bean
    public CacheManager cacheManager() {
        SimpleCacheManager cacheManager = new SimpleCacheManager();
        cacheManager.setCaches(List.of(
                buildCache("glacier-geometries", 5000, 30),
                buildCache("job-status", 2000, 5),
                buildCache("user-sessions", 1000, 60),
                buildCache("raster-metadata", 3000, 15),
                buildCache("report-cache", 500, 120),
                buildCache("satellite-images", 4000, 20),
                buildCache("analysis-results", 2000, 30),
                buildCache("geoserver-layers", 1000, 45)
        ));
        return cacheManager;
    }

    private CaffeineCache buildCache(String name, int maxSize, int ttlMinutes) {
        return new CaffeineCache(name, Caffeine.newBuilder()
                .maximumSize(maxSize)
                .expireAfterWrite(ttlMinutes, TimeUnit.MINUTES)
                .recordStats()
                .build());
    }
}
