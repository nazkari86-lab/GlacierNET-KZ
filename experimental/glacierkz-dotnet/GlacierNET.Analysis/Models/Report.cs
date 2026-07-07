using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace GlacierNET.Analysis.Models;

[Table("reports")]
public class Report
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; } = Guid.NewGuid();

    [Required]
    [MaxLength(200)]
    [Column("title")]
    public string Title { get; set; } = string.Empty;

    [MaxLength(2000)]
    [Column("description")]
    public string? Description { get; set; }

    [Required]
    [Column("report_type")]
    public ReportType ReportType { get; set; }

    [Required]
    [Column("format")]
    public ExportFormat Format { get; set; } = ExportFormat.Json;

    [Column("generated_at")]
    public DateTime GeneratedAt { get; set; } = DateTime.UtcNow;

    [Column("period_start")]
    public DateTime? PeriodStart { get; set; }

    [Column("period_end")]
    public DateTime? PeriodEnd { get; set; }

    [MaxLength(200)]
    [Column("generated_by")]
    public string? GeneratedBy { get; set; }

    [Column("file_path")]
    [MaxLength(500)]
    public string? FilePath { get; set; }

    [Column("file_size_bytes")]
    public long FileSizeBytes { get; set; }

    [MaxLength(100)]
    [Column("file_content_type")]
    public string ContentType { get; set; } = "application/json";

    [Column("is_public")]
    public bool IsPublic { get; set; }

    [Column("glacier_ids_json")]
    public string? GlacierIdsJson { get; set; }

    [Column("parameters_json")]
    public string? ParametersJson { get; set; }

    [Column("summary_json")]
    public string? SummaryJson { get; set; }

    [Column("created_at")]
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [Column("expires_at")]
    public DateTime? ExpiresAt { get; set; }

    [Column("download_count")]
    public int DownloadCount { get; set; }

    [Column("status")]
    [MaxLength(50)]
    public string Status { get; set; } = "Generated";

    [NotMapped]
    public bool IsExpired => ExpiresAt.HasValue && ExpiresAt.Value < DateTime.UtcNow;

    [NotMapped]
    public string HumanReadableSize => FormatBytes(FileSizeBytes);

    [NotMapped]
    public string ReportTypeDisplayName => ReportType switch
    {
        ReportType.AnnualSummary => "Annual Glacier Summary",
        ReportType.TrendAnalysis => "Trend Analysis Report",
        ReportType.AnomalyDetection => "Anomaly Detection Report",
        ReportType.ComparisonReport => "Glacier Comparison Report",
        ReportType.ComplianceReport => "Compliance & Standards Report",
        _ => ReportType.ToString()
    };

    private static string FormatBytes(long bytes)
    {
        string[] sizes = ["B", "KB", "MB", "GB"];
        double len = bytes;
        int order = 0;
        while (len >= 1024 && order < sizes.Length - 1)
        {
            order++;
            len /= 1024;
        }
        return $"{len:0.##} {sizes[order]}";
    }
}
