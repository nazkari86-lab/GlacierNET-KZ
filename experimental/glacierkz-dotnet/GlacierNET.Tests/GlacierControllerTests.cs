using FluentAssertions;
using GlacierNET.Analysis.Controllers;
using GlacierNET.Analysis.Data;
using GlacierNET.Analysis.Models;
using GlacierNET.Analysis.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Caching.Distributed;
using Microsoft.Extensions.Logging;
using Moq;
using Xunit;

namespace GlacierNET.Tests;

public class GlacierControllerTests
{
    private readonly Mock<ILogger<GlacierController>> _loggerMock;
    private readonly Mock<GlacierService> _glacierServiceMock;
    private readonly Mock<IDistributedCache> _cacheMock;
    private readonly GlacierController _controller;
    private readonly GlacierDbContext _dbContext;

    public GlacierControllerTests()
    {
        _loggerMock = new Mock<ILogger<GlacierController>>();
        _cacheMock = new Mock<IDistributedCache>();

        var options = new DbContextOptionsBuilder<GlacierDbContext>()
            .UseInMemoryDatabase(databaseName: Guid.NewGuid().ToString())
            .Options;
        _dbContext = new GlacierDbContext(options);

        var cacheServiceMock = new Mock<CacheService>(
            Mock.Of<IDistributedCache>(),
            Mock.Of<ILogger<CacheService>>());

        _glacierServiceMock = new Mock<GlacierService>(
            _dbContext,
            cacheServiceMock.Object,
            Mock.Of<ILogger<GlacierService>>());

        _controller = new GlacierController(
            _glacierServiceMock.Object,
            _loggerMock.Object);
    }

    [Fact]
    public async Task GetAll_ReturnsOkResult_WithListOfGlaciers()
    {
        var glaciers = new List<Glacier>
        {
            new() { Id = Guid.NewGuid(), Name = "Petrov Glacier", Region = "Tien Shan", AreaKm2 = 45.2, IsActive = true },
            new() { Id = Guid.NewGuid(), Name = "Manas Glacier", Region = "Pamir", AreaKm2 = 82.5, IsActive = true }
        };
        _glacierServiceMock.Setup(s => s.GetAllGlaciersAsync(1, 50, null, null))
            .ReturnsAsync(new PagedResult<Glacier> { Items = glaciers, TotalCount = 2 });

        var result = await _controller.GetAll();

        var okResult = result.Should().BeOfType<OkObjectResult>().Subject;
        var pagedResult = okResult.Value.Should().BeOfType<PagedResult<Glacier>>().Subject;
        pagedResult.Items.Should().HaveCount(2);
    }

    [Fact]
    public async Task GetById_ReturnsOkResult_WhenGlacierExists()
    {
        var glacierId = Guid.NewGuid();
        var glacier = new Glacier
        {
            Id = glacierId,
            Name = "Test Glacier",
            Region = "Tien Shan",
            AreaKm2 = 25.0,
            Latitude = 42.5,
            Longitude = 75.3,
            Elevation = 4200,
            IsActive = true,
            CreatedAt = DateTime.UtcNow
        };
        _glacierServiceMock.Setup(s => s.GetGlacierByIdAsync(glacierId))
            .ReturnsAsync(glacier);

        var result = await _controller.GetById(glacierId);

        var okResult = result.Should().BeOfType<OkObjectResult>().Subject;
        var returned = okResult.Value.Should().BeOfType<Glacier>().Subject;
        returned.Name.Should().Be("Test Glacier");
        returned.AreaKm2.Should().Be(25.0);
    }

    [Fact]
    public async Task GetById_ReturnsNotFound_WhenGlacierDoesNotExist()
    {
        _glacierServiceMock.Setup(s => s.GetGlacierByIdAsync(It.IsAny<Guid>()))
            .ReturnsAsync((Glacier?)null);

        var result = await _controller.GetById(Guid.NewGuid());

        result.Should().BeOfType<NotFoundResult>();
    }

    [Fact]
    public async Task Create_ReturnsCreatedAtAction_WithNewGlacier()
    {
        var glacier = new Glacier
        {
            Name = "New Glacier",
            Region = "Karakoram",
            AreaKm2 = 60.0,
            Latitude = 35.8,
            Longitude = 76.5,
            Elevation = 5100,
            IsActive = true
        };
        _glacierServiceMock.Setup(s => s.CreateGlacierAsync(It.IsAny<Glacier>()))
            .ReturnsAsync((Glacier g) => { g.Id = Guid.NewGuid(); g.CreatedAt = DateTime.UtcNow; return g; });

        var result = await _controller.Create(glacier);

        var createdResult = result.Should().BeOfType<CreatedAtActionResult>().Subject;
        var returned = createdResult.Value.Should().BeOfType<Glacier>().Subject;
        returned.Name.Should().Be("New Glacier");
        returned.Id.Should().NotBeEmpty();
    }

