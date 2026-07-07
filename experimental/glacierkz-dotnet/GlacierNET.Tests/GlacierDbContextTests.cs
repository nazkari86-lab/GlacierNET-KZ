using FluentAssertions;
using GlacierNET.Analysis.Data;
using GlacierNET.Analysis.Models;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace GlacierNET.Tests;

public class GlacierDbContextTests
{
    private readonly GlacierDbContext _dbContext;

    public GlacierDbContextTests()
    {
        var options = new DbContextOptionsBuilder<GlacierDbContext>()
            .UseInMemoryDatabase(databaseName: Guid.NewGuid().ToString())
            .Options;
        _dbContext = new GlacierDbContext(options);
        _dbContext.Database.EnsureCreated();
    }

    public void Dispose()
    {
        _dbContext.Database.EnsureDeleted();
        _dbContext.Dispose();
    }

    [Fact]
    public void Database_CanBeCreated()
    {
        _dbContext.Database.IsInMemory().Should().BeTrue();
    }

    [Fact]
    public void DbSet_Glaciers_IsAccessible()
    {
        _dbContext.Glaciers.Should().NotBeNull();
    }

    [Fact]
    public void DbSet_AnalysisResults_IsAccessible()
    {
        _dbContext.AnalysisResults.Should().NotBeNull();
    }

    [Fact]
    public void DbSet_TrendData_IsAccessible()
    {
        _dbContext.TrendData.Should().NotBeNull();
    }

    [Fact]
    public void DbSet_Users_IsAccessible()
    {
        _dbContext.Users.Should().NotBeNull();
    }

    [Fact]
    public void DbSet_Reports_IsAccessible()
    {
        _dbContext.Reports.Should().NotBeNull();
    }

    [Fact]
    public void DbSet_ProcessingTasks_IsAccessible()
    {
        _dbContext.ProcessingTasks.Should().NotBeNull();
    }

    [Fact]
    public void DbSet_SatelliteImages_IsAccessible()
    {
        _dbContext.SatelliteImages.Should().NotBeNull();
    }

    [Fact]
    public async Task Glaciers_CanBeAdded()
    {
        var glacier = new Glacier
        {
            Id = Guid.NewGuid(),
            Name = "Test Glacier",
            Region = "Tien Shan",
            AreaKm2 = 35.5,
            Latitude = 42.0,
            Longitude = 76.0,
            Elevation = 4500,
            IsActive = true,
            CreatedAt = DateTime.UtcNow
        };

        _dbContext.Glaciers.Add(glacier);
        await _dbContext.SaveChangesAsync();

        var saved = await _dbContext.Glaciers.FindAsync(glacier.Id);
        saved.Should().NotBeNull();
        saved!.Name.Should().Be("Test Glacier");
        saved.Region.Should().Be("Tien Shan");
        saved.AreaKm2.Should().Be(35.5);
    }

    [Fact]
    public async Task Glaciers_CanBeQueried()
    {
        _dbContext.Glaciers.AddRange(
            new Glacier { Id = Guid.NewGuid(), Name = "Glacier A", Region = "Tien Shan", AreaKm2 = 10.0, CreatedAt = DateTime.UtcNow },
            new Glacier { Id = Guid.NewGuid(), Name = "Glacier B", Region = "Pamir", AreaKm2 = 20.0, CreatedAt = DateTime.UtcNow },
            new Glacier { Id = Guid.NewGuid(), Name = "Glacier C", Region = "Tien Shan", AreaKm2 = 30.0, CreatedAt = DateTime.UtcNow }
        );
        await _dbContext.SaveChangesAsync();

        var tienShanGlaciers = await _dbContext.Glaciers
            .Where(g => g.Region == "Tien Shan")
            .ToListAsync();

        tienShanGlaciers.Should().HaveCount(2);
        tienShanGlaciers.Should().OnlyContain(g => g.Region == "Tien Shan");
    }

