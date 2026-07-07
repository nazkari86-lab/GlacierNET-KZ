package kz.glacier.model;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "batch_results", indexes = {
        @Index(name = "idx_batch_result_job", columnList = "raster_job_id"),
        @Index(name = "idx_batch_result_status", columnList = "processing_status")
})
public class BatchResult {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "raster_job_id", nullable = false)
    private RasterJob rasterJob;

    @Column(name = "result_type", nullable = false, length = 50)
    private String resultType;

    @Column(name = "result_data", columnDefinition = "jsonb")
    private String resultData;

    @Column(name = "output_file_path", length = 500)
    private String outputFilePath;

    @Column(name = "output_file_size_bytes")
    private Long outputFileSizeBytes;

    @Column(name = "output_format", length = 20)
    private String outputFormat = "GEOTIFF";

    @Column(name = "processing_status", nullable = false, length = 30)
    private String processingStatus;

    @Column(name = "error_code", length = 50)
    private String errorCode;

    @Column(name = "error_message", length = 2000)
    private String errorMessage;

    @Column(name = "processing_time_ms")
    private Long processingTimeMs;

    @Column(name = "records_input")
    private Long recordsInput = 0L;

    @Column(name = "records_output")
    private Long recordsOutput = 0L;

    @Column(name = "records_failed")
    private Long recordsFailed = 0L;

    @Column(name = "checksum_sha256", length = 64)
    private String checksumSha256;

    @Column(name = "output_crs", length = 20)
    private String outputCrs = "EPSG:4326";

    @Column(name = "spatial_resolution_m")
    private Double spatialResolutionM;

    @Column(name = "pixel_count")
    private Long pixelCount;

    @Column(name = "min_value")
    private Double minValue;

    @Column(name = "max_value")
    private Double maxValue;

    @Column(name = "mean_value")
    private Double meanValue;

    @Column(name = "std_deviation")
    private Double stdDeviation;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private Instant createdAt;

    public BatchResult() {
        this.processingStatus = "PENDING";
    }

    public BatchResult(RasterJob rasterJob, String resultType) {
        this();
        this.rasterJob = rasterJob;
        this.resultType = resultType;
    }

    public void markCompleted(String outputPath, long fileSize) {
        this.processingStatus = "COMPLETED";
        this.outputFilePath = outputPath;
        this.outputFileSizeBytes = fileSize;
    }

    public void markFailed(String errorCode, String errorMessage) {
        this.processingStatus = "FAILED";
        this.errorCode = errorCode;
        this.errorMessage = errorMessage;
    }

    public boolean isCompleted() {
        return "COMPLETED".equals(processingStatus);
    }

    public boolean isFailed() {
        return "FAILED".equals(processingStatus);
    }

    public double getSuccessRate() {
        if (recordsInput == null || recordsInput == 0) return 0.0;
        long output = recordsOutput != null ? recordsOutput : 0;
        return (double) output / recordsInput * 100.0;
    }

    // Getters and Setters
    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public RasterJob getRasterJob() { return rasterJob; }
    public void setRasterJob(RasterJob rasterJob) { this.rasterJob = rasterJob; }

    public String getResultType() { return resultType; }
    public void setResultType(String resultType) { this.resultType = resultType; }

    public String getResultData() { return resultData; }
    public void setResultData(String resultData) { this.resultData = resultData; }

    public String getOutputFilePath() { return outputFilePath; }
    public void setOutputFilePath(String outputFilePath) { this.outputFilePath = outputFilePath; }

    public Long getOutputFileSizeBytes() { return outputFileSizeBytes; }
    public void setOutputFileSizeBytes(Long outputFileSizeBytes) { this.outputFileSizeBytes = outputFileSizeBytes; }

    public String getOutputFormat() { return outputFormat; }
    public void setOutputFormat(String outputFormat) { this.outputFormat = outputFormat; }

    public String getProcessingStatus() { return processingStatus; }
    public void setProcessingStatus(String processingStatus) { this.processingStatus = processingStatus; }

    public String getErrorCode() { return errorCode; }
    public void setErrorCode(String errorCode) { this.errorCode = errorCode; }

    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }

    public Long getProcessingTimeMs() { return processingTimeMs; }
    public void setProcessingTimeMs(Long processingTimeMs) { this.processingTimeMs = processingTimeMs; }

    public Long getRecordsInput() { return recordsInput; }
    public void setRecordsInput(Long recordsInput) { this.recordsInput = recordsInput; }

    public Long getRecordsOutput() { return recordsOutput; }
    public void setRecordsOutput(Long recordsOutput) { this.recordsOutput = recordsOutput; }

    public Long getRecordsFailed() { return recordsFailed; }
    public void setRecordsFailed(Long recordsFailed) { this.recordsFailed = recordsFailed; }

    public String getChecksumSha256() { return checksumSha256; }
    public void setChecksumSha256(String checksumSha256) { this.checksumSha256 = checksumSha256; }

    public String getOutputCrs() { return outputCrs; }
    public void setOutputCrs(String outputCrs) { this.outputCrs = outputCrs; }

    public Double getSpatialResolutionM() { return spatialResolutionM; }
    public void setSpatialResolutionM(Double spatialResolutionM) { this.spatialResolutionM = spatialResolutionM; }

    public Long getPixelCount() { return pixelCount; }
    public void setPixelCount(Long pixelCount) { this.pixelCount = pixelCount; }

    public Double getMinValue() { return minValue; }
    public void setMinValue(Double minValue) { this.minValue = minValue; }

    public Double getMaxValue() { return maxValue; }
    public void setMaxValue(Double maxValue) { this.maxValue = maxValue; }

    public Double getMeanValue() { return meanValue; }
    public void setMeanValue(Double meanValue) { this.meanValue = meanValue; }

    public Double getStdDeviation() { return stdDeviation; }
    public void setStdDeviation(Double stdDeviation) { this.stdDeviation = stdDeviation; }

    public Instant getCreatedAt() { return createdAt; }
}
