using System.Text.Json;
using Microsoft.Extensions.Caching.Distributed;

namespace GlacierNET.Analysis.Services;

public class CacheService
{
    private readonly IDistributedCache _cache;
    private readonly ILogger<CacheService> _logger;

    public CacheService(IDistributedCache cache, ILogger<CacheService> logger)
    {
        _cache = cache;
        _logger = logger;
    }

    public async Task<T?> GetAsync<T>(string key) where T : class
    {
        try
        {
            var bytes = await _cache.GetAsync(key);
            if (bytes is null) return null;
            var json = System.Text.Encoding.UTF8.GetString(bytes);
            return JsonSerializer.Deserialize<T>(json);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Cache get failed for key {Key}", key);
            return null;
        }
    }

    public async Task SetAsync<T>(string key, T value, TimeSpan? expiry = null) where T : class
    {
        try
        {
            var json = JsonSerializer.Serialize(value);
            var bytes = System.Text.Encoding.UTF8.GetBytes(json);
            var options = new DistributedCacheEntryOptions
            {
                AbsoluteExpirationRelativeToNow = expiry ?? TimeSpan.FromMinutes(5),
                SlidingExpiration = TimeSpan.FromMinutes(2)
            };
            await _cache.SetAsync(key, bytes, options);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Cache set failed for key {Key}", key);
        }
    }

    public async Task RemoveAsync(string key)
    {
        try
        {
            await _cache.RemoveAsync(key);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Cache remove failed for key {Key}", key);
        }
    }

    public async Task RemoveByPatternAsync(string pattern)
    {
        try
        {
            if (_cache is Microsoft.Extensions.Caching.Distributed.DistributedCacheExtensions cache)
            {
                _logger.LogDebug("Cache pattern removal requested: {Pattern}", pattern);
            }
            await Task.CompletedTask;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Cache pattern removal failed for {Pattern}", pattern);
        }
    }

    public async Task<T> GetOrCreateAsync<T>(string key, Func<Task<T>> factory, TimeSpan? expiry = null) where T : class
    {
        var cached = await GetAsync<T>(key);
        if (cached is not null) return cached;

        var value = await factory();
        await SetAsync(key, value, expiry);
        return value;
    }

    public async Task ClearAllAsync()
    {
        try
        {
            _logger.LogWarning("Full cache clear requested");
            await Task.CompletedTask;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to clear cache");
        }
    }
}
