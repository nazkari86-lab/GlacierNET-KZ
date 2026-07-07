package kz.glacier.kafka;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;

public class TaskMessage implements Serializable {
    
    private static final long serialVersionUID = 1L;
    
    private String taskId;
    private String taskType;
    private String jobId;
    private String glacierId;
    private String status;
    private String priority;
    private Map<String, Object> payload;
    private LocalDateTime timestamp;
    private String correlationId;
    private String source;
    private int retryCount;
    private int maxRetries;
    private String errorMessage;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    
    public TaskMessage() {
        this.taskId = UUID.randomUUID().toString();
        this.timestamp = LocalDateTime.now();
        this.createdAt = LocalDateTime.now();
        this.updatedAt = LocalDateTime.now();
        this.retryCount = 0;
        this.maxRetries = 3;
        this.source = "glacierkz-service";
    }
    
    public TaskMessage(String taskType, String jobId, String glacierId, 
                      Map<String, Object> payload) {
        this();
        this.taskType = taskType;
        this.jobId = jobId;
        this.glacierId = glacierId;
        this.payload = payload;
    }
    
    // Getters and Setters
    public String getTaskId() { return taskId; }
    public void setTaskId(String taskId) { this.taskId = taskId; }
    
    public String getTaskType() { return taskType; }
    public void setTaskType(String taskType) { this.taskType = taskType; }
    
    public String getJobId() { return jobId; }
    public void setJobId(String jobId) { this.jobId = jobId; }
    
    public String getGlacierId() { return glacierId; }
    public void setGlacierId(String glacierId) { this.glacierId = glacierId; }
    
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    
    public String getPriority() { return priority; }
    public void setPriority(String priority) { this.priority = priority; }
    
    public Map<String, Object> getPayload() { return payload; }
    public void setPayload(Map<String, Object> payload) { this.payload = payload; }
    
    public LocalDateTime getTimestamp() { return timestamp; }
    public void setTimestamp(LocalDateTime timestamp) { this.timestamp = timestamp; }
    
    public String getCorrelationId() { return correlationId; }
    public void setCorrelationId(String correlationId) { this.correlationId = correlationId; }
    
    public String getSource() { return source; }
    public void setSource(String source) { this.source = source; }
    
    public int getRetryCount() { return retryCount; }
    public void setRetryCount(int retryCount) { this.retryCount = retryCount; }
    
    public int getMaxRetries() { return maxRetries; }
    public void setMaxRetries(int maxRetries) { this.maxRetries = maxRetries; }
    
    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }
    
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
    
    // Business methods
    public boolean canRetry() {
        return retryCount < maxRetries;
    }
    
    public void incrementRetryCount() {
        this.retryCount++;
        this.updatedAt = LocalDateTime.now();
    }
    
    public boolean isExpired() {
        return createdAt != null && createdAt.plusHours(24).isBefore(LocalDateTime.now());
    }
    
    public boolean isHighPriority() {
        return "HIGH".equals(priority) || "CRITICAL".equals(priority);
    }
    
    public void markAsCompleted() {
        this.status = "COMPLETED";
        this.updatedAt = LocalDateTime.now();
    }
    
    public void markAsFailed(String errorMessage) {
        this.status = "FAILED";
        this.errorMessage = errorMessage;
        this.updatedAt = LocalDateTime.now();
    }
    
    public void markAsProcessing() {
        this.status = "PROCESSING";
        this.updatedAt = LocalDateTime.now();
    }
    
    public void markAsQueued() {
        this.status = "QUEUED";
        this.updatedAt = LocalDateTime.now();
    }
    
    // Static factory methods
    public static TaskMessage createProcessingTask(String jobId, String glacierId,
                                                  Map<String, Object> payload) {
        TaskMessage message = new TaskMessage("PROCESSING", jobId, glacierId, payload);
        message.setPriority("HIGH");
        message.markAsQueued();
        return message;
    }
    
    public static TaskMessage createAnalysisTask(String jobId, String glacierId,
                                                String analysisType) {
        TaskMessage message = new TaskMessage("ANALYSIS", jobId, glacierId, null);
        message.setPriority("MEDIUM");
        message.markAsQueued();
        return message;
    }
    
    public static TaskMessage createNotificationTask(String jobId, String type,
                                                    Map<String, Object> payload) {
        TaskMessage message = new TaskMessage("NOTIFICATION", jobId, null, payload);
        message.setPriority("LOW");
        message.markAsQueued();
        return message;
    }
    
    @Override
    public String toString() {
        return String.format(
            "TaskMessage{taskId='%s', taskType='%s', jobId='%s', glacierId='%s', " +
            "status='%s', priority='%s', retryCount=%d/%d, createdAt=%s}",
            taskId, taskType, jobId, glacierId, status, priority, 
            retryCount, maxRetries, createdAt
        );
    }
    
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        TaskMessage that = (TaskMessage) o;
        return taskId != null ? taskId.equals(that.taskId) : that.taskId == null;
    }
    
    @Override
    public int hashCode() {
        return taskId != null ? taskId.hashCode() : 0;
    }
}