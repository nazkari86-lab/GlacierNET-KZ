package kz.glacier.model;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "processing_tasks", indexes = {
        @Index(name = "idx_task_status", columnList = "status"),
        @Index(name = "idx_task_type", columnList = "task_type"),
        @Index(name = "idx_task_owner", columnList = "owner_user_id"),
        @Index(name = "idx_task_correlation", columnList = "correlation_id")
})
public class ProcessingTask {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "task_name", nullable = false, length = 255)
    private String taskName;

    @Column(name = "task_type", nullable = false, length = 50)
    private String taskType;

    @Column(name = "status", nullable = false, length = 30)
    private String status;

    @Column(name = "priority")
    private Integer priority = 5;

    @Column(name = "owner_user_id")
    private UUID ownerUserId;

    @Column(name = "assigned_worker", length = 100)
    private String assignedWorker;

    @Column(name = "correlation_id", length = 100)
    private String correlationId;

    @Column(name = "input_payload", columnDefinition = "jsonb")
    private String inputPayload;

    @Column(name = "output_payload", columnDefinition = "jsonb")
    private String outputPayload;

    @Column(name = "progress_percent")
    private Integer progressPercent = 0;

    @Column(name = "result_message", length = 2000)
    private String resultMessage;

    @Column(name = "error_details", columnDefinition = "jsonb")
    private String errorDetails;

    @Column(name = "started_at")
    private Instant startedAt;

    @Column(name = "completed_at")
    private Instant completedAt;

    @Column(name = "expires_at")
    private Instant expiresAt;

    @Column(name = "timeout_seconds")
    private Integer timeoutSeconds = 3600;

    @Column(name = "retry_count")
    private Integer retryCount = 0;

    @Column(name = "max_retries")
    private Integer maxRetries = 3;

    @Column(name = "cancellable")
    private Boolean cancellable = true;

    @Column(name = "cancelled")
    private Boolean cancelled = false;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private Instant createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private Instant updatedAt;

    @Version
    private Long version;

    public ProcessingTask() {
        this.status = "QUEUED";
    }

    public ProcessingTask(String taskName, String taskType, UUID ownerUserId) {
        this();
        this.taskName = taskName;
        this.taskType = taskType;
        this.ownerUserId = ownerUserId;
    }

    public void markRunning() {
        this.status = "RUNNING";
        this.startedAt = Instant.now();
        if (timeoutSeconds != null) {
            this.expiresAt = Instant.now().plusSeconds(timeoutSeconds);
        }
    }

    public void markCompleted(String resultMessage) {
        this.status = "COMPLETED";
        this.completedAt = Instant.now();
        this.progressPercent = 100;
        this.resultMessage = resultMessage;
    }

    public void markFailed(String error) {
        this.status = "FAILED";
        this.completedAt = Instant.now();
        this.resultMessage = error;
    }

    public void markExpired() {
        this.status = "EXPIRED";
        this.completedAt = Instant.now();
        this.resultMessage = "Task expired after " + timeoutSeconds + " seconds";
    }

    public void markCancelled() {
        this.status = "CANCELLED";
        this.completedAt = Instant.now();
        this.cancelled = true;
    }

    public boolean isTerminal() {
        return "COMPLETED".equals(status) || "FAILED".equals(status)
                || "CANCELLED".equals(status) || "EXPIRED".equals(status);
    }

    public boolean isExpired() {
        return expiresAt != null && Instant.now().isAfter(expiresAt);
    }

    public boolean canRetry() {
        return retryCount < maxRetries && "FAILED".equals(status);
    }

    public long getElapsedSeconds() {
        if (startedAt == null) return 0;
        Instant end = completedAt != null ? completedAt : Instant.now();
        return end.getEpochSecond() - startedAt.getEpochSecond();
    }

    // Getters and Setters
    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public String getTaskName() { return taskName; }
    public void setTaskName(String taskName) { this.taskName = taskName; }

    public String getTaskType() { return taskType; }
    public void setTaskType(String taskType) { this.taskType = taskType; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public Integer getPriority() { return priority; }
    public void setPriority(Integer priority) { this.priority = priority; }

    public UUID getOwnerUserId() { return ownerUserId; }
    public void setOwnerUserId(UUID ownerUserId) { this.ownerUserId = ownerUserId; }

    public String getAssignedWorker() { return assignedWorker; }
    public void setAssignedWorker(String assignedWorker) { this.assignedWorker = assignedWorker; }

    public String getCorrelationId() { return correlationId; }
    public void setCorrelationId(String correlationId) { this.correlationId = correlationId; }

    public String getInputPayload() { return inputPayload; }
    public void setInputPayload(String inputPayload) { this.inputPayload = inputPayload; }

    public String getOutputPayload() { return outputPayload; }
    public void setOutputPayload(String outputPayload) { this.outputPayload = outputPayload; }

    public Integer getProgressPercent() { return progressPercent; }
    public void setProgressPercent(Integer progressPercent) { this.progressPercent = progressPercent; }

    public String getResultMessage() { return resultMessage; }
    public void setResultMessage(String resultMessage) { this.resultMessage = resultMessage; }

    public String getErrorDetails() { return errorDetails; }
    public void setErrorDetails(String errorDetails) { this.errorDetails = errorDetails; }

    public Instant getStartedAt() { return startedAt; }
    public void setStartedAt(Instant startedAt) { this.startedAt = startedAt; }

    public Instant getCompletedAt() { return completedAt; }
    public void setCompletedAt(Instant completedAt) { this.completedAt = completedAt; }

    public Instant getExpiresAt() { return expiresAt; }
    public void setExpiresAt(Instant expiresAt) { this.expiresAt = expiresAt; }

    public Integer getTimeoutSeconds() { return timeoutSeconds; }
    public void setTimeoutSeconds(Integer timeoutSeconds) { this.timeoutSeconds = timeoutSeconds; }

    public Integer getRetryCount() { return retryCount; }
    public void setRetryCount(Integer retryCount) { this.retryCount = retryCount; }

    public Integer getMaxRetries() { return maxRetries; }
    public void setMaxRetries(Integer maxRetries) { this.maxRetries = maxRetries; }

    public Boolean getCancellable() { return cancellable; }
    public void setCancellable(Boolean cancellable) { this.cancellable = cancellable; }

    public Boolean getCancelled() { return cancelled; }
    public void setCancelled(Boolean cancelled) { this.cancelled = cancelled; }

    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }

    public Long getVersion() { return version; }
    public void setVersion(Long version) { this.version = version; }
}
