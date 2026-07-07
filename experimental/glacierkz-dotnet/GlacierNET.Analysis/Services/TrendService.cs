using Microsoft.EntityFrameworkCore;
using GlacierNET.Analysis.Data;
using GlacierNET.Analysis.Models;

namespace GlacierNET.Analysis.Services;

public class TrendService
{
    private readonly GlacierDbContext _context;
    private readonly CacheService _cache;
    private readonly ILogger<TrendService> _logger;

    public TrendService(GlacierDbContext context, CacheService cache, ILogger<TrendService> logger)
    {
        _context = context;
        _cache = cache;
        _logger = logger;
    }

    public async Task<List<TrendData>> GetTrendDataAsync(
        Guid glacierId,
        AnalysisType analysisType,
        DateTime? startDate = null,
        DateTime? endDate = null)
    {
        IQueryable<TrendData> query = _context.TrendDataPoints
            .Where(t => t.GlacierId == glacierId && t.AnalysisType == analysisType)
            .AsNoTracking();

        if (startDate.HasValue) query = query.Where(t => t.MeasurementDate >= startDate.Value);
        if (endDate.HasValue) query = query.Where(t => t.MeasurementDate <= endDate.Value);

        return await query.OrderBy(t => t.MeasurementDate).ToListAsync();
    }

    public async Task<TrendData> AddTrendDataPointAsync(TrendData dataPoint)
    {
        dataPoint.Id = Guid.NewGuid();
        dataPoint.CreatedAt = DateTime.UtcNow;
        _context.TrendDataPoints.Add(dataPoint);
        await _context.SaveChangesAsync();
        await _cache.RemoveByPatternAsync($"trend:{dataPoint.GlacierId}:*");
        return dataPoint;
    }

    public async Task<List<TrendData>> AddTrendDataBatchAsync(List<TrendData> dataPoints)
    {
        foreach (var point in dataPoints)
        {
            point.Id = Guid.NewGuid();
            point.CreatedAt = DateTime.UtcNow;
        }
        _context.TrendDataPoints.AddRange(dataPoints);
        await _context.SaveChangesAsync();
        return dataPoints;
    }

    public async Task<TrendSummary> CalculateTrendSummaryAsync(Guid glacierId, AnalysisType type, int lookbackYears = 10)
    {
        var cacheKey = $"trend:{glacierId}:{type}:{lookbackYears}";
        var cached = await _cache.GetAsync<TrendSummary>(cacheKey);
        if (cached is not null) return cached;

        var startDate = DateTime.UtcNow.AddYears(-lookbackYears);
        var dataPoints = await _context.TrendDataPoints
            .Where(t => t.GlacierId == glacierId &&
                       t.AnalysisType == type &&
                       t.MeasurementDate >= startDate)
            .OrderBy(t => t.MeasurementDate)
            .AsNoTracking()
            .ToListAsync();

        if (dataPoints.Count < 2)
        {
            return new TrendSummary { GlacierId = glacierId, AnalysisType = type, DataPointCount = dataPoints.Count };
        }

        var values = dataPoints.Select(d => d.Value).ToList();
        var dates = dataPoints.Select(d => d.MeasurementDate).ToList();
        var n = values.Count;

        var mean = values.Average();
        var variance = values.Select(v => (v - mean) * (v - mean)).Average();
        var stdDev = Math.Sqrt(variance);

        var xMean = dates.Average(d => d.ToOADate());
        var yMean = mean;
        var sumXY = 0.0;
        var sumXX = 0.0;

        for (int i = 0; i < n; i++)
        {
            var xDiff = dates[i].ToOADate() - xMean;
            var yDiff = values[i] - yMean;
            sumXY += xDiff * yDiff;
            sumXX += xDiff * xDiff;
        }

        var slope = sumXX > 0 ? sumXY / sumXX : 0;
        var intercept = yMean - slope * xMean;

        var predicted = dates.Select(d => slope * d.ToOADate() + intercept).ToList();
        var ssRes = 0.0;
        var ssTot = 0.0;
        for (int i = 0; i < n; i++)
        {
            ssRes += (values[i] - predicted[i]) * (values[i] - predicted[i]);
            ssTot += (values[i] - yMean) * (values[i] - yMean);
        }
        var rSquared = ssTot > 0 ? 1.0 - (ssRes / ssTot) : 0;

        var yearOverYearChanges = new List<double>();
        for (int i = 1; i < n; i++)
        {
            var yearsDiff = (dates[i] - dates[i - 1]).TotalDays / 365.25;
            if (yearsDiff > 0)
                yearOverYearChanges.Add((values[i] - values[i - 1]) / yearsDiff);
        }

        var summary = new TrendSummary
        {
            GlacierId = glacierId,
            AnalysisType = type,
            DataPointCount = n,
            StartDate = dates.First(),
            EndDate = dates.Last(),
            MeanValue = mean,
            MinValue = values.Min(),
            MaxValue = values.Max(),
            StdDeviation = stdDev,
            LinearSlope = slope,
            LinearIntercept = intercept,
            RSquared = rSquared,
            TrendDirection = slope > 0.001 ? "Increasing" : slope < -0.001 ? "Decreasing" : "Stable",
            AnnualChangeRate = slope * 365.25,
            AverageYearOverYearChange = yearOverYearChanges.Count > 0 ? yearOverYearChanges.Average() : 0,
            FirstValue = values.First(),
            LastValue = values.Last(),
            TotalChange = values.Last() - values.First(),
            TotalChangePercent = Math.Abs(values.First()) > 0.001
                ? ((values.Last() - values.First()) / Math.Abs(values.First())) * 100
                : 0
        };

        await _cache.SetAsync(cacheKey, summary, TimeSpan.FromMinutes(30));
        return summary;
    }

