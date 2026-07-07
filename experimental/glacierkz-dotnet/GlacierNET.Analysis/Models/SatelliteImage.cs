using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace GlacierNET.Analysis.Models;

[Table("satellite_images")]
public class SatelliteImage
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
    [MaxLength(200)]
    [Column("file_path")]
    public string FilePath { get; set; } = string.Empty;

    [Required]
    [MaxLength(100)]
    [Column("file_name")]
    public string FileName { get; set; } = string.Empty;

    [Column("file_size_bytes")]
    public long FileSizeBytes { get; set; }

    [Required]
    [Column("capture_date")]
    public DateTime CaptureDate { get; set; }

    [Column("processing_date")]
    public DateTime? ProcessingDate { get; set; }

    [Required]
    [Column("image_source")]
    public ImageSource Source { get; set; }

    [Required]
    [Column("sensor_type")]
    public SensorType Sensor { get; set; }

    [Column("cloud_cover_percent")]
    public double CloudCoverPercent { get; set; }

    [Column("snow_cover_percent")]
    public double SnowCoverPercent { get; set; }

    [Column("spatial_resolution_m")]
    public double SpatialResolutionM { get; set; }

    [Column("epsg_code")]
    public int EpsgCode { get; set; } = 4326;

    [Column("min_latitude")]
    public double MinLatitude { get; set; }

    [Column("max_latitude")]
    public double MaxLatitude { get; set; }

    [Column("min_longitude")]
    public double MinLongitude { get; set; }

    [Column("max_longitude")]
    public double MaxLongitude { get; set; }

    [Column("bands_count")]
    public int BandsCount { get; set; }

    [MaxLength(500)]
    [Column("bands_description")]
    public string? BandsDescription { get; set; }

    [Column("quality_score")]
    public double QualityScore { get; set; }

    [Column("is_processed")]
    public bool IsProcessed { get; set; }

    [MaxLength(200)]
    [Column("processing_algorithm")]
    public string? ProcessingAlgorithm { get; set; }

    [Column("checksum_sha256")]
    [MaxLength(64)]
    public string? ChecksumSha256 { get; set; }

    [Column("created_at")]
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [Column("metadata_json")]
    public string? MetadataJson { get; set; }

    [NotMapped]
    public string HumanReadableSize => FormatBytes(FileSizeBytes);

    [NotMapped]
    public double CoverageAreaKm2 =>
        ((MaxLatitude - MinLatitude) * 111.32) * ((MaxLongitude - MinLongitude) * 111.32 * Math.Cos((MinLatitude + MaxLatitude) / 2 * Math.PI / 180));

    private static string FormatBytes(long bytes)
    {
        string[] sizes = ["B", "KB", "MB", "GB", "TB"];
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
