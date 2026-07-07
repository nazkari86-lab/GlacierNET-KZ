using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace GlacierNET.Analysis.Models;

[Table("analysis_results")]
public class AnalysisResult
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; } = Guid.NewGuid();

    [Required]
    [Column("glacier_id")]
    public Guid GlacierId { get; set; }

    [ForeignKey("GlacierId")]
    public Glacier? Glacier { get; set; }

    [Required]
    [Column("analysis_type")]
    public AnalysisType AnalysisType { get; set; }

    [Column("analysis_date")]
    public DateTime AnalysisDate { get; set; } = DateTime.UtcNow;

    [Column("period_start")]
    public DateTime PeriodStart { get; set; }

    [Column("period_end")]
    public DateTime PeriodEnd { get; set; }

    [Column("value")]
    public double Value { get; set; }

    [Column("unit")]
    [MaxLength(50)]
    public string Unit { get; set; } = string.Empty;

    [Column("previous_value")]
    public double? PreviousValue { get; set; }

    [Column("change_percent")]
    public double? ChangePercent { get; set; }

    [Column("confidence_score")]
    public double ConfidenceScore { get; set; }

    [Column("methodology")]
    [MaxLength(500)]
    public string? Methodology { get; set; }

    [Column("algorithm_version")]
    [MaxLength(50)]
    public string? AlgorithmVersion { get; set; }

    [Column("parameters_json")]
    public string? ParametersJson { get; set; }

    [Column("result_data_json")]
    public string? ResultDataJson { get; set; }

    [Column("is_anomaly")]
    public bool IsAnomaly { get; set; }

    [Column("anomaly_severity")]
    public SeverityLevel? AnomalySeverity { get; set; }

    [MaxLength(1000)]
    [Column("notes")]
    public string? Notes { get; set; }

    [Column("validated_by")]
    [MaxLength(200)]
    public string? ValidatedBy { get; set; }

    [Column("validated_at")]
    public DateTime? ValidatedAt { get; set; }

    [Column("created_at")]
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [NotMapped]
    public double? AbsoluteChange => PreviousValue.HasValue ? Value - PreviousValue.Value : null;

    [NotMapped]
    public string TrendIndicator
    {
        get
        {
            if (!ChangePercent.HasValue) return "—";
            return ChangePercent.Value switch
            {
                < -10 => "↓↓ Significant decrease",
                < -5 => "↓ Moderate decrease",
                < -1 => "↘ Slight decrease",
                < 1 => "→ Stable",
                < 5 => "↗ Slight increase",
                < 10 => "↑ Moderate increase",
                _ => "↑↑ Significant increase"
            };
        }
    }
}
