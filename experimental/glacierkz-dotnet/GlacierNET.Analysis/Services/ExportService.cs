using System.Globalization;
using System.Text;
using System.Text.Json;
using CsvHelper;
using CsvHelper.Configuration;
using Microsoft.EntityFrameworkCore;
using NetTopologySuite.IO;
using GlacierNET.Analysis.Data;
using GlacierNET.Analysis.Models;

namespace GlacierNET.Analysis.Services;

public class ExportService
{
    private readonly GlacierDbContext _context;
    private readonly ILogger<ExportService> _logger;

    public ExportService(GlacierDbContext context, ILogger<ExportService> logger)
    {
        _context = context;
        _logger = logger;
    }

    public async Task<byte[]> ExportGlaciersAsync(ExportFormat format, List<Guid>? glacierIds = null)
    {
        var query = _context.Glaciers.Where(g => g.IsActive).AsNoTracking();
        if (glacierIds?.Count > 0)
            query = query.Where(g => glacierIds.Contains(g.Id));

        var glaciers = await query.ToListAsync();

        return format switch
        {
            ExportFormat.Csv => ExportCsv(glaciers),
            ExportFormat.Json => ExportJson(glaciers),
            ExportFormat.GeoJson => ExportGeoJson(glaciers),
            ExportFormat.Kml => ExportKml(glaciers),
            _ => throw new ArgumentOutOfRangeException(nameof(format))
        };
    }

    public async Task<byte[]> ExportAnalysisResultsAsync(
        ExportFormat format,
        Guid? glacierId = null,
        AnalysisType? type = null,
        DateTime? from = null,
        DateTime? to = null)
    {
        var query = _context.AnalysisResults
            .Include(a => a.Glacier)
            .AsNoTracking();

        if (glacierId.HasValue) query = query.Where(a => a.GlacierId == glacierId.Value);
        if (type.HasValue) query = query.Where(a => a.AnalysisType == type.Value);
        if (from.HasValue) query = query.Where(a => a.AnalysisDate >= from.Value);
        if (to.HasValue) query = query.Where(a => a.AnalysisDate <= to.Value);

        var results = await query.OrderByDescending(a => a.AnalysisDate).ToListAsync();

        return format switch
        {
            ExportFormat.Csv => ExportAnalysisCsv(results),
            ExportFormat.Json => ExportJson(results),
            _ => throw new ArgumentOutOfRangeException(nameof(format))
        };
    }

    public async Task<byte[]> ExportTrendDataAsync(
        ExportFormat format,
        Guid glacierId,
        AnalysisType type,
        DateTime? startDate = null,
        DateTime? endDate = null)
    {
        var query = _context.TrendDataPoints
            .Where(t => t.GlacierId == glacierId && t.AnalysisType == type)
            .AsNoTracking();

        if (startDate.HasValue) query = query.Where(t => t.MeasurementDate >= startDate.Value);
        if (endDate.HasValue) query = query.Where(t => t.MeasurementDate <= endDate.Value);

        var data = await query.OrderBy(t => t.MeasurementDate).ToListAsync();

        return format switch
        {
            ExportFormat.Csv => ExportTrendCsv(data),
            ExportFormat.Json => ExportJson(data),
            _ => throw new ArgumentOutOfRangeException(nameof(format))
        };
    }

    private static byte[] ExportCsv(List<Glacier> glaciers)
    {
        using var memoryStream = new MemoryStream();
        using var writer = new StreamWriter(memoryStream, Encoding.UTF8);
        using var csv = new CsvWriter(writer, new CsvConfiguration(CultureInfo.InvariantCulture));

        csv.Context.RegisterClassMap<GlacierMap>();
        csv.WriteRecords(glaciers);
        writer.Flush();
        return memoryStream.ToArray();
    }

    private static byte[] ExportAnalysisCsv(List<AnalysisResult> results)
    {
        using var memoryStream = new MemoryStream();
        using var writer = new StreamWriter(memoryStream, Encoding.UTF8);
        using var csv = new CsvWriter(writer, new CsvConfiguration(CultureInfo.InvariantCulture));

        csv.Context.RegisterClassMap<AnalysisResultMap>();
        csv.WriteRecords(results);
        writer.Flush();
        return memoryStream.ToArray();
    }

    private static byte[] ExportTrendCsv(List<TrendData> data)
    {
        using var memoryStream = new MemoryStream();
        using var writer = new StreamWriter(memoryStream, Encoding.UTF8);
        using var csv = new CsvWriter(writer, new CsvConfiguration(CultureInfo.InvariantCulture));

        csv.Context.RegisterClassMap<TrendDataMap>();
        csv.WriteRecords(data);
        writer.Flush();
        return memoryStream.ToArray();
    }

    private static byte[] ExportJson(object data)
    {
        var json = JsonSerializer.Serialize(data, new JsonSerializerOptions
        {
            WriteIndented = true,
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase
        });
        return Encoding.UTF8.GetBytes(json);
    }