    public async Task<List<TrendSummary>> GetAllGlacierTrendsAsync(AnalysisType type, int lookbackYears = 5)
    {
        var glacierIds = await _context.Glaciers
            .Where(g => g.IsActive)
            .Select(g => g.Id)
            .ToListAsync();

        var tasks = glacierIds.Select(id => CalculateTrendSummaryAsync(id, type, lookbackYears));
        return (await Task.WhenAll(tasks)).ToList();
    }

    public async Task<SeasonalPattern> DetectSeasonalPatternAsync(Guid glacierId, AnalysisType type)
    {
        var dataPoints = await _context.TrendDataPoints
            .Where(t => t.GlacierId == glacierId && t.AnalysisType == type)
            .AsNoTracking()
            .ToListAsync();

        var monthlyAverages = dataPoints
            .GroupBy(d => d.MeasurementDate.Month)
            .ToDictionary(
                g => g.Key,
                g => new MonthlyAverage
                {
                    Month = g.Key,
                    AverageValue = g.Average(d => d.Value),
                    StdDeviation = Math.Sqrt(g.Select(d => (d.Value - g.Average(x => x.Value)) * (d.Value - g.Average(x => x.Value))).Average()),
                    DataPointCount = g.Count()
                });

        var months = monthlyAverages.Values.ToList();
        var peakMonth = months.OrderByDescending(m => m.AverageValue).First();
        var troughMonth = months.OrderBy(m => m.AverageValue).First();

        var amplitude = peakMonth.AverageValue - troughMonth.AverageValue;

        return new SeasonalPattern
        {
            GlacierId = glacierId,
            AnalysisType = type,
            MonthlyAverages = monthlyAverages,
            PeakMonth = peakMonth.Month,
            TroughMonth = troughMonth.Month,
            Amplitude = amplitude,
            IsSeasonalPatternSignificant = amplitude > months.Average(m => m.StdDeviation) * 2,
            SeasonalStrength = amplitude / months.Average(m => m.StdDeviation)
        };
    }
}

public class TrendSummary
{
    public Guid GlacierId { get; set; }
    public AnalysisType AnalysisType { get; set; }
    public int DataPointCount { get; set; }
    public DateTime StartDate { get; set; }
    public DateTime EndDate { get; set; }
    public double MeanValue { get; set; }
    public double MinValue { get; set; }
    public double MaxValue { get; set; }
    public double StdDeviation { get; set; }
    public double LinearSlope { get; set; }
    public double LinearIntercept { get; set; }
    public double RSquared { get; set; }
    public string TrendDirection { get; set; } = string.Empty;
    public double AnnualChangeRate { get; set; }
    public double AverageYearOverYearChange { get; set; }
    public double FirstValue { get; set; }
    public double LastValue { get; set; }
    public double TotalChange { get; set; }
    public double TotalChangePercent { get; set; }
}

public class SeasonalPattern
{
    public Guid GlacierId { get; set; }
    public AnalysisType AnalysisType { get; set; }
    public Dictionary<int, MonthlyAverage> MonthlyAverages { get; set; } = new();
    public int PeakMonth { get; set; }
    public int TroughMonth { get; set; }
    public double Amplitude { get; set; }
    public bool IsSeasonalPatternSignificant { get; set; }
    public double SeasonalStrength { get; set; }
}

public class MonthlyAverage
{
    public int Month { get; set; }
    public double AverageValue { get; set; }
    public double StdDeviation { get; set; }
    public int DataPointCount { get; set; }
    public string MonthName => System.Globalization.CultureInfo.CurrentCulture.DateTimeFormat.GetMonthName(Month);
}