    [Fact]
    public async Task Glaciers_CanBeUpdated()
    {
        var glacier = new Glacier
        {
            Id = Guid.NewGuid(),
            Name = "Original Name",
            Region = "Tien Shan",
            AreaKm2 = 50.0,
            CreatedAt = DateTime.UtcNow
        };
        _dbContext.Glaciers.Add(glacier);
        await _dbContext.SaveChangesAsync();

        var saved = await _dbContext.Glaciers.FindAsync(glacier.Id);
        saved!.Name = "Updated Name";
        saved.AreaKm2 = 55.0;
        await _dbContext.SaveChangesAsync();

        var updated = await _dbContext.Glaciers.FindAsync(glacier.Id);
        updated!.Name.Should().Be("Updated Name");
        updated.AreaKm2.Should().Be(55.0);
    }

    [Fact]
    public async Task Glaciers_CanBeDeleted()
    {
        var glacier = new Glacier
        {
            Id = Guid.NewGuid(),
            Name = "To Delete",
            Region = "Tien Shan",
            AreaKm2 = 10.0,
            CreatedAt = DateTime.UtcNow
        };
        _dbContext.Glaciers.Add(glacier);
        await _dbContext.SaveChangesAsync();

        _dbContext.Glaciers.Remove(glacier);
        await _dbContext.SaveChangesAsync();

        var deleted = await _dbContext.Glaciers.FindAsync(glacier.Id);
        deleted.Should().BeNull();
    }

    [Fact]
    public async Task AnalysisResults_CanBeAdded()
    {
        var glacierId = Guid.NewGuid();
        _dbContext.Glaciers.Add(new Glacier
        {
            Id = glacierId,
            Name = "Parent Glacier",
            Region = "Tien Shan",
            AreaKm2 = 30.0,
            CreatedAt = DateTime.UtcNow
        });
        await _dbContext.SaveChangesAsync();

        var result = new AnalysisResult
        {
            Id = Guid.NewGuid(),
            GlacierId = glacierId,
            AnalysisType = "MassBalance",
            Result = -1.5,
            IsAnomaly = false,
            AnomalyScore = 1.2,
            AnalysisDate = DateTime.UtcNow
        };

        _dbContext.AnalysisResults.Add(result);
        await _dbContext.SaveChangesAsync();

        var saved = await _dbContext.AnalysisResults.FindAsync(result.Id);
        saved.Should().NotBeNull();
        saved!.AnalysisType.Should().Be("MassBalance");
        saved.Result.Should().Be(-1.5);
    }

    [Fact]
    public async Task AnalysisResults_CanBeFilteredByType()
    {
        var glacierId = Guid.NewGuid();
        _dbContext.Glaciers.Add(new Glacier
        {
            Id = glacierId,
            Name = "Parent Glacier",
            Region = "Tien Shan",
            AreaKm2 = 30.0,
            CreatedAt = DateTime.UtcNow
        });
        _dbContext.AnalysisResults.AddRange(
            new AnalysisResult { Id = Guid.NewGuid(), GlacierId = glacierId, AnalysisType = "MassBalance", Result = -1.0, AnalysisDate = DateTime.UtcNow },
            new AnalysisResult { Id = Guid.NewGuid(), GlacierId = glacierId, AnalysisType = "AreaChange", Result = -0.05, AnalysisDate = DateTime.UtcNow },
            new AnalysisResult { Id = Guid.NewGuid(), GlacierId = glacierId, AnalysisType = "MassBalance", Result = -2.0, AnalysisDate = DateTime.UtcNow }
        );
        await _dbContext.SaveChangesAsync();

        var massBalanceResults = await _dbContext.AnalysisResults
            .Where(r => r.AnalysisType == "MassBalance")
            .ToListAsync();

        massBalanceResults.Should().HaveCount(2);
        massBalanceResults.Should().OnlyContain(r => r.AnalysisType == "MassBalance");
    }

