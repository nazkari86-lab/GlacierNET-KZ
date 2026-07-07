using FluentAssertions;
using GlacierNET.Analysis.Data;
using GlacierNET.Analysis.Models;
using GlacierNET.Analysis.Services;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Caching.Distributed;
using Microsoft.Extensions.Logging;
using Moq;
using Xunit;

namespace GlacierNET.Tests;

public class AnalysisServiceTests
{
    private readonly GlacierDbContext _dbContext;
    private readonly Mock<IDistributedCache> _cacheMock;
    private readonly Mock<ILogger<AnalysisService>> _loggerMock;
    private readonly AnalysisService _service;

    public AnalysisServiceTests()
    {
        var options = new DbContextOptionsBuilder<GlacierDbContext>()
            .UseInMemoryDatabase(databaseName: Guid.NewGuid().ToString())
            .Options;
        _dbContext = new GlacierDbContext(options);

        _cacheMock = new Mock<IDistributedCache>();
        _loggerMock = new Mock<ILogger<AnalysisService>>();

        var cacheServiceMock = new Mock<CacheService>(
            Mock.Of<IDistributedCache>(),
            Mock.Of<ILogger<CacheService>>());

        _service = new AnalysisService(_dbContext, cacheServiceMock.Object, _loggerMock.Object);
        SeedTestData();
    }

    private void SeedTestData()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");

        if (!_dbContext.Glaciers.Any())
        {
            _dbContext.Glaciers.Add(new Glacier
            {
                Id = glacierId,
                Name = "Petrov Glacier",
                Region = "Tien Shan",
                AreaKm2 = 45.2,
                Latitude = 42.5,
                Longitude = 75.3,
                Elevation = 4200,
                IsActive = true,
                CreatedAt = DateTime.UtcNow
            });
        }

        if (!_dbContext.AnalysisResults.Any())
        {
            _dbContext.AnalysisResults.AddRange(
                new AnalysisResult
                {
                    Id = Guid.NewGuid(),
                    GlacierId = glacierId,
                    AnalysisType = "MassBalance",
                    Result = -1.25,
                    IsAnomaly = false,
                    AnomalyScore = 1.5,
                    AnalysisDate = DateTime.UtcNow.AddDays(-30)
                },
                new AnalysisResult
                {
                    Id = Guid.NewGuid(),
                    GlacierId = glacierId,
                    AnalysisType = "AreaChange",
                    Result = -0.05,
                    IsAnomaly = true,
                    AnomalyScore = 2.8,
                    AnalysisDate = DateTime.UtcNow.AddDays(-15)
                },
                new AnalysisResult
                {
                    Id = Guid.NewGuid(),
                    GlacierId = glacierId,
                    AnalysisType = "Velocity",
                    Result = 0.023,
                    IsAnomaly = false,
                    AnomalyScore = 1.1,
                    AnalysisDate = DateTime.UtcNow.AddDays(-7)
                }
            );
        }

