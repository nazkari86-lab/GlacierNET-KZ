using FluentAssertions;
using GlacierNET.Analysis.Data;
using GlacierNET.Analysis.Models;
using GlacierNET.Analysis.Services;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Moq;
using Xunit;

namespace GlacierNET.Tests;

public class TrendServiceTests
{
    private readonly GlacierDbContext _dbContext;
    private readonly TrendService _service;

    public TrendServiceTests()
    {
        var options = new DbContextOptionsBuilder<GlacierDbContext>()
            .UseInMemoryDatabase(databaseName: Guid.NewGuid().ToString())
            .Options;
        _dbContext = new GlacierDbContext(options);

        var loggerMock = new Mock<ILogger<TrendService>>();
        _service = new TrendService(_dbContext, loggerMock.Object);
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
                Name = "Test Glacier",
                Region = "Tien Shan",
                AreaKm2 = 45.2,
                Latitude = 42.5,
                Longitude = 75.3,
                Elevation = 4200,
                IsActive = true,
                CreatedAt = DateTime.UtcNow
            });
        }

        if (!_dbContext.TrendData.Any())
        {
            for (int year = 2010; year <= 2024; year++)
            {
                _dbContext.TrendData.Add(new TrendData
                {
                    Id = Guid.NewGuid(),
                    GlacierId = glacierId,
                    Year = year,
                    MassBalance = -0.5 - (year - 2010) * 0.15 + Random.Shared.NextDouble() * 0.3,
                    AreaChange = -0.02 - (year - 2010) * 0.005,
                    ElevationChange = -5.0 - (year - 2010) * 1.2,
                    Snowfall = 1200.0 - (year - 2010) * 15.0 + Random.Shared.NextDouble() * 50,
                    CreatedAt = DateTime.UtcNow
                });
            }
        }

        _dbContext.SaveChanges();
    }

    [Fact]
    public async Task GetTrendDataByGlacierIdAsync_ReturnsTrendData_ForValidGlacierId()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");

        var trendData = await _service.GetTrendDataByGlacierIdAsync(glacierId);

        trendData.Should().NotBeNull();
        trendData.Should().HaveCount(15);
        trendData.Should().BeInAscendingOrder(t => t.Year);
    }

    [Fact]
    public async Task GetTrendDataByGlacierIdAsync_ReturnsEmpty_ForInvalidGlacierId()
    {
        var trendData = await _service.GetTrendDataByGlacierIdAsync(Guid.NewGuid());

        trendData.Should().NotBeNull();
        trendData.Should().BeEmpty();
    }

    [Fact]
    public async Task GetTrendSummaryAsync_ReturnsSummary_WhenDataExists()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");

        var summary = await _service.GetTrendSummaryAsync(glacierId);

        summary.Should().NotBeNull();
        summary!.GlacierId.Should().Be(glacierId);
        summary.TotalYears.Should().Be(15);
        summary.StartYear.Should().Be(2010);
        summary.EndYear.Should().Be(2024);
        summary.Slope.Should().NotBe(0);
        summary.RSquared.Should().BeGreaterThanOrEqualTo(0);
        summary.RSquared.Should().BeLessThanOrEqualTo(1);
    }

    [Fact]
    public async Task GetTrendSummaryAsync_ReturnsNull_ForInvalidGlacierId()
    {
        var summary = await _service.GetTrendSummaryAsync(Guid.NewGuid());

        summary.Should().BeNull();
    }

    [Fact]
    public async Task CalculateLinearRegressionAsync_ReturnsCorrectSlope_WhenTrendIsDeclining()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");

        var regression = await _service.CalculateLinearRegressionAsync(glacierId, "MassBalance");

        regression.Should().NotBeNull();
        regression!.Slope.Should().BeLessThan(0, "mass balance should be declining");
        regression.Intercept.Should().NotBe(0);
        regression.RSquared.Should().BeGreaterThanOrEqualTo(0);
        regression.RSquared.Should().BeLessThanOrEqualTo(1);
    }

    [Fact]
    public async Task CalculateLinearRegressionAsync_ReturnsNull_ForInvalidGlacierId()
    {
        var regression = await _service.CalculateLinearRegressionAsync(Guid.NewGuid(), "MassBalance");

        regression.Should().BeNull();
    }

    [Fact]
    public async Task GetSeasonalPatternsAsync_ReturnsPatterns_WhenDataExists()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");

        var patterns = await _service.GetSeasonalPatternsAsync(glacierId);

        patterns.Should().NotBeNull();
        patterns.Should().NotBeEmpty();
    }

    [Fact]
    public async Task DetectTrendShiftAsync_DetectsShifts_WhenPresent()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");

        var shifts = await _service.DetectTrendShiftAsync(glacierId);

        shifts.Should().NotBeNull();
    }

    [Fact]
    public async Task CompareTrendsAsync_ReturnsComparison_WhenGlaciersExist()
    {
        var glacierIds = new List<Guid>
        {
            Guid.Parse("11111111-1111-1111-1111-111111111111")
        };

        var comparison = await _service.CompareTrendsAsync(glacierIds);

        comparison.Should().NotBeNull();
        comparison.Should().HaveCount(1);
    }

    [Fact]
    public async Task GetYearOverYearChangeAsync_ReturnsYearlyChanges()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");

        var changes = await _service.GetYearOverYearChangeAsync(glacierId);

        changes.Should().NotBeNull();
        changes.Should().HaveCount(14);
        changes.Should().OnlyContain(c => c.Year >= 2011 && c.Year <= 2024);
    }

    [Fact]
    public async Task GetMovingAverageAsync_ReturnsSmoothedData()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");

        var movingAvg = await _service.GetMovingAverageAsync(glacierId, 3);

        movingAvg.Should().NotBeNull();
        movingAvg.Should().NotBeEmpty();
    }

    [Fact]
    public async Task CreateTrendDataAsync_AddsNewTrendData()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");
        var newData = new TrendData
        {
            GlacierId = glacierId,
            Year = 2025,
            MassBalance = -3.0,
            AreaChange = -0.1,
            ElevationChange = -15.0,
            Snowfall = 900.0
        };

        var created = await _service.CreateTrendDataAsync(newData);

        created.Should().NotBeNull();
        created.Id.Should().NotBeEmpty();
        created.Year.Should().Be(2025);
    }

    [Fact]
    public async Task UpdateTrendDataAsync_ModifiesExistingData()
    {
        var trendData = _dbContext.TrendData.First();
        var originalMB = trendData.MassBalance;
        trendData.MassBalance = -5.0;

        var updated = await _service.UpdateTrendDataAsync(trendData.Id, trendData);

        updated.Should().NotBeNull();
        updated!.MassBalance.Should().Be(-5.0);
        updated.MassBalance.Should().NotBe(originalMB);
    }

    [Fact]
    public async Task DeleteTrendDataAsync_ReturnsTrue_WhenDataExists()
    {
        var trendData = _dbContext.TrendData.First();

        var deleted = await _service.DeleteTrendDataAsync(trendData.Id);

        deleted.Should().BeTrue();
    }

    [Fact]
    public async Task DeleteTrendDataAsync_ReturnsFalse_WhenDataDoesNotExist()
    {
        var deleted = await _service.DeleteTrendDataAsync(Guid.NewGuid());

        deleted.Should().BeFalse();
    }

    [Fact]
    public async Task GetAverageMassBalanceAsync_ReturnsCorrectAverage()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");

        var average = await _service.GetAverageMassBalanceAsync(glacierId);

        average.Should().BeLessThan(0, "average mass balance should be negative");
    }

    [Fact]
    public async Task GetMinMassBalanceAsync_ReturnsMinimum()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");

        var min = await _service.GetMinMassBalanceAsync(glacierId);

        min.Should().BeLessThan(0);
    }

    [Fact]
    public async Task GetMaxMassBalanceAsync_ReturnsMaximum()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");

        var max = await _service.GetMaxMassBalanceAsync(glacierId);

        max.Should().BeGreaterThan(-5.0);
    }

    [Fact]
    public async Task GetStdDeviationAsync_ReturnsPositiveValue()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");

        var stdDev = await _service.GetStdDeviationAsync(glacierId);

        stdDev.Should().BeGreaterThan(0);
    }

    [Fact]
    public async Task BatchCreateTrendDataAsync_CreatesMultipleRecords()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");
        var newData = new List<TrendData>
        {
            new() { GlacierId = glacierId, Year = 2025, MassBalance = -3.0, AreaChange = -0.1, Snowfall = 900.0 },
            new() { GlacierId = glacierId, Year = 2026, MassBalance = -3.2, AreaChange = -0.12, Snowfall = 880.0 }
        };

        var created = await _service.BatchCreateTrendDataAsync(newData);

        created.Should().HaveCount(2);
        created.Should().OnlyContain(t => t.Id != Guid.Empty);
    }

    [Fact]
    public async Task GetCorrelationAsync_ReturnsValueBetweenMinusOneAndOne()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");

        var correlation = await _service.GetCorrelationAsync(glacierId, "MassBalance", "AreaChange");

        correlation.Should().BeGreaterThanOrEqualTo(-1);
        correlation.Should().BeLessThanOrEqualTo(1);
    }

    [Fact]
    public async Task GetAccelerationAsync_ReturnsAccelerationValue()
    {
        var glacierId = Guid.Parse("11111111-1111-1111-1111-111111111111");

        var acceleration = await _service.GetAccelerationAsync(glacierId);

        acceleration.Should().NotBe(0, "there should be some acceleration in the trend");
    }
}
