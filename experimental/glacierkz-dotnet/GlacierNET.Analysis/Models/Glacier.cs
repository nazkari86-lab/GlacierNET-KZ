using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using NetTopologySuite.Geometries;

namespace GlacierNET.Analysis.Models;

[Table("glaciers")]
public class Glacier
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; } = Guid.NewGuid();

    [Required]
    [MaxLength(200)]
    [Column("name")]
    public string Name { get; set; } = string.Empty;

    [MaxLength(500)]
    [Column("local_name")]
    public string? LocalName { get; set; }

    [Required]
    [MaxLength(100)]
    [Column("region")]
    public string Region { get; set; } = string.Empty;

    [Required]
    [MaxLength(100)]
    [Column("country")]
    public string Country { get; set; } = "Kazakhstan";

    [MaxLength(50)]
    [Column("mountain_range")]
    public string? MountainRange { get; set; }

    [Column("elevation_min")]
    public double ElevationMin { get; set; }

    [Column("elevation_max")]
    public double ElevationMax { get; set; }

    [Column("elevation_mean")]
    public double ElevationMean { get; set; }

    [Column("area_km2")]
    public double AreaKm2 { get; set; }

    [Column("length_km")]
    public double LengthKm { get; set; }

    [Column("orientation")]
    public double Orientation { get; set; }

    [Column("status")]
    public GlacierStatus Status { get; set; } = GlacierStatus.Unknown;

    [Column("geometry")]
    public MultiPolygon? Geometry { get; set; }

    [Column("center_point")]
    public Point? CenterPoint { get; set; }

    [MaxLength(1000)]
    [Column("description")]
    public string? Description { get; set; }

    [Column("discovered_date")]
    public DateTime? DiscoveredDate { get; set; }

    [Column("first_survey_date")]
    public DateTime? FirstSurveyDate { get; set; }

    [Column("created_at")]
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [Column("updated_at")]
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;

    [Column("is_active")]
    public bool IsActive { get; set; } = true;

    [MaxLength(100)]
    [Column("data_source")]
    public string? DataSource { get; set; }

    public ICollection<SatelliteImage> SatelliteImages { get; set; } = new List<SatelliteImage>();
    public ICollection<AnalysisResult> AnalysisResults { get; set; } = new List<AnalysisResult>();
    public ICollection<TrendData> TrendDataPoints { get; set; } = new List<TrendData>();

    [NotMapped]
    public double ElevationRange => ElevationMax - ElevationMin;

    [NotMapped]
    public double SlopeDegrees => LengthKm > 0
        ? Math.Atan2(ElevationMax - ElevationMin, LengthKm * 1000) * (180.0 / Math.PI)
        : 0;

    public override string ToString() =>
        $"{Name} ({Region}) — {AreaKm2:F2} km², Elev: {ElevationMin:F0}–{ElevationMax:F0}m, Status: {Status}";
}