    [Fact]
    public async Task Update_ReturnsOkResult_WhenGlacierExists()
    {
        var glacierId = Guid.NewGuid();
        var existing = new Glacier
        {
            Id = glacierId,
            Name = "Old Name",
            Region = "Tien Shan",
            AreaKm2 = 30.0,
            IsActive = true,
            CreatedAt = DateTime.UtcNow
        };
        var updated = new Glacier
        {
            Name = "Updated Name",
            Region = "Tien Shan",
            AreaKm2 = 32.0
        };

        _glacierServiceMock.Setup(s => s.GetGlacierByIdAsync(glacierId))
            .ReturnsAsync(existing);
        _glacierServiceMock.Setup(s => s.UpdateGlacierAsync(glacierId, It.IsAny<Glacier>()))
            .ReturnsAsync((Guid id, Glacier g) =>
            {
                g.Id = id;
                g.CreatedAt = existing.CreatedAt;
                return g;
            });

        var result = await _controller.Update(glacierId, updated);

        var okResult = result.Should().BeOfType<OkObjectResult>().Subject;
        var returned = okResult.Value.Should().BeOfType<Glacier>().Subject;
        returned.Name.Should().Be("Updated Name");
        returned.AreaKm2.Should().Be(32.0);
    }

    [Fact]
    public async Task Update_ReturnsNotFound_WhenGlacierDoesNotExist()
    {
        _glacierServiceMock.Setup(s => s.GetGlacierByIdAsync(It.IsAny<Guid>()))
            .ReturnsAsync((Glacier?)null);

        var result = await _controller.Update(Guid.NewGuid(), new Glacier());

        result.Should().BeOfType<NotFoundResult>();
    }

    [Fact]
    public async Task Delete_ReturnsNoContent_WhenGlacierExists()
    {
        var glacierId = Guid.NewGuid();
        _glacierServiceMock.Setup(s => s.DeleteGlacierAsync(glacierId))
            .ReturnsAsync(true);

        var result = await _controller.Delete(glacierId);

        result.Should().BeOfType<NoContentResult>();
    }

    [Fact]
    public async Task Delete_ReturnsNotFound_WhenGlacierDoesNotExist()
    {
        _glacierServiceMock.Setup(s => s.DeleteGlacierAsync(It.IsAny<Guid>()))
            .ReturnsAsync(false);

        var result = await _controller.Delete(Guid.NewGuid());

        result.Should().BeOfType<NotFoundResult>();
    }

    [Fact]
    public async Task Search_ReturnsOkResult_WithMatchingGlaciers()
    {
        var glaciers = new List<Glacier>
        {
            new() { Id = Guid.NewGuid(), Name = "Petrov Glacier", Region = "Tien Shan", AreaKm2 = 45.2 }
        };
        _glacierServiceMock.Setup(s => s.SearchGlaciersAsync("Petrov", null))
            .ReturnsAsync(glaciers);

        var result = await _controller.Search("Petrov", null);

        var okResult = result.Should().BeOfType<OkObjectResult>().Subject;
        var returned = okResult.Value.Should().BeOfType<List<Glacier>>().Subject;
        returned.Should().HaveCount(1);
        returned[0].Name.Should().Be("Petrov Glacier");
    }

    [Fact]
    public async Task GetByRegion_ReturnsOkResult_WithGlaciersInRegion()
    {
        var glaciers = new List<Glacier>
        {
            new() { Id = Guid.NewGuid(), Name = "Glacier A", Region = "Tien Shan", AreaKm2 = 10.0 },
            new() { Id = Guid.NewGuid(), Name = "Glacier B", Region = "Tien Shan", AreaKm2 = 20.0 }
        };
        _glacierServiceMock.Setup(s => s.GetGlaciersByRegionAsync("Tien Shan"))
            .ReturnsAsync(glaciers);

        var result = await _controller.GetByRegion("Tien Shan");

        var okResult = result.Should().BeOfType<OkObjectResult>().Subject;
        var returned = okResult.Value.Should().BeOfType<List<Glacier>>().Subject;
        returned.Should().HaveCount(2);
    }

