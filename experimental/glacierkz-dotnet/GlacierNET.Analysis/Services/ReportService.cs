using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using GlacierNET.Analysis.Data;
using GlacierNET.Analysis.Models;

namespace GlacierNET.Analysis.Services;

public class ReportService
{
    private readonly GlacierDbContext _context;
    private readonly AnalysisService _analysisService;
    private readonly TrendService _trendService;
    private readonly ILogger<ReportService> _logger;

    public ReportService(
        GlacierDbContext context,
        AnalysisService analysisService,
        TrendService trendService,
        ILogger<ReportService> logger)
    {
        _context = context;
        _analysisService = analysisService;
        _trendService = trendService;
        _logger = logger;
    }

    public async Task<Report> GenerateReportAsync(
        ReportType reportType,
        string title,
        string? generatedBy = null,
        List<Guid>? glacierIds = null,
        DateTime? periodStart = null,
        DateTime? periodEnd = null)
    {
        var report = new Report
        {
            Id = Guid.NewGuid(),
            Title = title,
            ReportType = reportType,
            GeneratedAt = DateTime.UtcNow,
            GeneratedBy = generatedBy,
            PeriodStart = periodStart,
            PeriodEnd = periodEnd,
            CreatedAt = DateTime.UtcNow,
            Status = "Processing"
        };

        _context.Reports.Add(report);
        await _context.SaveChangesAsync();

        try
        {
            var content = reportType switch
            {
                ReportType.AnnualSummary => await GenerateAnnualSummaryAsync(glacierIds, periodStart, periodEnd),
                ReportType.TrendAnalysis => await GenerateTrendAnalysisReportAsync(glacierIds),
                ReportType.AnomalyDetection => await GenerateAnomalyReportAsync(glacierIds),
                ReportType.ComparisonReport => await GenerateComparisonReportAsync(glacierIds),
                _ => GenerateGenericReport()
            };

            var contentBytes = Encoding.UTF8.GetBytes(content);
            report.FileSizeBytes = contentBytes.Length;
            report.ContentType = "application/json";
            report.Status = "Generated";
            report.SummaryJson = content;

            await _context.SaveChangesAsync();
            _logger.LogInformation("Generated {Type} report: {Id}", reportType, report.Id);
            return report;
        }
        catch (Exception ex)
        {
            report.Status = "Failed";
            report.Description = $"Error: {ex.Message}";
            await _context.SaveChangesAsync();
            _logger.LogError(ex, "Failed to generate report {Id}", report.Id);
            throw;
        }
    }

