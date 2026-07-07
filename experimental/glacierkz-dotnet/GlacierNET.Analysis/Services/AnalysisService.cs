using Microsoft.EntityFrameworkCore;
using GlacierNET.Analysis.Data;
using GlacierNET.Analysis.Models;

namespace GlacierNET.Analysis.Services;

public class AnalysisService
{
    private readonly GlacierDbContext _context;
    private readonly CacheService _cache;
    private readonly ILogger<AnalysisService> _logger;

    public AnalysisService(GlacierDbContext context, CacheService cache, ILogger<AnalysisService> logger)
    {
        _context = context;
        _cache = cache;
        _logger = logger;
    }

    public async Task<List<AnalysisResult>> GetAnalysisResultsAsync(
        Guid? glacierId = null,
        AnalysisType? type = null,
        DateTime? from = null,
        DateTime? to = null,
        int page = 1,
        int pageSize = 50)
    {
        IQueryable<AnalysisResult> query = _context.AnalysisResults
            .Include(a => a.Glacier)
            .AsNoTracking();

        if (glacierId.HasValue) query = query.Where(a => a.GlacierId == glacierId.Value);
        if (type.HasValue) query = query.Where(a => a.AnalysisType == type.Value);
        if (from.HasValue) query = query.Where(a => a.AnalysisDate >= from.Value);
        if (to.HasValue) query = query.Where(a => a.AnalysisDate <= to.Value);

        return await query
            .OrderByDescending(a => a.AnalysisDate)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync();
    }

    public async Task<AnalysisResult> CreateAnalysisResultAsync(AnalysisResult result)
    {
        result.Id = Guid.NewGuid();
        result.CreatedAt = DateTime.UtcNow;

        if (result.PreviousValue.HasValue)
            result.ChangePercent = ((result.Value - result.PreviousValue.Value) / Math.Abs(result.PreviousValue.Value)) * 100;

        _context.AnalysisResults.Add(result);
        await _context.SaveChangesAsync();
        _logger.LogInformation("Created analysis result: {Type} for glacier {GlacierId}", result.AnalysisType, result.GlacierId);
        return result;
    }

    public async Task<List<AnalysisResult>> GetLatestAnalysisAsync(Guid glacierId, int count = 5)
    {
        return await _context.AnalysisResults
            .Where(a => a.GlacierId == glacierId)
            .OrderByDescending(a => a.AnalysisDate)
            .Take(count)
            .AsNoTracking()
            .ToListAsync();
    }

    public async Task<Dictionary<AnalysisType, AnalysisResult>> GetLatestByTypeAsync(Guid glacierId)
    {
        return await _context.AnalysisResults
            .Where(a => a.GlacierId == glacierId)
            .GroupBy(a => a.AnalysisType)
            .Select(g => g.OrderByDescending(a => a.AnalysisDate).First())
            .AsNoTracking()
            .ToDictionaryAsync(a => a.AnalysisType);
    }

    public async Task<List<AnalysisResult>> DetectAnomaliesAsync(Guid? glacierId = null, double thresholdStdDev = 2.0)
    {
        var recentResults = await _context.AnalysisResults
            .Where(a => (!glacierId.HasValue || a.GlacierId == glacierId.Value) && a.AnalysisDate >= DateTime.UtcNow.AddYears(-5))
            .AsNoTracking()
            .ToListAsync();

        var grouped = recentResults
            .GroupBy(a => new { a.GlacierId, a.AnalysisType })
            .Where(g => g.Count() > 5);

        var anomalies = new List<AnalysisResult>();
        foreach (var group in grouped)
        {
            var values = group.Select(a => a.Value).ToList();
            var mean = values.Average();
            var stdDev = Math.Sqrt(values.Select(v => (v - mean) * (v - mean)).Average());

            foreach (var result in group)
            {
                if (Math.Abs(result.Value - mean) > thresholdStdDev * stdDev)
                {
                    result.IsAnomaly = true;
                    result.AnomalySeverity = Math.Abs(result.Value - mean) > 3 * thresholdStdDev * stdDev
                        ? SeverityLevel.Critical
                        : SeverityLevel.Warning;
                    anomalies.Add(result);
                }
            }
        }

        _logger.LogInformation("Detected {Count} anomalies across {GlacierCount} glaciers",
            anomalies.Count,
            anomalies.Select(a => a.GlacierId).Distinct().Count());
        return anomalies;
    }

    public async Task<Dictionary<string, object>> GetAnalysisSummaryAsync()
    {
        var cached = await _cache.GetAsync<Dictionary<string, object>>("stats:analysis");
        if (cached is not null) return cached;

        var summary = new Dictionary<string, object>
        {
            ["totalAnalyses"] = await _context.AnalysisResults.CountAsync(),
            ["analysesThisMonth"] = await _context.AnalysisResults.CountAsync(a => a.AnalysisDate >= DateTime.UtcNow.AddMonths(-1)),
            ["anomalyCount"] = await _context.AnalysisResults.CountAsync(a => a.IsAnomaly),
            ["averageConfidence"] = await _context.AnalysisResults.AverageAsync(a => a.ConfidenceScore),
            ["byType"] = await _context.AnalysisResults
                .GroupBy(a => a.AnalysisType)
                .Select(x => new { Type = x.Key.ToString(), Count = x.Count() })
                .ToDictionaryAsync(x => x.Type, x => (object)x.Count),
            ["recentTrends"] = await _context.AnalysisResults
                .Where(a => a.AnalysisDate >= DateTime.UtcNow.AddMonths(-3))
                .GroupBy(a => a.AnalysisType)
                .Select(x => new
                {
                    Type = x.Key.ToString(),
                    AvgValue = x.Average(a => a.Value),
                    AvgConfidence = x.Average(a => a.ConfidenceScore)
                })
                .ToListAsync()
        };

        await _cache.SetAsync("stats:analysis", summary, TimeSpan.FromMinutes(15));
        return summary;
    }

    public async Task<List<AnalysisResult>> CompareGlaciersAsync(List<Guid> glacierIds, AnalysisType type, DateTime from, DateTime to)
    {
        return await _context.AnalysisResults
            .Where(a => glacierIds.Contains(a.GlacierId) &&
                        a.AnalysisType == type &&
                        a.AnalysisDate >= from &&
                        a.AnalysisDate <= to)
            .Include(a => a.Glacier)
            .OrderBy(a => a.AnalysisDate)
            .AsNoTracking()
            .ToListAsync();
    }

    public async Task<double> CalculateMassBalanceTrendAsync(Guid glacierId, int years = 10)
    {
        var startDate = DateTime.UtcNow.AddYears(-years);
        var values = await _context.TrendDataPoints
            .Where(t => t.GlacierId == glacierId &&
                       t.AnalysisType == AnalysisType.MassBalance &&
                       t.MeasurementDate >= startDate)
            .OrderBy(t => t.MeasurementDate)
            .Select(t => t.Value)
            .ToListAsync();

        if (values.Count < 2) return 0;

        var n = values.Count;
        var xMean = (n - 1) / 2.0;
        var yMean = values.Average();
        var sumXY = 0.0;
        var sumXX = 0.0;

        for (int i = 0; i < n; i++)
        {
            sumXY += (i - xMean) * (values[i] - yMean);
            sumXX += (i - xMean) * (i - xMean);
        }

        return sumXX > 0 ? sumXY / sumXX : 0;
    }
}
