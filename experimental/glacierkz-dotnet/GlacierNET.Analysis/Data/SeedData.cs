using Microsoft.EntityFrameworkCore;
using GlacierNET.Analysis.Models;

namespace GlacierNET.Analysis.Data;

public static class SeedData
{
    public static async Task InitializeAsync(IServiceProvider serviceProvider)
    {
        using var scope = serviceProvider.CreateScope();
        var context = scope.ServiceProvider.GetRequiredService<GlacierDbContext>();

        if (await context.Users.AnyAsync()) return;

        context.Users.AddRange(
            new User
            {
                Id = Guid.Parse("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                Username = "admin",
                Email = "admin@glacierkz.kz",
                PasswordHash = BCrypt.Net.BCrypt.HashPassword("Admin123!"),
                Salt = string.Empty,
                FullName = "System Administrator",
                Organization = "GlacierNET-KZ",
                Role = UserRole.Admin,
                IsAdmin = true,
                IsActive = true,
                CreatedAt = DateTime.UtcNow,
                UpdatedAt = DateTime.UtcNow
            },
            new User
            {
                Id = Guid.Parse("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                Username = "researcher1",
                Email = "researcher@glacierkz.kz",
                PasswordHash = BCrypt.Net.BCrypt.HashPassword("Research123!"),
                Salt = string.Empty,
                FullName = "Dr. Aigul Zhakupova",
                Organization = "Institute of Geography",
                Role = UserRole.Researcher,
                IsAdmin = false,
                IsActive = true,
                CreatedAt = DateTime.UtcNow,
                UpdatedAt = DateTime.UtcNow
            }
        );

        var glacierIds = new[]
        {
            Guid.Parse("11111111-1111-1111-1111-111111111111"),
            Guid.Parse("22222222-2222-2222-2222-222222222222"),
            Guid.Parse("33333333-3333-3333-3333-333333333333")
        };
        var analysisTypes = new[] { AnalysisType.MassBalance, AnalysisType.AreaChange, AnalysisType.SurfaceTemperature };
        var random = new Random(42);

        foreach (var glacierId in glacierIds)
        {
            foreach (var analysisType in analysisTypes)
            {
                for (int year = 2015; year <= 2024; year++)
                {
                    context.TrendDataPoints.Add(new TrendData
                    {
                        Id = Guid.NewGuid(),
                        GlacierId = glacierId,
                        AnalysisType = analysisType,
                        MeasurementDate = new DateTime(year, 8, 15),
                        Value = analysisType switch
                        {
                            AnalysisType.MassBalance => -0.5 - random.NextDouble() * 1.5 + (year - 2015) * 0.02,
                            AnalysisType.AreaChange => -0.02 - random.NextDouble() * 0.05 + (year - 2015) * 0.001,
                            _ => 5.0 + random.NextDouble() * 10 - (year - 2015) * 0.1
                        },
                        Unit = analysisType switch
                        {
                            AnalysisType.MassBalance => "m w.e.",
                            AnalysisType.AreaChange => "km²",
                            _ => "°C"
                        },
                        Uncertainty = random.NextDouble() * 0.3,
                        DataPointCount = random.Next(50, 500),
                        DataSource = "Landsat-8",
                        QualityFlag = random.Next(2, 5),
                        Latitude = 43.0 + random.NextDouble() * 0.5,
                        Longitude = 77.0 + random.NextDouble() * 0.5,
                        Elevation = 3500 + random.NextDouble() * 700,
                        CreatedAt = DateTime.UtcNow
                    });
                }

                context.AnalysisResults.Add(new AnalysisResult
                {
                    Id = Guid.NewGuid(),
                    GlacierId = glacierId,
                    AnalysisType = analysisType,
                    AnalysisDate = DateTime.UtcNow.AddDays(-random.Next(1, 30)),
                    PeriodStart = new DateTime(2023, 1, 1),
                    PeriodEnd = new DateTime(2023, 12, 31),
                    Value = analysisType switch
                    {
                        AnalysisType.MassBalance => -0.8 + random.NextDouble() * 0.4,
                        AnalysisType.AreaChange => -0.03 + random.NextDouble() * 0.02,
                        _ => 8.5
                    },
                    Unit = analysisType switch
                    {
                        AnalysisType.MassBalance => "m w.e.",
                        AnalysisType.AreaChange => "km²",
                        _ => "°C"
                    },
                    ConfidenceScore = 0.85 + random.NextDouble() * 0.1,
                    Methodology = "Satellite remote sensing with ground truth validation",
                    IsAnomaly = random.NextDouble() > 0.85,
                    CreatedAt = DateTime.UtcNow
                });
            }
        }

        context.ProcessingTasks.AddRange(
            new ProcessingTask
            {
                Id = Guid.NewGuid(),
                Name = "Sentinel-2 Image Processing",
                Description = "Process latest Sentinel-2 images for all glaciers",
                TaskType = "ImageProcessing",
                Status = TaskStatusType.Completed,
                ProgressPercent = 100,
                TotalItems = 15,
                CompletedItems = 15,
                StartedAt = DateTime.UtcNow.AddHours(-4),
                CompletedAt = DateTime.UtcNow.AddHours(-2),
                RequestedBy = "admin",
                CreatedAt = DateTime.UtcNow.AddHours(-5),
                UpdatedAt = DateTime.UtcNow.AddHours(-2)
            },
            new ProcessingTask
            {
                Id = Guid.NewGuid(),
                Name = "Annual Mass Balance Analysis",
                Description = "Compute mass balance for 2024 across all glaciers",
                TaskType = "MassBalanceAnalysis",
                Status = TaskStatusType.Running,
                ProgressPercent = 45,
                TotalItems = 3,
                CompletedItems = 1,
                StartedAt = DateTime.UtcNow.AddMinutes(-30),
                EstimatedDurationSeconds = 3600,
                RequestedBy = "researcher1",
                CreatedAt = DateTime.UtcNow.AddMinutes(-45),
                UpdatedAt = DateTime.UtcNow
            }
        );

        context.Reports.Add(new Report
        {
            Id = Guid.NewGuid(),
            Title = "2024 Q1 Glacier Status Summary",
            Description = "Quarterly summary of glacier monitoring activities",
            ReportType = ReportType.AnnualSummary,
            Format = ExportFormat.Json,
            GeneratedAt = DateTime.UtcNow.AddDays(-5),
            GeneratedBy = "admin",
            IsPublic = true,
            ContentType = "application/json",
            Status = "Generated",
            CreatedAt = DateTime.UtcNow.AddDays(-5)
        });

        await context.SaveChangesAsync();
    }

    private static string BCryptHash(string password)
    {
        return BCrypt.Net.BCrypt.HashPassword(password);
    }
}
