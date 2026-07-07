package kz.glacier.model;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "raster_jobs", indexes = {
        @Index(name = "idx_raster_job_status", columnList = "status"),
        @Index(name = "idx_raster_job_type", columnList = "job_type"),
        @Index(name = "idx_raster_job_glacier", columnList = "glacier_id"),
        @Index(name = "idx_raster_job_created", columnList = "created_at")
})
public class RasterJob {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "job_name", nullable = false, length = 255)
    private String jobName;

    @Column(name = "job_type", nullable = false, length = 50)
    private String jobType;

    @Column(name = "status", nullable = false, length = 30)
    private String status;

    @Column(name = "batch_execution_id")
    private Long batchExecutionId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "glacier_id")
    private Glacier glacier;

    @Column(name = "input_parameters", columnDefinition = "jsonb")
    private String inputParameters;

    @Column(name = "output_parameters", columnDefinition = "jsonb")
    private String outputParameters;

    @Column(name = "error_message", length = 2000)
    private String errorMessage;

    @Column(name = "progress_percent")
    private Integer progressPercent = 0;

    @Column(name = "records_processed")
    private Long recordsProcessed = 0L;

    @Column(name = "records_total")
    private Long recordsTotal = 0L;

    @Column(name = "started_at")
    private Instant startedAt;

    @Column(name = "completed_at")
    private Instant completedAt;

    @Column(name = "duration_ms")
    private Long durationMs;

    @Column(name = "retry_count")
    private Integer retryCount = 0;

    @Column(name = "max_retries")
    private Integer maxRetries = 3;

    @Column(name = "priority")
    private Integer priority = 5;

    @Column(name = "created_by", length = 100)
    private String createdBy;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private Instant createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private Instant updatedAt;

    @Version
    private Long version;

    public RasterJob() {
        this.status = "PENDING";
    }

    public RasterJob(String jobName, String jobType, Glacier glacier) {
        this();
        this.jobName = jobName;
        this.jobType = jobType;
        this.glacier = glacier;
    }

    public void markStarted() {
        this.status = "RUNNING";
        this.startedAt = Instant.now();
    }

    public void markCompleted() {
        this.status = "COMPLETED";
        this.completedAt = Instant.now();
        this.progressPercent = 100;
        if (startedAt != null) {
            this.durationMs = completedAt.toEpochMilli() - startedAt.toEpochMilli();
        }
    }

    public void markFailed(String errorMessage) {
        this.status = "FAILED";
        this.completedAt = Instant.now();
        this.errorMessage = errorMessage;
        if (startedAt != null) {
            this.durationMs = completedAt.toEpochMilli() - startedAt.toEpochMilli();
        }
    }

    public void markCancelled() {
        this.status = "CANCELLED";
        this.completedAt = Instant.now();
    }

    public void incrementProgress(int delta) {
        this.progressPercent = Math.min(100, this.progressPercent + delta);
    }

    public boolean isRetryable() {
        return retryCount < maxRetries && "FAILED".equals(status);
    }

    public boolean isRunning() {
        return "RUNNING".equals(status);
    }

    public boolean isCompleted() {
        return "COMPLETED".equals(status);
    }

    // Getters and Setters
    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public String getJobName() { return jobName; }
    public void setJobName(String jobName) { this.jobName = jobName; }

    public String getJobType() { return jobType; }
    public void setJobType(String jobType) { this.jobType = jobType; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public Long getBatchExecutionId() { return batchExecutionId; }
    public void setBatchExecutionId(Long batchExecutionId) { this.batchExecutionId = batchExecutionId; }

    public Glacier getGlacier() { return glacier; }
    public void setGlacier(Glacier glacier) { this.glacier = glacier; }

    public String getInputParameters() { return inputParameters; }
    public void setInputParameters(String inputParameters) { this.inputParameters = inputParameters; }

    public String getOutputParameters() { return outputParameters; }
    public void setOutputParameters(String outputParameters) { this.outputParameters = outputParameters; }

    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }

    public Integer getProgressPercent() { return progressPercent; }
    public void setProgressPercent(Integer progressPercent) { this.progressPercent = progressPercent; }

    public Long getRecordsProcessed() { return recordsProcessed; }
    public void setRecordsProcessed(Long recordsProcessed) { this.recordsProcessed = recordsProcessed; }

    public Long getRecordsTotal() { return recordsTotal; }
    public void setRecordsTotal(Long recordsTotal) { this.recordsTotal = recordsTotal; }

    public Instant getStartedAt() { return startedAt; }
    public void setStartedAt(Instant startedAt) { this.startedAt = startedAt; }

    public Instant getCompletedAt() { return completedAt; }
    public void setCompletedAt(Instant completedAt) { this.completedAt = completedAt; }

    public Long getDurationMs() { return durationMs; }
    public void setDurationMs(Long durationMs) { this.durationMs = durationMs; }

    public Integer getRetryCount() { return retryCount; }
    public void setRetryCount(Integer retryCount) { this.retryCount = retryCount; }

    public Integer getMaxRetries() { return maxRetries; }
    public void setMaxRetries(Integer maxRetries) { this.maxRetries = maxRetries; }

    public Integer getPriority() { return priority; }
    public void setPriority(Integer priority) { this.priority = priority; }

    public String getCreatedBy() { return createdBy; }
    public void setCreatedBy(String createdBy) { this.createdBy = createdBy; }

    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }

    public Long getVersion() { return version; }
    public void setVersion(Long version) { this.version = version; }
}
