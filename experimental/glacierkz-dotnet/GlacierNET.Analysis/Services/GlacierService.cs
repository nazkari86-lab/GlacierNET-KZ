using Microsoft.EntityFrameworkCore;
using NetTopologySuite.Geometries;
using GlacierNET.Analysis.Data;
using GlacierNET.Analysis.Models;

namespace GlacierNET.Analysis.Services;

public class GlacierService
{
    private readonly GlacierDbContext _context;
    private readonly CacheService _cache;
    private readonly ILogger<GlacierService> _logger;

    public GlacierService(GlacierDbContext context, CacheService cache, ILogger<GlacierService> logger)
    {
        _context = context;
        _cache = cache;
        _logger = logger;
    }

    public async Task<List<Glacier>> GetAllGlaciersAsync(int page = 1, int pageSize = 25, string? sortBy = null, bool descending = false)
    {
        var cacheKey = $"glaciers:list:{page}:{pageSize}:{sortBy}:{descending}";
        var cached = await _cache.GetAsync<List<Glacier>>(cacheKey);
        if (cached is not null) return cached;

        IQueryable<Glacier> query = _context.Glaciers
            .Where(g => g.IsActive)
            .Include(g => g.AnalysisResults)
            .Include(g => g.TrendDataPoints);

        query = sortBy?.ToLower() switch
        {
            "name" => descending ? query.OrderByDescending(g => g.Name) : query.OrderBy(g => g.Name),
            "area" => descending ? query.OrderByDescending(g => g.AreaKm2) : query.OrderBy(g => g.AreaKm2),
            "elevation" => descending ? query.OrderByDescending(g => g.ElevationMean) : query.OrderBy(g => g.ElevationMean),
            "status" => descending ? query.OrderByDescending(g => g.Status) : query.OrderBy(g => g.Status),
            "region" => descending ? query.OrderByDescending(g => g.Region) : query.OrderBy(g => g.Region),
            "created" => descending ? query.OrderByDescending(g => g.CreatedAt) : query.OrderBy(g => g.CreatedAt),
            _ => query.OrderBy(g => g.Name)
        };

        var result = await query
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .AsNoTracking()
            .ToListAsync();

        await _cache.SetAsync(cacheKey, result, TimeSpan.FromMinutes(5));
        return result;
    }

    public async Task<Glacier?> GetGlacierByIdAsync(Guid id)
    {
        var cacheKey = $"glacier:{id}";
        var cached = await _cache.GetAsync<Glacier>(cacheKey);
        if (cached is not null) return cached;

        var glacier = await _context.Glaciers
            .Include(g => g.SatelliteImages.OrderByDescending(s => s.CaptureDate).Take(10))
            .Include(g => g.AnalysisResults.OrderByDescending(a => a.AnalysisDate).Take(20))
            .Include(g => g.TrendDataPoints.OrderByDescending(t => t.MeasurementDate).Take(100))
            .AsNoTracking()
            .FirstOrDefaultAsync(g => g.Id == id);

        if (glacier is not null)
            await _cache.SetAsync(cacheKey, glacier, TimeSpan.FromMinutes(10));

        return glacier;
    }

    public async Task<Glacier> CreateGlacierAsync(Glacier glacier)
    {
        glacier.Id = Guid.NewGuid();
        glacier.CreatedAt = DateTime.UtcNow;
        glacier.UpdatedAt = DateTime.UtcNow;
        glacier.IsActive = true;

        _context.Glaciers.Add(glacier);
        await _context.SaveChangesAsync();
        await _cache.RemoveByPatternAsync("glaciers:*");
        _logger.LogInformation("Created glacier {Name} in {Region}", glacier.Name, glacier.Region);
        return glacier;
    }

    public async Task<Glacier?> UpdateGlacierAsync(Guid id, Glacier updated)
    {
        var existing = await _context.Glaciers.FindAsync(id);
        if (existing is null) return null;

        existing.Name = updated.Name;
        existing.LocalName = updated.LocalName;
        existing.Region = updated.Region;
        existing.Country = updated.Country;
        existing.MountainRange = updated.MountainRange;
        existing.ElevationMin = updated.ElevationMin;
        existing.ElevationMax = updated.ElevationMax;
        existing.ElevationMean = updated.ElevationMean;
        existing.AreaKm2 = updated.AreaKm2;
        existing.LengthKm = updated.LengthKm;
        existing.Orientation = updated.Orientation;
        existing.Status = updated.Status;
        existing.Geometry = updated.Geometry;
        existing.CenterPoint = updated.CenterPoint;
        existing.Description = updated.Description;
        existing.DiscoveredDate = updated.DiscoveredDate;
        existing.FirstSurveyDate = updated.FirstSurveyDate;
        existing.UpdatedAt = DateTime.UtcNow;

        await _context.SaveChangesAsync();
        await _cache.RemoveByPatternAsync("glacier:*");
        _logger.LogInformation("Updated glacier {Id}", id);
        return existing;
    }