    private static byte[] ExportGeoJson(List<Glacier> glaciers)
    {
        var features = new List<GeoJsonFeature>();
        var geoJsonWriter = new GeoJsonWriter();

        foreach (var glacier in glaciers)
        {
            var feature = new GeoJsonFeature
            {
                Type = "Feature",
                Properties = new Dictionary<string, object>
                {
                    ["id"] = glacier.Id,
                    ["name"] = glacier.Name,
                    ["localName"] = glacier.LocalName ?? "",
                    ["region"] = glacier.Region,
                    ["country"] = glacier.Country,
                    ["mountainRange"] = glacier.MountainRange ?? "",
                    ["areaKm2"] = glacier.AreaKm2,
                    ["lengthKm"] = glacier.LengthKm,
                    ["elevationMin"] = glacier.ElevationMin,
                    ["elevationMax"] = glacier.ElevationMax,
                    ["elevationMean"] = glacier.ElevationMean,
                    ["status"] = glacier.Status.ToString(),
                    ["orientation"] = glacier.Orientation
                },
                Geometry = glacier.Geometry != null
                    ? JsonSerializer.Deserialize<GeoJsonGeometry>(geoJsonWriter.Write(glacier.Geometry))
                    : null
            };
            features.Add(feature);
        }

        var geoJson = new GeoJsonFeatureCollection
        {
            Type = "FeatureCollection",
            Features = features
        };

        return Encoding.UTF8.GetBytes(JsonSerializer.Serialize(geoJson, new JsonSerializerOptions
        {
            WriteIndented = true,
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase
        }));
    }

    private static byte[] ExportKml(List<Glacier> glaciers)
    {
        var sb = new StringBuilder();
        sb.AppendLine("<?xml version=\"1.0\" encoding=\"UTF-8\"?>");
        sb.AppendLine("<kml xmlns=\"http://www.opengis.net/kml/2.2\">");
        sb.AppendLine("  <Document>");
        sb.AppendLine("    <name>GlacierNET-KZ Glaciers</name>");
        sb.AppendLine("    <description>Glacier monitoring data from GlacierNET-KZ platform</description>");

        foreach (var glacier in glaciers)
        {
            sb.AppendLine("    <Placemark>");
            sb.AppendLine($"      <name>{SecurityElement.Escape(glacier.Name)}</name>");
            sb.AppendLine($"      <description><![CDATA[");
            sb.AppendLine($"        Region: {glacier.Region}<br/>");
            sb.AppendLine($"        Area: {glacier.AreaKm2:F2} km²<br/>");
            sb.AppendLine($"        Elevation: {glacier.ElevationMin:F0}–{glacier.ElevationMax:F0} m<br/>");
            sb.AppendLine($"        Status: {glacier.Status}<br/>");
            sb.AppendLine($"      ]]></description>");
            if (glacier.CenterPoint != null)
            {
                sb.AppendLine($"      <Point>");
                sb.AppendLine($"        <coordinates>{glacier.CenterPoint.X},{glacier.CenterPoint.Y},{glacier.ElevationMean}</coordinates>");
                sb.AppendLine($"      </Point>");
            }
            sb.AppendLine("    </Placemark>");
        }

        sb.AppendLine("  </Document>");
        sb.AppendLine("</kml>");
        return Encoding.UTF8.GetBytes(sb.ToString());
    }
}

public class GeoJsonFeature
{
    public string Type { get; set; } = "Feature";
    public Dictionary<string, object> Properties { get; set; } = new();
    public GeoJsonGeometry? Geometry { get; set; }
}

public class GeoJsonGeometry
{
    public string Type { get; set; } = string.Empty;
    public object? Coordinates { get; set; }
}

public class GeoJsonFeatureCollection
{
    public string Type { get; set; } = "FeatureCollection";
    public List<GeoJsonFeature> Features { get; set; } = new();
}

public class GlacierMap : ClassMap<Glacier>
{
    public GlacierMap()
    {
        Map(m => m.Id).Name("id");
        Map(m => m.Name).Name("name");
        Map(m => m.LocalName).Name("local_name");
        Map(m => m.Region).Name("region");
        Map(m => m.Country).Name("country");
        Map(m => m.MountainRange).Name("mountain_range");
        Map(m => m.AreaKm2).Name("area_km2");
        Map(m => m.LengthKm).Name("length_km");
        Map(m => m.ElevationMin).Name("elevation_min");
        Map(m => m.ElevationMax).Name("elevation_max");
        Map(m => m.ElevationMean).Name("elevation_mean");
        Map(m => m.Status).Name("status");
        Map(m => m.Orientation).Name("orientation");
        Map(m => m.CreatedAt).Name("created_at");
    }
}

public class AnalysisResultMap : ClassMap<AnalysisResult>
{
    public AnalysisResultMap()
    {
        Map(m => m.Id).Name("id");
        Map(m => m.GlacierId).Name("glacier_id");
        Map(m => m.AnalysisType).Name("analysis_type");
        Map(m => m.AnalysisDate).Name("analysis_date");
        Map(m => m.Value).Name("value");
        Map(m => m.Unit).Name("unit");
        Map(m => m.PreviousValue).Name("previous_value");
        Map(m => m.ChangePercent).Name("change_percent");
        Map(m => m.ConfidenceScore).Name("confidence_score");
        Map(m => m.IsAnomaly).Name("is_anomaly");
    }
}

public class TrendDataMap : ClassMap<TrendData>
{
    public TrendDataMap()
    {
        Map(m => m.Id).Name("id");
        Map(m => m.GlacierId).Name("glacier_id");
        Map(m => m.AnalysisType).Name("analysis_type");
        Map(m => m.MeasurementDate).Name("measurement_date");
        Map(m => m.Value).Name("value");
        Map(m => m.Unit).Name("unit");
        Map(m => m.Uncertainty).Name("uncertainty");
        Map(m => m.DataPointCount).Name("data_point_count");
        Map(m => m.DataSource).Name("data_source");
        Map(m => m.QualityFlag).Name("quality_flag");
    }
}
