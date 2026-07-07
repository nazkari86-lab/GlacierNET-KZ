package kz.glacier.kafka;

import kz.glacier.service.AuditService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

@Component
public class TaskProducer {
    
    private static final Logger log = LoggerFactory.getLogger(TaskProducer.class);
    
    private static final String TASK_TOPIC = "glacier.task.events";
    private static final String RESULT_TOPIC = "glacier.result.events";
    private static final String NOTIFICATION_TOPIC = "glacier.notification.events";
    
    @Autowired
    private KafkaTemplate<String, TaskMessage> kafkaTemplate;
    
    @Autowired
    private AuditService auditService;
    
    @Transactional
    public CompletableFuture<SendResult<String, TaskMessage>> sendTaskMessage(
            TaskMessage message) {
        
        log.info("Sending task message: {} to topic: {}", message.getTaskId(), TASK_TOPIC);
        
        // Validate message
        if (!validateMessage(message)) {
            log.warn("Invalid message, not sending: {}", message.getTaskId());
            return CompletableFuture.failedFuture(
                new IllegalArgumentException("Invalid message"));
        }
        
        // Set correlation ID if not present
        if (message.getCorrelationId() == null) {
            message.setCorrelationId(UUID.randomUUID().toString());
        }
        
        // Set timestamps
        if (message.getCreatedAt() == null) {
            message.setCreatedAt(LocalDateTime.now());
        }
        message.setUpdatedAt(LocalDateTime.now());
        
        // Send to Kafka
        CompletableFuture<SendResult<String, TaskMessage>> future = 
            kafkaTemplate.send(TASK_TOPIC, message.getTaskId(), message);
        
        future.whenComplete((result, ex) -> {
            if (ex != null) {
                log.error("Failed to send task message {}: {}", 
                    message.getTaskId(), ex.getMessage(), ex);
                
                // Log audit for failed send
                auditService.logAsync(
                    "kafka_producer",
                    message.getTaskId(),
                    "SEND_FAILED",
                    ex.getMessage()
                );
            } else {
                log.info("Task message sent successfully: {} to partition: {} offset: {}",
                    message.getTaskId(),
                    result.getRecordMetadata().partition(),
                    result.getRecordMetadata().offset());
                
                // Log audit for successful send
                auditService.logAsync(
                    "kafka_producer",
                    message.getTaskId(),
                    "SENT",
                    String.format("Sent to partition %d offset %d",
                        result.getRecordMetadata().partition(),
                        result.getRecordMetadata().offset())
                );
            }
        });
        
        return future;
    }
    
    @Transactional
    public CompletableFuture<SendResult<String, TaskMessage>> sendResultMessage(
            TaskMessage message) {
        
        log.info("Sending result message: {} to topic: {}", message.getTaskId(), RESULT_TOPIC);
        
        if (!validateMessage(message)) {
            return CompletableFuture.failedFuture(
                new IllegalArgumentException("Invalid message"));
        }
        
        message.setUpdatedAt(LocalDateTime.now());
        
        CompletableFuture<SendResult<String, TaskMessage>> future = 
            kafkaTemplate.send(RESULT_TOPIC, message.getTaskId(), message);
        
        future.whenComplete((result, ex) -> {
            if (ex != null) {
                log.error("Failed to send result message {}: {}", 
                    message.getTaskId(), ex.getMessage(), ex);
            } else {
                log.info("Result message sent successfully: {}", message.getTaskId());
            }
        });
        
        return future;
    }
    
    @Transactional
    public CompletableFuture<SendResult<String, TaskMessage>> sendNotificationMessage(
            TaskMessage message) {
        
        log.info("Sending notification message: {} to topic: {}", 
            message.getTaskId(), NOTIFICATION_TOPIC);
        
        if (!validateMessage(message)) {
            return CompletableFuture.failedFuture(
                new IllegalArgumentException("Invalid message"));
        }
        
        message.setUpdatedAt(LocalDateTime.now());
        
        CompletableFuture<SendResult<String, TaskMessage>> future = 
            kafkaTemplate.send(NOTIFICATION_TOPIC, message.getTaskId(), message);
        
        future.whenComplete((result, ex) -> {
            if (ex != null) {
                log.error("Failed to send notification message {}: {}", 
                    message.getTaskId(), ex.getMessage(), ex);
            } else {
                log.info("Notification message sent successfully: {}", message.getTaskId());
            }
        });
        
        return future;
    }
    
    // Convenience methods for common task types
    public CompletableFuture<SendResult<String, TaskMessage>> sendProcessingTask(
            String jobId, String glacierId, Map<String, Object> payload) {
        
        TaskMessage message = TaskMessage.createProcessingTask(jobId, glacierId, payload);
        return sendTaskMessage(message);
    }
    
    public CompletableFuture<SendResult<String, TaskMessage>> sendAnalysisTask(
            String jobId, String glacierId, String analysisType) {
        
        TaskMessage message = TaskMessage.createAnalysisTask(jobId, glacierId, analysisType);
        return sendTaskMessage(message);
    }
    
    public CompletableFuture<SendResult<String, TaskMessage>> sendNotificationTask(
            String jobId, String type, Map<String, Object> payload) {
        
        TaskMessage message = TaskMessage.createNotificationTask(jobId, type, payload);
        return sendNotificationMessage(message);
    }
    
    public CompletableFuture<SendResult<String, TaskMessage>> sendCancellationTask(
            String jobId) {
        
        TaskMessage message = new TaskMessage("CANCEL", jobId, null, null);
        message.setPriority("HIGH");
        message.markAsQueued();
        return sendTaskMessage(message);
    }
    
    public CompletableFuture<SendResult<String, TaskMessage>> sendRetryTask(
            String jobId, String glacierId) {
        
        TaskMessage message = new TaskMessage("RETRY", jobId, glacierId, null);
        message.setPriority("MEDIUM");
        message.markAsQueued();
        return sendTaskMessage(message);
    }
    
    public CompletableFuture<SendResult<String, TaskMessage>> sendCompletionResult(
            String jobId, String taskId, Map<String, Object> resultPayload) {
        
        TaskMessage message = new TaskMessage("PROCESSING", jobId, null, resultPayload);
        message.setTaskId(taskId);
        message.markAsCompleted();
        return sendResultMessage(message);
    }
    
    public CompletableFuture<SendResult<String, TaskMessage>> sendFailureResult(
            String jobId, String taskId, String errorMessage) {
        
        TaskMessage message = new TaskMessage("PROCESSING", jobId, null, null);
        message.setTaskId(taskId);
        message.markAsFailed(errorMessage);
        return sendResultMessage(message);
    }
    
    private boolean validateMessage(TaskMessage message) {
        if (message == null) {
            return false;
        }
        
        if (message.getTaskId() == null || message.getTaskId().isEmpty()) {
            log.warn("Message missing task ID");
            return false;
        }
        
        if (message.getTaskType() == null || message.getTaskType().isEmpty()) {
            log.warn("Message missing task type");
            return false;
        }
        
        if (message.getJobId() == null || message.getJobId().isEmpty()) {
            log.warn("Message missing job ID");
            return false;
        }
        
        return true;
    }
    
    public String getTaskTopic() {
        return TASK_TOPIC;
    }
    
    public String getResultTopic() {
        return RESULT_TOPIC;
    }
    
    public String getNotificationTopic() {
        return NOTIFICATION_TOPIC;
    }
}