    [Fact]
    public async Task AnalysisResults_CanBeFilteredByAnomaly()
    {
        var glacierId = Guid.NewGuid();
        _dbContext.Glaciers.Add(new Glacier
        {
            Id = glacierId,
            Name = "Parent Glacier",
            Region = "Tien Shan",
            AreaKm2 = 30.0,
            CreatedAt = DateTime.UtcNow
        });
        _dbContext.AnalysisResults.AddRange(
            new AnalysisResult { Id = Guid.NewGuid(), GlacierId = glacierId, AnalysisType = "Test", Result = 1.0, IsAnomaly = false, AnalysisDate = DateTime.UtcNow },
            new AnalysisResult { Id = Guid.NewGuid(), GlacierId = glacierId, AnalysisType = "Test", Result = 2.0, IsAnomaly = true, AnalysisDate = DateTime.UtcNow },
            new AnalysisResult { Id = Guid.NewGuid(), GlacierId = glacierId, AnalysisType = "Test", Result = 3.0, IsAnomaly = true, AnalysisDate = DateTime.UtcNow }
        );
        await _dbContext.SaveChangesAsync();

        var anomalies = await _dbContext.AnalysisResults
            .Where(r => r.IsAnomaly)
            .ToListAsync();

        anomalies.Should().HaveCount(2);
        anomalies.Should().OnlyContain(r => r.IsAnomaly);
    }

    [Fact]
    public async Task TrendData_CanBeAdded()
    {
        var glacierId = Guid.NewGuid();
        _dbContext.Glaciers.Add(new Glacier
        {
            Id = glacierId,
            Name = "Parent Glacier",
            Region = "Tien Shan",
            AreaKm2 = 30.0,
            CreatedAt = DateTime.UtcNow
        });
        await _dbContext.SaveChangesAsync();

        var trendData = new TrendData
        {
            Id = Guid.NewGuid(),
            GlacierId = glacierId,
            Year = 2024,
            MassBalance = -1.5,
            AreaChange = -0.05,
            ElevationChange = -10.0,
            Snowfall = 1000.0,
            CreatedAt = DateTime.UtcNow
        };

        _dbContext.TrendData.Add(trendData);
        await _dbContext.SaveChangesAsync();

        var saved = await _dbContext.TrendData.FindAsync(trendData.Id);
        saved.Should().NotBeNull();
        saved!.Year.Should().Be(2024);
        saved.MassBalance.Should().Be(-1.5);
    }

    [Fact]
    public async Task TrendData_CanBeFilteredByYear()
    {
        var glacierId = Guid.NewGuid();
        _dbContext.Glaciers.Add(new Glacier
        {
            Id = glacierId,
            Name = "Parent Glacier",
            Region = "Tien Shan",
            AreaKm2 = 30.0,
            CreatedAt = DateTime.UtcNow
        });
        _dbContext.TrendData.AddRange(
            new TrendData { Id = Guid.NewGuid(), GlacierId = glacierId, Year = 2020, MassBalance = -1.0, Snowfall = 1200, CreatedAt = DateTime.UtcNow },
            new TrendData { Id = Guid.NewGuid(), GlacierId = glacierId, Year = 2021, MassBalance = -1.5, Snowfall = 1100, CreatedAt = DateTime.UtcNow },
            new TrendData { Id = Guid.NewGuid(), GlacierId = glacierId, Year = 2022, MassBalance = -2.0, Snowfall = 1000, CreatedAt = DateTime.UtcNow }
        );
        await _dbContext.SaveChangesAsync();

        var data2021 = await _dbContext.TrendData
            .Where(t => t.Year == 2021)
            .ToListAsync();

        data2021.Should().HaveCount(1);
        data2021[0].MassBalance.Should().Be(-1.5);
    }

    [Fact]
    public async Task Users_CanBeAdded()
    {
        var user = new User
        {
            Id = Guid.NewGuid(),
            Username = "testuser",
            Email = "test@example.com",
            PasswordHash = "hashed_password",
            Role = "Researcher",
            CreatedAt = DateTime.UtcNow
        };

        _dbContext.Users.Add(user);
        await _dbContext.SaveChangesAsync();

        var saved = await _dbContext.Users.FindAsync(user.Id);
        saved.Should().NotBeNull();
        saved!.Username.Should().Be("testuser");
        saved.Email.Should().Be("test@example.com");
    }