    public async Task<string> GenerateHtmlReportAsync(Report report)
    {
        var sb = new StringBuilder();
        sb.AppendLine("<!DOCTYPE html>");
        sb.AppendLine("<html lang=\"en\">");
        sb.AppendLine("<head>");
        sb.AppendLine("  <meta charset=\"UTF-8\">");
        sb.AppendLine("  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">");
        sb.AppendLine($"  <title>{EscapeHtml(report.Title)}</title>");
        sb.AppendLine("  <style>");
        sb.AppendLine("    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background: #f5f7fa; color: #333; }");
        sb.AppendLine("    .container { max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }");
        sb.AppendLine("    h1 { color: #1a5276; border-bottom: 3px solid #2196F3; padding-bottom: 10px; }");
        sb.AppendLine("    h2 { color: #2c3e50; margin-top: 30px; }");
        sb.AppendLine("    .meta { background: #ecf0f1; padding: 15px; border-radius: 5px; margin-bottom: 20px; }");
        sb.AppendLine("    .meta span { display: inline-block; margin-right: 30px; }");
        sb.AppendLine("    .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }");
        sb.AppendLine("    .stat-card { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #2196F3; }");
        sb.AppendLine("    .stat-card .value { font-size: 2em; font-weight: bold; color: #2196F3; }");
        sb.AppendLine("    .stat-card .label { color: #666; margin-top: 5px; }");
        sb.AppendLine("    table { width: 100%; border-collapse: collapse; margin: 20px 0; }");
        sb.AppendLine("    th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }");
        sb.AppendLine("    th { background: #2196F3; color: white; }");
        sb.AppendLine("    tr:hover { background: #f5f5f5; }");
        sb.AppendLine("    .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #888; font-size: 0.9em; }");
        sb.AppendLine("  </style>");
        sb.AppendLine("</head>");
        sb.AppendLine("<body>");
        sb.AppendLine("<div class=\"container\">");
        sb.AppendLine($"  <h1>{EscapeHtml(report.Title)}</h1>");
        sb.AppendLine("  <div class=\"meta\">");
        sb.AppendLine($"    <span><strong>Type:</strong> {report.ReportTypeDisplayName}</span>");
        sb.AppendLine($"    <span><strong>Generated:</strong> {report.GeneratedAt:yyyy-MM-dd HH:mm} UTC</span>");
        sb.AppendLine($"    <span><strong>By:</strong> {EscapeHtml(report.GeneratedBy ?? "System")}</span>");
        sb.AppendLine("  </div>");

        if (!string.IsNullOrEmpty(report.Description))
            sb.AppendLine($"  <p>{EscapeHtml(report.Description)}</p>");

        if (!string.IsNullOrEmpty(report.SummaryJson))
        {
            try
            {
                var summary = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(report.SummaryJson);
                if (summary is not null)
                {
                    sb.AppendLine("  <h2>Summary Statistics</h2>");
                    sb.AppendLine("  <div class=\"stat-grid\">");
                    foreach (var kvp in summary)
                    {
                        sb.AppendLine("    <div class=\"stat-card\">");
                        sb.AppendLine($"      <div class=\"value">{kvp.Value}</div>");
                        sb.AppendLine($"      <div class=\"label">{EscapeHtml(kvp.Key)}</div>");
                        sb.AppendLine("    </div>");
                    }
                    sb.AppendLine("  </div>");
                }
            }
            catch
            {
                sb.AppendLine($"  <pre>{EscapeHtml(report.SummaryJson)}</pre>");
            }
        }

        sb.AppendLine($"  <div class=\"footer\">");
        sb.AppendLine($"    <p>GlacierNET-KZ Analytics Platform &copy; {DateTime.UtcNow.Year}</p>");
        sb.AppendLine($"    <p>Report ID: {report.Id}</p>");
        sb.AppendLine($"  </div>");
        sb.AppendLine("</div>");
        sb.AppendLine("</body>");
        sb.AppendLine("</html>");

        return sb.ToString();
    }

    public async Task<List<Report>> GetReportsAsync(ReportType? type = null, string? generatedBy = null, int page = 1, int pageSize = 20)
    {
        IQueryable<Report> query = _context.Reports.AsNoTracking();
        if (type.HasValue) query = query.Where(r => r.ReportType == type.Value);
        if (!string.IsNullOrEmpty(generatedBy)) query = query.Where(r => r.GeneratedBy == generatedBy);

        return await query
            .OrderByDescending(r => r.GeneratedAt)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync();
    }

    public async Task<Report?> GetReportByIdAsync(Guid id)
    {
        return await _context.Reports.AsNoTracking().FirstOrDefaultAsync(r => r.Id == id);
    }

    public async Task<bool> DeleteReportAsync(Guid id)
    {
        var report = await _context.Reports.FindAsync(id);
        if (report is null) return false;
        _context.Reports.Remove(report);
        await _context.SaveChangesAsync();
        return true;
    }

    private async Task<string> GenerateAnnualSummaryAsync(List<Guid>? glacierIds, DateTime? periodStart, DateTime? periodEnd)
    {
        var glaciers = await _context.Glaciers
            .Where(g => g.IsActive && (!glacierIds?.Any() == true || glacierIds.Contains(g.Id)))
            .ToListAsync();

        var stats = new Dictionary<string, object>
        {
            ["totalGlaciers"] = glaciers.Count,
            ["totalAreaKm2"] = glaciers.Sum(g => g.AreaKm2),
            ["averageAreaKm2"] = glaciers.Average(g => g.AreaKm2),
            ["retreatingCount"] = glaciers.Count(g => g.Status == GlacierStatus.Retreating),
            ["stableCount"] = glaciers.Count(g => g.Status == GlacierStatus.Stable),
            ["activeCount"] = glaciers.Count(g => g.Status == GlacierStatus.Active),
            ["periodStart"] = periodStart?.ToString("yyyy-MM-dd") ?? "N/A",
            ["periodEnd"] = periodEnd?.ToString("yyyy-MM-dd") ?? "N/A",
            ["generatedAt"] = DateTime.UtcNow.ToString("yyyy-MM-dd HH:mm:ss")
        };

        return JsonSerializer.Serialize(stats, new JsonSerializerOptions { WriteIndented = true });
    }

    private async Task<string> GenerateTrendAnalysisReportAsync(List<Guid>? glacierIds)
    {
        var ids = glacierIds ?? await _context.Glaciers.Where(g => g.IsActive).Select(g => g.Id).ToListAsync();
        var summaries = new List<object>();

        foreach (var id in ids.Take(20))
        {
            var summary = await _trendService.CalculateTrendSummaryAsync(id, AnalysisType.MassBalance);
            var glacier = await _context.Glaciers.FindAsync(id);
            summaries.Add(new
            {
                glacierName = glacier?.Name ?? "Unknown",
                glacierId = id,
                trendDirection = summary.TrendDirection,
                annualChangeRate = summary.AnnualChangeRate,
                rSquared = summary.RSquared,
                dataPoints = summary.DataPointCount,
                totalChange = summary.TotalChange
            });
        }

        return JsonSerializer.Serialize(new { trendAnalyses = summaries }, new JsonSerializerOptions { WriteIndented = true });
    }

    private async Task<string> GenerateAnomalyReportAsync(List<Guid>? glacierIds)
    {
        var anomalies = new List<object>();
        foreach (var glacierId in glacierIds ?? await _context.Glaciers.Where(g => g.IsActive).Select(g => g.Id).ToListAsync())
        {
            var results = await _analysisService.DetectAnomaliesAsync(glacierId);
            anomalies.AddRange(results.Select(r => new
            {
                glacierId,
                analysisType = r.AnalysisType.ToString(),
                value = r.Value,
                severity = r.AnomalySeverity?.ToString(),
                date = r.AnalysisDate
            }));
        }

        return JsonSerializer.Serialize(new { anomalies, totalAnomalies = anomalies.Count },
            new JsonSerializerOptions { WriteIndented = true });
    }

    private async Task<string> GenerateComparisonReportAsync(List<Guid>? glacierIds)
    {
        var ids = glacierIds?.Take(10).ToList() ?? await _context.Glaciers.Where(g => g.IsActive).Select(g => g.Id).Take(10).ToListAsync();
        var glaciers = await _context.Glaciers.Where(g => ids.Contains(g.Id)).ToListAsync();

        return JsonSerializer.Serialize(new
        {
            glaciers = glaciers.Select(g => new
            {
                g.Name,
                g.Region,
                g.AreaKm2,
                g.ElevationMin,
                g.ElevationMax,
                g.Status,
                g.LengthKm
            })
        }, new JsonSerializerOptions { WriteIndented = true });
    }

    private string GenerateGenericReport()
    {
        return JsonSerializer.Serialize(new
        {
            reportType = "Generic",
            generatedAt = DateTime.UtcNow,
            status = "Generated"
        }, new JsonSerializerOptions { WriteIndented = true });
    }

    private static string EscapeHtml(string input) =>
        System.Net.WebUtility.HtmlEncode(input);
}
