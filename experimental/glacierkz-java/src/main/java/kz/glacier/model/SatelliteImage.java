package kz.glacier.model;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.annotations.Type;
import org.hibernate.spatial.JTSGeometryType;
import org.locationtech.jts.geom.Geometry;

import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;

@Entity
@Table(name = "satellite_images", indexes = {
        @Index(name = "idx_satellite_glacier", columnList = "glacier_id"),
        @Index(name = "idx_satellite_date", columnList = "capture_date"),
        @Index(name = "idx_satellite_source", columnList = "data_source"),
        @Index(name = "idx_satellite_status", columnList = "processing_status")
})
public class SatelliteImage {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "image_name", nullable = false, length = 255)
    private String imageName;

    @Column(name = "file_path", nullable = false, length = 500)
    private String filePath;

    @Column(name = "file_size_bytes")
    private Long fileSizeBytes;

    @Column(name = "file_format", length = 20)
    private String fileFormat = "GEOTIFF";

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "glacier_id")
    private Glacier glacier;

    @Column(name = "data_source", nullable = false, length = 50)
    private String dataSource;

    @Column(name = "satellite_name", length = 50)
    private String satelliteName;

    @Column(name = "band_count")
    private Integer bandCount;

    @Column(name = "spatial_resolution_m")
    private Double spatialResolutionM;

    @Column(name = "capture_date")
    private LocalDate captureDate;

    @Column(name = "capture_time")
    private Instant captureTime;

    @Type(JTSGeometryType.class)
    @Column(name = "footprint", columnDefinition = "geometry(Geometry, 4326)")
    private Geometry footprint;

    @Column(name = "cloud_cover_percent")
    private Double cloudCoverPercent;

    @Column(name = "snow_cover_percent")
    private Double snowCoverPercent;

    @Column(name = "processing_status", nullable = false, length = 30)
    private String processingStatus;

    @Column(name = "processing_error", length = 2000)
    private String processingError;

    @Column(name = "ndvi_min")
    private Double ndviMin;

    @Column(name = "ndvi_max")
    private Double ndviMax;

    @Column(name = "ndvi_mean")
    private Double ndviMean;

    @Column(name = "brightness_temp_min")
    private Double brightnessTempMin;

    @Column(name = "brightness_temp_max")
    private Double brightnessTempMax;

    @Column(name = "epsg_code", length = 10)
    private String epsgCode = "EPSG:4326";

    @Column(name = "width_pixels")
    private Integer widthPixels;

    @Column(name = "height_pixels")
    private Integer heightPixels;

    @Column(name = "bits_per_pixel")
    private Integer bitsPerPixel;

    @Column(name = "checksum_sha256", length = 64)
    private String checksumSha256;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private Instant createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private Instant updatedAt;

    @Version
    private Long version;

    public SatelliteImage() {
        this.processingStatus = "PENDING";
    }

    public SatelliteImage(String imageName, String filePath, String dataSource) {
        this();
        this.imageName = imageName;
        this.filePath = filePath;
        this.dataSource = dataSource;
    }

    public void markProcessing() {
        this.processingStatus = "PROCESSING";
    }

    public void markCompleted() {
        this.processingStatus = "COMPLETED";
    }

    public void markFailed(String error) {
        this.processingStatus = "FAILED";
        this.processingError = error;
    }

    public boolean isHighResolution() {
        return spatialResolutionM != null && spatialResolutionM <= 10.0;
    }

    public boolean isCloudFree() {
        return cloudCoverPercent != null && cloudCoverPercent < 10.0;
    }

    public boolean isRecentlyCaptured() {
        if (captureDate == null) return false;
        return captureDate.isAfter(LocalDate.now().minusMonths(6));
    }

    // Getters and Setters
    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public String getImageName() { return imageName; }
    public void setImageName(String imageName) { this.imageName = imageName; }

    public String getFilePath() { return filePath; }
    public void setFilePath(String filePath) { this.filePath = filePath; }

    public Long getFileSizeBytes() { return fileSizeBytes; }
    public void setFileSizeBytes(Long fileSizeBytes) { this.fileSizeBytes = fileSizeBytes; }

    public String getFileFormat() { return fileFormat; }
    public void setFileFormat(String fileFormat) { this.fileFormat = fileFormat; }

    public Glacier getGlacier() { return glacier; }
    public void setGlacier(Glacier glacier) { this.glacier = glacier; }

    public String getDataSource() { return dataSource; }
    public void setDataSource(String dataSource) { this.dataSource = dataSource; }

    public String getSatelliteName() { return satelliteName; }
    public void setSatelliteName(String satelliteName) { this.satelliteName = satelliteName; }

    public Integer getBandCount() { return bandCount; }
    public void setBandCount(Integer bandCount) { this.bandCount = bandCount; }

    public Double getSpatialResolutionM() { return spatialResolutionM; }
    public void setSpatialResolutionM(Double spatialResolutionM) { this.spatialResolutionM = spatialResolutionM; }

    public LocalDate getCaptureDate() { return captureDate; }
    public void setCaptureDate(LocalDate captureDate) { this.captureDate = captureDate; }

    public Instant getCaptureTime() { return captureTime; }
    public void setCaptureTime(Instant captureTime) { this.captureTime = captureTime; }

    public Geometry getFootprint() { return footprint; }
    public void setFootprint(Geometry footprint) { this.footprint = footprint; }

    public Double getCloudCoverPercent() { return cloudCoverPercent; }
    public void setCloudCoverPercent(Double cloudCoverPercent) { this.cloudCoverPercent = cloudCoverPercent; }

    public Double getSnowCoverPercent() { return snowCoverPercent; }
    public void setSnowCoverPercent(Double snowCoverPercent) { this.snowCoverPercent = snowCoverPercent; }

    public String getProcessingStatus() { return processingStatus; }
    public void setProcessingStatus(String processingStatus) { this.processingStatus = processingStatus; }

    public String getProcessingError() { return processingError; }
    public void setProcessingError(String processingError) { this.processingError = processingError; }

    public Double getNdviMin() { return ndviMin; }
    public void setNdviMin(Double ndviMin) { this.ndviMin = ndviMin; }

    public Double getNdviMax() { return ndviMax; }
    public void setNdviMax(Double ndviMax) { this.ndviMax = ndviMax; }

    public Double getNdviMean() { return ndviMean; }
    public void setNdviMean(Double ndviMean) { this.ndviMean = ndviMean; }

    public Double getBrightnessTempMin() { return brightnessTempMin; }
    public void setBrightnessTempMin(Double brightnessTempMin) { this.brightnessTempMin = brightnessTempMin; }

    public Double getBrightnessTempMax() { return brightnessTempMax; }
    public void setBrightnessTempMax(Double brightnessTempMax) { this.brightnessTempMax = brightnessTempMax; }

    public String getEpsgCode() { return epsgCode; }
    public void setEpsgCode(String epsgCode) { this.epsgCode = epsgCode; }

    public Integer getWidthPixels() { return widthPixels; }
    public void setWidthPixels(Integer widthPixels) { this.widthPixels = widthPixels; }

    public Integer getHeightPixels() { return heightPixels; }
    public void setHeightPixels(Integer heightPixels) { this.heightPixels = heightPixels; }

    public Integer getBitsPerPixel() { return bitsPerPixel; }
    public void setBitsPerPixel(Integer bitsPerPixel) { this.bitsPerPixel = bitsPerPixel; }

    public String getChecksumSha256() { return checksumSha256; }
    public void setChecksumSha256(String checksumSha256) { this.checksumSha256 = checksumSha256; }

    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }

    public Long getVersion() { return version; }
    public void setVersion(Long version) { this.version = version; }
}
