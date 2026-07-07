namespace GlacierNET.Analysis.Models;

public enum UserRole
{
    Viewer,
    Researcher,
    Admin
}

public enum TaskStatusType
{
    Queued,
    Pending,
    Running,
    Completed,
    Failed,
    Cancelled,
    Paused
}

public enum AnalysisType
{
    MassBalance,
    AreaChange,
    VelocityMapping,
    AlbedoAnalysis,
    SurfaceTemperature,
    ElevationChange,
    DebrisCover,
    LakeFormation
}

public enum GlacierStatus
{
    Active,
    Retreating,
    Advancing,
    Stable,
    Disappeared,
    Unknown
}

public enum ExportFormat
{
    Csv,
    Json,
    GeoJson,
    Kml
}

public enum ReportType
{
    AnnualSummary,
    TrendAnalysis,
    AnomalyDetection,
    ComparisonReport,
    ComplianceReport
}

public enum SeverityLevel
{
    Info,
    Warning,
    Critical,
    Emergency
}

public enum ImageSource
{
    Landsat8,
    Landsat9,
    Sentinel2,
    Sentinel1,
    Modis,
    Aster,
    Custom
}

public enum SensorType
{
    Optical,
    Radar,
    LiDAR,
    Thermal,
    Multispectral,
    Hyperspectral
}