    public async Task<bool> DeleteGlacierAsync(Guid id)
    {
        var glacier = await _context.Glaciers.FindAsync(id);
        if (glacier is null) return false;

        glacier.IsActive = false;
        glacier.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();
        await _cache.RemoveByPatternAsync("glacier:*");
        _logger.LogInformation("Soft-deleted glacier {Id}", id);
        return true;
    }

    public async Task<List<Glacier>> SearchGlaciersAsync(string query, int maxResults = 20)
    {
        return await _context.Glaciers
            .Where(g => g.IsActive &&
                (g.Name.Contains(query) ||
                 g.Region.Contains(query) ||
                 (g.LocalName != null && g.LocalName.Contains(query)) ||
                 (g.MountainRange != null && g.MountainRange.Contains(query))))
            .OrderBy(g => g.Name)
            .Take(maxResults)
            .AsNoTracking()
            .ToListAsync();
    }

    public async Task<List<Glacier>> GetGlaciersInBoundingBoxAsync(double minLat, double maxLat, double minLon, double maxLon)
    {
        var geometryFactory = new GeometryFactory(new PrecisionModel(), 4326);
        var envelope = new Envelope(minLon, maxLon, minLat, maxLat);
        var searchGeom = geometryFactory.ToGeometry(envelope);

        return await _context.Glaciers
            .Where(g => g.IsActive && g.Geometry != null && g.Geometry.Intersects(searchGeom))
            .AsNoTracking()
            .ToListAsync();
    }

    public async Task<List<Glacier>> GetGlaciersNearPointAsync(double latitude, double longitude, double radiusKm = 50)
    {
        var point = new Point(longitude, latitude) { SRID = 4326 };
        return await _context.Glaciers
            .Where(g => g.IsActive && g.CenterPoint != null &&
                g.CenterPoint.Distance(point) <= radiusKm / 111.32)
            .OrderBy(g => g.CenterPoint!.Distance(point))
            .AsNoTracking()
            .ToListAsync();
    }

    public async Task<List<Glacier>> GetGlaciersByStatusAsync(GlacierStatus status)
    {
        return await _context.Glaciers
            .Where(g => g.IsActive && g.Status == status)
            .OrderBy(g => g.Name)
            .AsNoTracking()
            .ToListAsync();
    }

    public async Task<Dictionary<string, object>> GetGlacierStatisticsAsync()
    {
        var cached = await _cache.GetAsync<Dictionary<string, object>>("stats:glaciers");
        if (cached is not null) return cached;

        var stats = new Dictionary<string, object>
        {
            ["totalGlaciers"] = await _context.Glaciers.CountAsync(g => g.IsActive),
            ["totalAreaKm2"] = await _context.Glaciers.Where(g => g.IsActive).SumAsync(g => g.AreaKm2),
            ["averageAreaKm2"] = await _context.Glaciers.Where(g => g.IsActive).AverageAsync(g => g.AreaKm2),
            ["averageElevation"] = await _context.Glaciers.Where(g => g.IsActive).AverageAsync(g => g.ElevationMean),
            ["retreatingCount"] = await _context.Glaciers.CountAsync(g => g.IsActive && g.Status == GlacierStatus.Retreating),
            ["stableCount"] = await _context.Glaciers.CountAsync(g => g.IsActive && g.Status == GlacierStatus.Stable),
            ["activeCount"] = await _context.Glaciers.CountAsync(g => g.IsActive && g.Status == GlacierStatus.Active),
            ["byRegion"] = await _context.Glaciers
                .Where(g => g.IsActive)
                .GroupBy(g => g.Region)
                .Select(x => new { Region = x.Key, Count = x.Count(), TotalArea = x.Sum(g => g.AreaKm2) })
                .ToDictionaryAsync(x => x.Region, x => (object)new { x.Count, x.TotalArea })
        };

        await _cache.SetAsync("stats:glaciers", stats, TimeSpan.FromMinutes(15));
        return stats;
    }

    public async Task<int> GetGlacierCountAsync()
    {
        return await _context.Glaciers.CountAsync(g => g.IsActive);
    }
}
