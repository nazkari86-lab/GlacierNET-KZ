using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Microsoft.EntityFrameworkCore;
using GlacierNET.Analysis.Data;
using GlacierNET.Analysis.Models;
using GlacierNET.Analysis.Services;
using System.Diagnostics;

namespace GlacierNET.Analysis.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize(Roles = "Admin")]
public class AdminController : ControllerBase
{
    private readonly GlacierDbContext _context;
    private readonly TrendService _trendService;
    private readonly NotificationService _notificationService;
    private readonly ILogger<AdminController> _logger;

    public AdminController(
        GlacierDbContext context,
        TrendService trendService,
        NotificationService notificationService,
        ILogger<AdminController> logger)
    {
        _context = context;
        _trendService = trendService;
        _notificationService = notificationService;
        _logger = logger;
    }

    [HttpGet("dashboard")]
    public async Task<ActionResult<AdminDashboard>> GetDashboard()
    {
        var glacierCount = await _context.Glaciers.CountAsync(g => g.IsActive);
        var imageCount = await _context.SatelliteImages.CountAsync();
        var analysisCount = await _context.AnalysisResults.CountAsync();
        var userCount = await _context.Users.CountAsync(u => u.IsActive);
        var taskCount = await _context.ProcessingTasks.CountAsync();

        var recentGlaciers = await _context.Glaciers
            .Where(g => g.IsActive)
            .OrderByDescending(g => g.UpdatedAt)
            .Take(5)
            .Select(g => new { g.Id, g.Name, g.Region, g.Status, g.UpdatedAt })
            .ToListAsync();

        var recentAnalyses = await _context.AnalysisResults
            .OrderByDescending(a => a.CreatedAt)
            .Take(5)
            .Select(a => new { a.Id, a.GlacierId, a.AnalysisType, a.Value, a.IsAnomaly, a.CreatedAt })
            .ToListAsync();

        var pendingTasks = await _context.ProcessingTasks
            .Where(t => t.Status == TaskStatusType.Running || t.Status == TaskStatusType.Queued)
            .Select(t => new { t.Id, t.Name, t.ProgressPercent, Status = t.Status.ToString() })
            .ToListAsync();

        var regionDistribution = await _context.Glaciers
            .Where(g => g.IsActive)
            .GroupBy(g => g.Region)
            .Select(g => new { Region = g.Key, Count = g.Count() })
            .OrderByDescending(g => g.Count)
            .ToListAsync();

        var statusDistribution = await _context.Glaciers
            .Where(g => g.IsActive)
            .GroupBy(g => g.Status)
            .Select(g => new { Status = g.Key.ToString(), Count = g.Count() })
            .ToListAsync();

        var anomalyCount = await _context.AnalysisResults
            .CountAsync(a => a.IsAnomaly);

        var process = Process.GetCurrentProcess();
        var uptime = DateTime.UtcNow - process.StartTime.ToUniversalTime();

        return Ok(new AdminDashboard
        {
            TotalGlaciers = glacierCount,
            TotalImages = imageCount,
            TotalAnalyses = analysisCount,
            TotalUsers = userCount,
            TotalTasks = taskCount,
            TotalAnomalies = anomalyCount,
            ActiveTasks = pendingTasks.Count,
            ServerUptime = uptime.TotalHours,
            RecentGlacierUpdates = recentGlaciers,
            RecentAnalyses = recentAnalyses,
            ActiveTasksList = pendingTasks,
            RegionDistribution = regionDistribution.ToDictionary(r => r.Region, r => r.Count),
            StatusDistribution = statusDistribution.ToDictionary(s => s.Status, s => s.Count),
            GeneratedAt = DateTime.UtcNow
        });
    }

    [HttpGet("system-health")]
    public async Task<ActionResult<SystemHealth>> GetSystemHealth()
    {
        var process = Process.GetCurrentProcess();
        var canConnectDb = await _context.Database.CanConnectAsync();

        return Ok(new SystemHealth
        {
            DatabaseConnected = canConnectDb,
            ServerUptime = (DateTime.UtcNow - process.StartTime.ToUniversalTime()).TotalHours,
            MemoryUsageMb = process.WorkingSet64 / 1024.0 / 1024.0,
            ProcessorTime = process.TotalProcessorTime.TotalSeconds,
            ThreadCount = process.Threads.Count,
            CheckedAt = DateTime.UtcNow
        });
    }

    [HttpPost("seed-data")]
    public async Task<IActionResult> SeedData()
    {
        var glacierCount = await _context.Glaciers.CountAsync();
        if (glacierCount > 0)
            return BadRequest("Database already contains data. Clear before re-seeding.");

        await SeedDataAsync();
        _logger.LogInformation("Database seeded via admin endpoint");
        return Ok(new { message = "Data seeded successfully" });
    }

    [HttpPost("recalculate-trends")]
    public async Task<IActionResult> RecalculateTrends()
    {
        var glaciers = await _context.Glaciers
            .Where(g => g.IsActive)
            .Select(g => g.Id)
            .ToListAsync();

        var processedCount = 0;
        foreach (var glacierId in glaciers)
        {
            var trendSummary = await _trendService.CalculateTrendSummaryAsync(glacierId);
            if (trendSummary != null) processedCount++;
        }

        _logger.LogInformation("Trends recalculated for {Count} glaciers", processedCount);
        return Ok(new { processedCount, totalGlaciers = glaciers.Count });
    }

    [HttpGet("audit-log")]
    public async Task<ActionResult<List<AuditLogEntry>>> GetAuditLog([FromQuery] int limit = 100)
    {
        var audits = await _context.AuditLogs
            .OrderByDescending(a => a.Timestamp)
            .Take(limit)
            .ToListAsync();
        return Ok(audits);
    }

    private async Task SeedDataAsync()
    {
        if (!await _context.Users.AnyAsync())
        {
            _context.Users.Add(new User
            {
                Id = Guid.Parse("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                Username = "admin",
                Email = "admin@glacierkz.kz",
                PasswordHash = BCrypt.Net.BCrypt.HashPassword("Admin123!"),
                Salt = string.Empty,
                Role = UserRole.Admin,
                Organization = "GlacierNET-KZ Research Institute",
                IsActive = true
            });
        }

        await _context.SaveChangesAsync();
    }
}

public class AdminDashboard
{
    public int TotalGlaciers { get; set; }
    public int TotalImages { get; set; }
    public int TotalAnalyses { get; set; }
    public int TotalUsers { get; set; }
    public int TotalTasks { get; set; }
    public int TotalAnomalies { get; set; }
    public int ActiveTasks { get; set; }
    public double ServerUptime { get; set; }
    public object RecentGlacierUpdates { get; set; } = new();
    public object RecentAnalyses { get; set; } = new();
    public object ActiveTasksList { get; set; } = new();
    public Dictionary<string, int> RegionDistribution { get; set; } = new();
    public Dictionary<string, int> StatusDistribution { get; set; } = new();
    public DateTime GeneratedAt { get; set; }
}

public class SystemHealth
{
    public bool DatabaseConnected { get; set; }
    public double ServerUptime { get; set; }
    public double MemoryUsageMb { get; set; }
    public double ProcessorTime { get; set; }
    public int ThreadCount { get; set; }
    public DateTime CheckedAt { get; set; }
}