        _dbContext.SaveChanges();
    }

    [Fact]
    public async Task GetAnalysisResultsByGlacierIdAsync_ReturnsResults_ForValidGlacierId()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");

        var results = await _service.GetAnalysisResultsByGlacierIdAsync(glacierId);

        results.Should().NotBeNull();
        results.Should().HaveCount(3);
        results.Should().Contain(r => r.AnalysisType == "MassBalance");
        results.Should().Contain(r => r.AnalysisType == "AreaChange");
        results.Should().Contain(r => r.AnalysisType == "Velocity");
    }

    [Fact]
    public async Task GetAnalysisResultsByGlacierIdAsync_ReturnsEmpty_ForInvalidGlacierId()
    {
        var results = await _service.GetAnalysisResultsByGlacierIdAsync(Guid.NewGuid());

        results.Should().NotBeNull();
        results.Should().BeEmpty();
    }

    [Fact]
    public async Task GetAnomaliesAsync_ReturnsOnlyAnomalies()
    {
        var anomalies = await _service.GetAnomaliesAsync(100);

        anomalies.Should().NotBeNull();
        anomalies.Should().HaveCount(1);
        anomalies.First().AnalysisType.Should().Be("AreaChange");
        anomalies.First().IsAnomaly.Should().BeTrue();
    }

    [Fact]
    public async Task GetAnomaliesAsync_RespectsLimit()
    {
        var anomalies = await _service.GetAnomaliesAsync(1);

        anomalies.Should().NotBeNull();
        anomalies.Should().HaveCount(1);
    }

    [Fact]
    public async Task GetAnalysisResultsByTypeAsync_ReturnsFilteredResults()
    {
        var results = await _service.GetAnalysisResultsByTypeAsync("MassBalance");

        results.Should().NotBeNull();
        results.Should().HaveCount(1);
        results.First().AnalysisType.Should().Be("MassBalance");
    }

    [Fact]
    public async Task GetAnalysisSummaryAsync_ReturnsSummary_ForValidGlacierId()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");

        var summary = await _service.GetAnalysisSummaryAsync(glacierId);

        summary.Should().NotBeNull();
        summary!.GlacierId.Should().Be(glacierId);
        summary.TotalAnalyses.Should().Be(3);
        summary.AnomalyCount.Should().Be(1);
        summary.LastAnalysisDate.Should().NotBeNull();
    }

    [Fact]
    public async Task GetAnalysisSummaryAsync_ReturnsNull_ForInvalidGlacierId()
    {
        var summary = await _service.GetAnalysisSummaryAsync(Guid.NewGuid());

        summary.Should().BeNull();
    }

    [Fact]
    public async Task GetMassBalanceTrendAsync_ReturnsTrendData_WhenDataExists()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");

        var trend = await _service.GetMassBalanceTrendAsync(glacierId);

        trend.Should().NotBeNull();
    }

    [Fact]
    public async Task CompareGlaciersAsync_ReturnsComparisonData()
    {
        var glacierIds = new List<Guid>
        {
            Guid.Parse("11111111-1111-1111-1111-111111111111")
        };

        var comparison = await _service.CompareGlaciersAsync(glacierIds);

        comparison.Should().NotBeNull();
    }

    [Fact]
    public async Task DetectAnomaliesAsync_DetectsStatisticalAnomalies()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");

        var detected = await _service.DetectAnomaliesAsync(glacierId);

        detected.Should().NotBeNull();
    }

    [Fact]
    public async Task GetTimeSeriesDataAsync_ReturnsTimeSeries_WhenDataExists()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");

        var timeSeries = await _service.GetTimeSeriesDataAsync(glacierId, "MassBalance", 365);

        timeSeries.Should().NotBeNull();
    }

    [Fact]
    public async Task CreateAnalysisResultAsync_AddsNewResult()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");
        var newResult = new AnalysisResult
        {
            GlacierId = glacierId,
            AnalysisType = "Temperature",
            Result = 2.5,
            IsAnomaly = false,
            AnalysisDate = DateTime.UtcNow
        };

        var created = await _service.CreateAnalysisResultAsync(newResult);

        created.Should().NotBeNull();
        created.Id.Should().NotBeEmpty();
        created.AnalysisType.Should().Be("Temperature");
    }

    [Fact]
    public async Task DeleteAnalysisResultAsync_ReturnsTrue_WhenResultExists()
    {
        var result = _dbContext.AnalysisResults.First();
        var deleted = await _service.DeleteAnalysisResultAsync(result.Id);

        deleted.Should().BeTrue();
    }

    [Fact]
    public async Task DeleteAnalysisResultAsync_ReturnsFalse_WhenResultDoesNotExist()
    {
        var deleted = await _service.DeleteAnalysisResultAsync(Guid.NewGuid());

        deleted.Should().BeFalse();
    }

    [Fact]
    public async Task GetRecentAnalysesAsync_ReturnsMostRecentAnalyses()
    {
        var recent = await _service.GetRecentAnalysesAsync(2);

        recent.Should().NotBeNull();
        recent.Should().HaveCount(2);
        recent.Should().BeInDescendingOrder(r => r.AnalysisDate);
    }

    [Fact]
    public async Task GetAnalysesByDateRangeAsync_ReturnsFilteredResults()
    {
        var start = DateTime.UtcNow.AddDays(-20);
        var end = DateTime.UtcNow.AddDays(-10);

        var results = await _service.GetAnalysesByDateRangeAsync(start, end);

        results.Should().NotBeNull();
        results.Should().OnlyContain(r => r.AnalysisDate >= start && r.AnalysisDate <= end);
    }

    [Fact]
    public async Task UpdateAnalysisResultAsync_ModifiesExistingResult()
    {
        var result = _dbContext.AnalysisResults.First();
        var originalResult = result.Result;
        result.Result = 99.99;

        var updated = await _service.UpdateAnalysisResultAsync(result.Id, result);

        updated.Should().NotBeNull();
        updated!.Result.Should().Be(99.99);
        updated.Result.Should().NotBe(originalResult);
    }

    [Fact]
    public async Task GetAnalysisTypesAsync_ReturnsDistinctTypes()
    {
        var types = await _service.GetAnalysisTypesAsync();

        types.Should().NotBeNull();
        types.Should().Contain("MassBalance");
        types.Should().Contain("AreaChange");
        types.Should().Contain("Velocity");
    }

    [Fact]
    public async Task GetAnalysisCountAsync_ReturnsCorrectCount()
    {
        var count = await _service.GetAnalysisCountAsync();

        count.Should().Be(3);
    }

    [Fact]
    public async Task GetAnalysisCountByTypeAsync_ReturnsCorrectCounts()
    {
        var counts = await _service.GetAnalysisCountByTypeAsync();

        counts.Should().NotBeNull();
        counts.Should().ContainKey("MassBalance");
        counts["MassBalance"].Should().Be(1);
        counts["AreaChange"].Should().Be(1);
    }

    [Fact]
    public async Task GetAverageResultByTypeAsync_ReturnsCorrectAverage()
    {
        var average = await _service.GetAverageResultByTypeAsync("MassBalance");

        average.Should().Be(-1.25);
    }

    [Fact]
    public async Task GetMinResultByTypeAsync_ReturnsCorrectMin()
    {
        var min = await _service.GetMinResultByTypeAsync("AreaChange");

        min.Should().Be(-0.05);
    }

    [Fact]
    public async Task GetMaxResultByTypeAsync_ReturnsCorrectMax()
    {
        var max = await _service.GetMaxResultByTypeAsync("Velocity");

        max.Should().Be(0.023);
    }

    [Fact]
    public async Task GetStdDeviationByTypeAsync_ReturnsPositiveValue()
    {
        var stdDev = await _service.GetStdDeviationByTypeAsync("MassBalance");

        stdDev.Should().BeGreaterThanOrEqualTo(0);
    }

    [Fact]
    public async Task BatchCreateAnalysisResultsAsync_CreatesMultipleResults()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");
        var newResults = new List<AnalysisResult>
        {
            new() { GlacierId = glacierId, AnalysisType = "Precipitation", Result = 450.5, AnalysisDate = DateTime.UtcNow },
            new() { GlacierId = glacierId, AnalysisType = "SnowCover", Result = 0.85, AnalysisDate = DateTime.UtcNow }
        };

        var created = await _service.BatchCreateAnalysisResultsAsync(newResults);

        created.Should().HaveCount(2);
        created.Should().OnlyContain(r => r.Id != Guid.Empty);
    }

    [Fact]
    public async Task GetAnomalyRateAsync_ReturnsRateBetweenZeroAndOne()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");

        var rate = await _service.GetAnomalyRateAsync(glacierId);

        rate.Should().BeGreaterThanOrEqualTo(0);
        rate.Should().BeLessThanOrEqualTo(1);
    }
}