    [Fact]
    public async Task Users_CanBeQueriedByUsername()
    {
        _dbContext.Users.AddRange(
            new User { Id = Guid.NewGuid(), Username = "admin", Email = "admin@test.com", PasswordHash = "hash1", Role = "Admin", CreatedAt = DateTime.UtcNow },
            new User { Id = Guid.NewGuid(), Username = "researcher1", Email = "res@test.com", PasswordHash = "hash2", Role = "Researcher", CreatedAt = DateTime.UtcNow }
        );
        await _dbContext.SaveChangesAsync();

        var user = await _dbContext.Users
            .FirstOrDefaultAsync(u => u.Username == "admin");

        user.Should().NotBeNull();
        user!.Role.Should().Be("Admin");
    }

    [Fact]
    public async Task Reports_CanBeAdded()
    {
        var report = new Report
        {
            Id = Guid.NewGuid(),
            Title = "Annual Summary 2024",
            Type = ReportType.AnnualSummary,
            Format = ReportFormat.HTML,
            Content = "<html><body><h1>Annual Summary</h1></body></html>",
            CreatedAt = DateTime.UtcNow
        };

        _dbContext.Reports.Add(report);
        await _dbContext.SaveChangesAsync();

        var saved = await _dbContext.Reports.FindAsync(report.Id);
        saved.Should().NotBeNull();
        saved!.Title.Should().Be("Annual Summary 2024");
        saved.Type.Should().Be(ReportType.AnnualSummary);
    }

    [Fact]
    public async Task Reports_CanBeFilteredByType()
    {
        _dbContext.Reports.AddRange(
            new Report { Id = Guid.NewGuid(), Title = "Report 1", Type = ReportType.AnnualSummary, Format = ReportFormat.HTML, CreatedAt = DateTime.UtcNow },
            new Report { Id = Guid.NewGuid(), Title = "Report 2", Type = ReportType.TrendAnalysis, Format = ReportFormat.JSON, CreatedAt = DateTime.UtcNow },
            new Report { Id = Guid.NewGuid(), Title = "Report 3", Type = ReportType.AnnualSummary, Format = ReportFormat.CSV, CreatedAt = DateTime.UtcNow }
        );
        await _dbContext.SaveChangesAsync();

        var annualReports = await _dbContext.Reports
            .Where(r => r.Type == ReportType.AnnualSummary)
            .ToListAsync();

        annualReports.Should().HaveCount(2);
        annualReports.Should().OnlyContain(r => r.Type == ReportType.AnnualSummary);
    }

    [Fact]
    public async Task ProcessingTasks_CanBeAdded()
    {
        var task = new ProcessingTask
        {
            Id = Guid.NewGuid(),
            TaskType = "ImageProcessing",
            Status = ProcessingStatus.Pending,
            Progress = 0,
            CreatedAt = DateTime.UtcNow
        };

        _dbContext.ProcessingTasks.Add(task);
        await _dbContext.SaveChangesAsync();

        var saved = await _dbContext.ProcessingTasks.FindAsync(task.Id);
        saved.Should().NotBeNull();
        saved!.TaskType.Should().Be("ImageProcessing");
        saved.Status.Should().Be(ProcessingStatus.Pending);
    }

    [Fact]
    public async Task ProcessingTasks_CanBeFilteredByStatus()
    {
        _dbContext.ProcessingTasks.AddRange(
            new ProcessingTask { Id = Guid.NewGuid(), TaskType = "Task1", Status = ProcessingStatus.Running, Progress = 50, CreatedAt = DateTime.UtcNow },
            new ProcessingTask { Id = Guid.NewGuid(), TaskType = "Task2", Status = ProcessingStatus.Completed, Progress = 100, CreatedAt = DateTime.UtcNow },
            new ProcessingTask { Id = Guid.NewGuid(), TaskType = "Task3", Status = ProcessingStatus.Running, Progress = 30, CreatedAt = DateTime.UtcNow }
        );
        await _dbContext.SaveChangesAsync();

        var runningTasks = await _dbContext.ProcessingTasks
            .Where(t => t.Status == ProcessingStatus.Running)
            .ToListAsync();

        runningTasks.Should().HaveCount(2);
        runningTasks.Should().OnlyContain(t => t.Status == ProcessingStatus.Running);
    }