    [Fact]
    public async Task GetStatistics_ReturnsOkResult_WithStatistics()
    {
        var stats = new GlacierStatistics
        {
            TotalGlaciers = 100,
            ActiveGlaciers = 85,
            TotalAreaKm2 = 5432.1,
            AverageAreaKm2 = 54.3,
            Regions = new Dictionary<string, int> { { "Tien Shan", 50 }, { "Pamir", 30 }, { "Karakoram", 20 } },
            StatusCounts = new Dictionary<string, int> { { "Active", 85 }, { "Retreating", 10 }, { "Stable", 5 } }
        };
        _glacierServiceMock.Setup(s => s.GetGlacierStatisticsAsync())
            .ReturnsAsync(stats);

        var result = await _controller.GetStatistics();

        var okResult = result.Should().BeOfType<OkObjectResult>().Subject;
        var returned = okResult.Value.Should().BeOfType<GlacierStatistics>().Subject;
        returned.TotalGlaciers.Should().Be(100);
        returned.TotalAreaKm2.Should().Be(5432.1);
    }

    [Fact]
    public async Task GetByBoundingBox_ReturnsOkResult_WithGlaciersInBounds()
    {
        var glaciers = new List<Glacier>
        {
            new() { Id = Guid.NewGuid(), Name = "Glacier In Bounds", Latitude = 42.0, Longitude = 75.0, AreaKm2 = 15.0 }
        };
        _glacierServiceMock.Setup(s => s.GetGlaciersByBoundingBoxAsync(40.0, 44.0, 70.0, 80.0))
            .ReturnsAsync(glaciers);

        var result = await _controller.GetByBoundingBox(40.0, 44.0, 70.0, 80.0);

        var okResult = result.Should().BeOfType<OkObjectResult>().Subject;
        var returned = okResult.Value.Should().BeOfType<List<Glacier>>().Subject;
        returned.Should().HaveCount(1);
    }

    [Fact]
    public async Task GetNearby_ReturnsOkResult_WithNearbyGlaciers()
    {
        var glaciers = new List<Glacier>
        {
            new() { Id = Guid.NewGuid(), Name = "Nearby Glacier", Latitude = 42.1, Longitude = 75.1, AreaKm2 = 12.0 }
        };
        _glacierServiceMock.Setup(s => s.GetNearbyGlaciersAsync(42.0, 75.0, 10.0))
            .ReturnsAsync(glaciers);

        var result = await _controller.GetNearby(42.0, 75.0, 10.0);

        var okResult = result.Should().BeOfType<OkObjectResult>().Subject;
        var returned = okResult.Value.Should().BeOfType<List<Glacier>>().Subject;
        returned.Should().HaveCount(1);
    }

    [Fact]
    public async Task SearchByName_ReturnsOkResult_WhenNameMatchExists()
    {
        var glaciers = new List<Glacier>
        {
            new() { Id = Guid.NewGuid(), Name = "Petrov Glacier", AreaKm2 = 45.2 }
        };
        _glacierServiceMock.Setup(s => s.SearchGlaciersByNameAsync("Petrov", false))
            .ReturnsAsync(glaciers);

        var result = await _controller.SearchByName("Petrov", false);

        var okResult = result.Should().BeOfType<OkObjectResult>().Subject;
        var returned = okResult.Value.Should().BeOfType<List<Glacier>>().Subject;
        returned.Should().HaveCount(1);
    }

    [Fact]
    public async Task SearchByStatus_ReturnsOkResult_WithFilteredGlaciers()
    {
        var glaciers = new List<Glacier>
        {
            new() { Id = Guid.NewGuid(), Name = "Active Glacier", IsActive = true, AreaKm2 = 30.0 }
        };
        _glacierServiceMock.Setup(s => s.GetGlaciersByStatusAsync(true))
            .ReturnsAsync(glaciers);

        var result = await _controller.SearchByStatus(true);

        var okResult = result.Should().BeOfType<OkObjectResult>().Subject;
        var returned = okResult.Value.Should().BeOfType<List<Glacier>>().Subject;
        returned.Should().HaveCount(1);
    }

    [Fact]
    public async Task GetCount_ReturnsOkResult_WithTotalCount()
    {
        _glacierServiceMock.Setup(s => s.GetGlacierCountAsync())
            .ReturnsAsync(150);

        var result = await _controller.GetCount();

        var okResult = result.Should().BeOfType<OkObjectResult>().Subject;
        okResult.Value.Should().Be(150);
    }

    [Fact]
    public async Task GetRegions_ReturnsOkResult_WithDistinctRegions()
    {
        var regions = new List<string> { "Tien Shan", "Pamir", "Karakoram", "Altai" };
        _glacierServiceMock.Setup(s => s.GetDistinctRegionsAsync())
            .ReturnsAsync(regions);

        var result = await _controller.GetRegions();

        var okResult = result.Should().BeOfType<OkObjectResult>().Subject;
        var returned = okResult.Value.Should().BeOfType<List<string>>().Subject;
        returned.Should().HaveCount(4);
        returned.Should().Contain("Tien Shan");
    }
}
