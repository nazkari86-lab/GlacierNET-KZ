package kz.glacier.model;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;

@Entity
@Table(name = "analysis_reports", indexes = {
        @Index(name = "idx_report_glacier", columnList = "glacier_id"),
        @Index(name = "idx_report_type", columnList = "report_type"),
        @Index(name = "idx_report_date", columnList = "report_date"),
        @Index(name = "idx_report_status", columnList = "status")
})
public class AnalysisReport {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "report_title", nullable = false, length = 255)
    private String reportTitle;

    @Column(name = "report_type", nullable = false, length = 50)
    private String reportType;

    @Column(name = "report_format", length = 20)
    private String reportFormat = "PDF";

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "glacier_id")
    private Glacier glacier;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "raster_job_id")
    private RasterJob rasterJob;

    @Column(name = "report_date")
    private LocalDate reportDate;

    @Column(name = "period_start")
    private LocalDate periodStart;

    @Column(name = "period_end")
    private LocalDate periodEnd;

    @Column(name = "status", nullable = false, length = 30)
    private String status;

    @Column(name = "file_path", length = 500)
    private String filePath;

    @Column(name = "file_size_bytes")
    private Long fileSizeBytes;

    @Column(name = "summary", columnDefinition = "text")
    private String summary;

    @Column(name = "key_findings", columnDefinition = "jsonb")
    private String keyFindings;

    @Column(name = "data_source_count")
    private Integer dataSourceCount;

    @Column(name = "total_images_analyzed")
    private Integer totalImagesAnalyzed;

    @Column(name = "area_analyzed_km2")
    private Double areaAnalyzedKm2;

    @Column(name = "change_detected")
    private Boolean changeDetected;

    @Column(name = "change_magnitude_percent")
    private Double changeMagnitudePercent;

    @Column(name = "trend_direction", length = 20)
    private String trendDirection;

    @Column(name = "confidence_score")
    private Double confidenceScore;

    @Column(name = "metadata_json", columnDefinition = "jsonb")
    private String metadataJson;

    @Column(name = "created_by_user_id")
    private UUID createdByUserId;

    @Column(name = "approved_by_user_id")
    private UUID approvedByUserId;

    @Column(name = "approved_at")
    private Instant approvedAt;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private Instant createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private Instant updatedAt;

    @Version
    private Long version;

    public AnalysisReport() {
        this.status = "DRAFT";
        this.reportDate = LocalDate.now();
    }

    public AnalysisReport(String reportTitle, String reportType, Glacier glacier) {
        this();
        this.reportTitle = reportTitle;
        this.reportType = reportType;
        this.glacier = glacier;
    }

    public void markGenerating() {
        this.status = "GENERATING";
    }

    public void markCompleted(String filePath, long fileSize) {
        this.status = "COMPLETED";
        this.filePath = filePath;
        this.fileSizeBytes = fileSize;
    }

    public void markFailed(String error) {
        this.status = "FAILED";
        this.summary = error;
    }

    public void approve(UUID approverUserId) {
        this.status = "APPROVED";
        this.approvedByUserId = approverUserId;
        this.approvedAt = Instant.now();
    }

    public boolean isRetreatReport() {
        return "RETREAT_ANALYSIS".equals(reportType);
    }

    public boolean isMassBalanceReport() {
        return "MASS_BALANCE".equals(reportType);
    }

    public boolean hasSignificantChange() {
        return changeDetected != null && changeDetected
                && changeMagnitudePercent != null && Math.abs(changeMagnitudePercent) > 5.0;
    }

    // Getters and Setters
    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public String getReportTitle() { return reportTitle; }
    public void setReportTitle(String reportTitle) { this.reportTitle = reportTitle; }

    public String getReportType() { return reportType; }
    public void setReportType(String reportType) { this.reportType = reportType; }

    public String getReportFormat() { return reportFormat; }
    public void setReportFormat(String reportFormat) { this.reportFormat = reportFormat; }

    public Glacier getGlacier() { return glacier; }
    public void setGlacier(Glacier glacier) { this.glacier = glacier; }

    public RasterJob getRasterJob() { return rasterJob; }
    public void setRasterJob(RasterJob rasterJob) { this.rasterJob = rasterJob; }

    public LocalDate getReportDate() { return reportDate; }
    public void setReportDate(LocalDate reportDate) { this.reportDate = reportDate; }

    public LocalDate getPeriodStart() { return periodStart; }
    public void setPeriodStart(LocalDate periodStart) { this.periodStart = periodStart; }

    public LocalDate getPeriodEnd() { return periodEnd; }
    public void setPeriodEnd(LocalDate periodEnd) { this.periodEnd = periodEnd; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public String getFilePath() { return filePath; }
    public void setFilePath(String filePath) { this.filePath = filePath; }

    public Long getFileSizeBytes() { return fileSizeBytes; }
    public void setFileSizeBytes(Long fileSizeBytes) { this.fileSizeBytes = fileSizeBytes; }

    public String getSummary() { return summary; }
    public void setSummary(String summary) { this.summary = summary; }

    public String getKeyFindings() { return keyFindings; }
    public void setKeyFindings(String keyFindings) { this.keyFindings = keyFindings; }

    public Integer getDataSourceCount() { return dataSourceCount; }
    public void setDataSourceCount(Integer dataSourceCount) { this.dataSourceCount = dataSourceCount; }

    public Integer getTotalImagesAnalyzed() { return totalImagesAnalyzed; }
    public void setTotalImagesAnalyzed(Integer totalImagesAnalyzed) { this.totalImagesAnalyzed = totalImagesAnalyzed; }

    public Double getAreaAnalyzedKm2() { return areaAnalyzedKm2; }
    public void setAreaAnalyzedKm2(Double areaAnalyzedKm2) { this.areaAnalyzedKm2 = areaAnalyzedKm2; }

    public Boolean getChangeDetected() { return changeDetected; }
    public void setChangeDetected(Boolean changeDetected) { this.changeDetected = changeDetected; }

    public Double getChangeMagnitudePercent() { return changeMagnitudePercent; }
    public void setChangeMagnitudePercent(Double changeMagnitudePercent) { this.changeMagnitudePercent = changeMagnitudePercent; }

    public String getTrendDirection() { return trendDirection; }
    public void setTrendDirection(String trendDirection) { this.trendDirection = trendDirection; }

    public Double getConfidenceScore() { return confidenceScore; }
    public void setConfidenceScore(Double confidenceScore) { this.confidenceScore = confidenceScore; }

    public String getMetadataJson() { return metadataJson; }
    public void setMetadataJson(String metadataJson) { this.metadataJson = metadataJson; }

    public UUID getCreatedByUserId() { return createdByUserId; }
    public void setCreatedByUserId(UUID createdByUserId) { this.createdByUserId = createdByUserId; }

    public UUID getApprovedByUserId() { return approvedByUserId; }
    public void setApprovedByUserId(UUID approvedByUserId) { this.approvedByUserId = approvedByUserId; }

    public Instant getApprovedAt() { return approvedAt; }
    public void setApprovedAt(Instant approvedAt) { this.approvedAt = approvedAt; }

    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }

    public Long getVersion() { return version; }
    public void setVersion(Long version) { this.version = version; }
}
