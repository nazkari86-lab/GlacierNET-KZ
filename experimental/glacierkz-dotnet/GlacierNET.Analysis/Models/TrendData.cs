using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace GlacierNET.Analysis.Models;

[Table("trend_data")]
public class TrendData
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

    [Required]
    [Column("measurement_date")]
    public DateTime MeasurementDate { get; set; }

    [Column("value")]
    public double Value { get; set; }

    [Column("unit")]
    [MaxLength(50)]
    public string Unit { get; set; } = string.Empty;

    [Column("uncertainty")]
    public double? Uncertainty { get; set; }

    [Column("data_point_count")]
    public int DataPointCount { get; set; }

    [Column("spatial_resolution_m")]
    public double? SpatialResolutionM { get; set; }

    [MaxLength(200)]
    [Column("data_source")]
    public string? DataSource { get; set; }

    [MaxLength(100)]
    [Column("processing_method")]
    public string? ProcessingMethod { get; set; }

    [Column("quality_flag")]
    public int QualityFlag { get; set; }

    [Column("latitude")]
    public double? Latitude { get; set; }

    [Column("longitude")]
    public double? Longitude { get; set; }

    [Column("elevation")]
    public double? Elevation { get; set; }

    [Column("metadata_json")]
    public string? MetadataJson { get; set; }

    [Column("created_at")]
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [NotMapped]
    public bool IsReliable => QualityFlag >= 2 && (Uncertainty ?? 0) < Value * 0.3;

    [NotMapped]
    public int Year => MeasurementDate.Year;

    [NotMapped]
    public int Month => MeasurementDate.Month;

    [NotMapped]
    public string SeasonalPeriod
    {
        get
        {
            return Month switch
            {
                12 or 1 or 2 => "Winter",
                3 or 4 or 5 => "Spring",
                6 or 7 or 8 => "Summer",
                9 or 10 or 11 => "Autumn",
                _ => "Unknown"
            };
        }
    }
}