    [Fact]
    public async Task SatelliteImages_CanBeAdded()
    {
        var satelliteImage = new SatelliteImage
        {
            Id = Guid.NewGuid(),
            GlacierId = Guid.NewGuid(),
            Source = "Sentinel-2",
            AcquisitionDate = DateTime.UtcNow.AddDays(-7),
            CloudCover = 5.2,
            Resolution = 10.0,
            FilePath = "/data/sentinel2/image.tif",
            CreatedAt = DateTime.UtcNow
        };

        _dbContext.SatelliteImages.Add(satelliteImage);
        await _dbContext.SaveChangesAsync();

        var saved = await _dbContext.SatelliteImages.FindAsync(satelliteImage.Id);
        saved.Should().NotBeNull();
        saved!.Source.Should().Be("Sentinel-2");
        saved.CloudCover.Should().Be(5.2);
    }

    [Fact]
    public async Task MultipleEntities_CanBeQueriedInSingleTransaction()
    {
        var glacierId = Guid.NewGuid();
        _dbContext.Glaciers.Add(new Glacier
        {
            Id = glacierId,
            Name = "Complete Glacier",
            Region = "Tien Shan",
            AreaKm2 = 40.0,
            CreatedAt = DateTime.UtcNow
        });

        _dbContext.AnalysisResults.Add(new AnalysisResult
        {
            Id = Guid.NewGuid(),
            GlacierId = glacierId,
            AnalysisType = "MassBalance",
            Result = -1.0,
            AnalysisDate = DateTime.UtcNow
        });

        _dbContext.TrendData.Add(new TrendData
        {
            Id = Guid.NewGuid(),
            GlacierId = glacierId,
            Year = 2024,
            MassBalance = -1.0,
            Snowfall = 1000,
            CreatedAt = DateTime.UtcNow
        });

        await _dbContext.SaveChangesAsync();

        var glacier = await _dbContext.Glaciers.FindAsync(glacierId);
        var analyses = await _dbContext.AnalysisResults.Where(a => a.GlacierId == glacierId).ToListAsync();
        var trends = await _dbContext.TrendData.Where(t => t.GlacierId == glacierId).ToListAsync();

        glacier.Should().NotBeNull();
        analyses.Should().HaveCount(1);
        trends.Should().HaveCount(1);
    }

    [Fact]
    public async Task SaveChangesAsync_PersistsDataCorrectly()
    {
        var glacier = new Glacier
        {
            Id = Guid.NewGuid(),
            Name = "Persistence Test",
            Region = "Tien Shan",
            AreaKm2 = 99.9,
            CreatedAt = DateTime.UtcNow
        };

        _dbContext.Glaciers.Add(glacier);
        await _dbContext.SaveChangesAsync();

        _dbContext.ChangeTracker.Clear();

        var loaded = await _dbContext.Glaciers.FindAsync(glacier.Id);
        loaded.Should().NotBeNull();
        loaded!.Name.Should().Be("Persistence Test");
        loaded.AreaKm2.Should().Be(99.9);
    }

    [Fact]
    public void ConnectionString_CanBeSet()
    {
        var connectionString = _dbContext.Database.GetConnectionString();
        connectionString.Should().NotBeNullOrEmpty();
    }

    [Fact]
    public void DbContext_CanBeInstantiatedMultipleTimes()
    {
        var options1 = new DbContextOptionsBuilder<GlacierDbContext>()
            .UseInMemoryDatabase(databaseName: "TestDb1")
            .Options;

        var options2 = new DbContextOptionsBuilder<GlacierDbContext>()
            .UseInMemoryDatabase(databaseName: "TestDb2")
            .Options;

        using var context1 = new GlacierDbContext(options1);
        using var context2 = new GlacierDbContext(options2);

        context1.Should().NotBeSameAs(context2);
    }
}
