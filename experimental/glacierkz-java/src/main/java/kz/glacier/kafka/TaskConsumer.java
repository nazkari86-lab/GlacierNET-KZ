package kz.glacier.kafka;

import kz.glacier.model.ProcessingTask;
import kz.glacier.model.RasterJob;
import kz.glacier.repository.ProcessingTaskRepository;
import kz.glacier.repository.RasterJobRepository;
import kz.glacier.service.AuditService;
import kz.glacier.service.NotificationService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.kafka.support.KafkaHeaders;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@Component
public class TaskConsumer {
    
    private static final Logger log = LoggerFactory.getLogger(TaskConsumer.class);
    
    @Autowired
    private RasterJobRepository rasterJobRepository;
    
    @Autowired
    private ProcessingTaskRepository processingTaskRepository;
    
    @Autowired
    private AuditService auditService;
    
    @Autowired
    private NotificationService notificationService;
    
    @KafkaListener(
        topics = "glacier.task.events",
        groupId = "glacierkz-consumer-group",
        containerFactory = "kafkaListenerContainerFactory"
    )
    @Transactional
    public void consumeTaskEvents(
            @Payload TaskMessage message,
            @Header(KafkaHeaders.RECEIVED_TOPIC) String topic,
            @Header(KafkaHeaders.RECEIVED_PARTITION) int partition,
            @Header(KafkaHeaders.OFFSET) long offset,
            Acknowledgment acknowledgment) {
        
        log.info("Received task event: {} from topic: {}, partition: {}, offset: {}",
            message.getTaskId(), topic, partition, offset);
        
        try {
            // Validate message
            if (!validateMessage(message)) {
                log.warn("Invalid message received, skipping: {}", message.getTaskId());
                acknowledgment.acknowledge();
                return;
            }
            
            // Check for duplicate processing
            if (isDuplicate(message)) {
                log.info("Duplicate message detected: {}", message.getTaskId());
                acknowledgment.acknowledge();
                return;
            }
            
            // Process based on task type
            switch (message.getTaskType()) {
                case "PROCESSING":
                    processRasterJob(message);
                    break;
                case "ANALYSIS":
                    processAnalysisTask(message);
                    break;
                case "NOTIFICATION":
                    processNotificationTask(message);
                    break;
                case "CANCEL":
                    processCancellation(message);
                    break;
                case "RETRY":
                    processRetry(message);
                    break;
                default:
                    log.warn("Unknown task type: {}", message.getTaskType());
            }
            
            // Acknowledge successful processing
            acknowledgment.acknowledge();
            
            log.info("Successfully processed task: {}", message.getTaskId());
            
        } catch (Exception e) {
            log.error("Failed to process task {}: {}", message.getTaskId(), 
                e.getMessage(), e);
            
            // Handle retry logic
            if (message.canRetry()) {
                handleRetry(message, e.getMessage());
            } else {
                handleMaxRetriesExceeded(message, e.getMessage());
            }
            
            acknowledgment.acknowledge();
        }
    }
    
    @KafkaListener(
        topics = "glacier.result.events",
        groupId = "glacierkz-consumer-group",
        containerFactory = "kafkaListenerContainerFactory"
    )
    @Transactional
    public void consumeResultEvents(
            @Payload TaskMessage message,
            @Header(KafkaHeaders.RECEIVED_TOPIC) String topic,
            @Header(KafkaHeaders.RECEIVED_PARTITION) int partition,
            @Header(KafkaHeaders.OFFSET) long offset,
            Acknowledgment acknowledgment) {
        
        log.info("Received result event: {} from topic: {}", message.getTaskId(), topic);
        
        try {
            // Update job status based on result
            if ("PROCESSING".equals(message.getTaskType())) {
                updateJobStatus(message);
            }
            
            // Send notification if needed
            if (shouldNotify(message)) {
                sendNotification(message);
            }
            
            acknowledgment.acknowledge();
            
        } catch (Exception e) {
            log.error("Failed to process result event {}: {}", 
                message.getTaskId(), e.getMessage(), e);
            acknowledgment.acknowledge();
        }
    }
    
    private boolean validateMessage(TaskMessage message) {
        if (message == null) {
            return false;
        }
        
        if (message.getTaskId() == null || message.getTaskId().isEmpty()) {
            return false;
        }
        
        if (message.getTaskType() == null || message.getTaskType().isEmpty()) {
            return false;
        }
        
        if (message.getJobId() == null || message.getJobId().isEmpty()) {
            return false;
        }
        
        // Check timestamp is not too old (24 hours)
        if (message.getTimestamp() != null && 
            message.getTimestamp().plusHours(24).isBefore(LocalDateTime.now())) {
            log.warn("Message timestamp is too old: {}", message.getTimestamp());
            return false;
        }
        
        return true;
    }
    
    private boolean isDuplicate(TaskMessage message) {
        // Check if we've already processed this task
        Optional<ProcessingTask> existing = processingTaskRepository
            .findByExternalId(message.getTaskId());
        
        if (existing.isPresent()) {
            log.info("Task {} already processed", message.getTaskId());
            return true;
        }
        
        return false;
    }
    
    private void processRasterJob(TaskMessage message) {
        log.info("Processing raster job: {}", message.getJobId());
        
        // Find the job
        Optional<RasterJob> jobOpt = rasterJobRepository
            .findById(UUID.fromString(message.getJobId()));
        
        if (jobOpt.isEmpty()) {
            log.warn("Job not found: {}", message.getJobId());
            return;
        }
        
        RasterJob job = jobOpt.get();
        
        // Update job status
        job.setStatus("RUNNING");
        job.setStartedAt(LocalDateTime.now());
        job.setUpdatedAt(LocalDateTime.now());
        
        // Store task reference
        ProcessingTask task = createProcessingTask(message);
        task.setReferenceId(job.getId().toString());
        processingTaskRepository.save(task);
        
        rasterJobRepository.save(job);
        
        // Log audit
        auditService.logAsync(
            "raster_job",
            job.getId().toString(),
            "START",
            "Job started processing via Kafka"
        );
    }
    
    private void processAnalysisTask(TaskMessage message) {
        log.info("Processing analysis task: {}", message.getJobId());
        
        ProcessingTask task = createProcessingTask(message);
        processingTaskRepository.save(task);
        
        auditService.logAsync(
            "analysis_task",
            message.getJobId(),
            "START",
            "Analysis task started"
        );
    }
    
    private void processNotificationTask(TaskMessage message) {
        log.info("Processing notification task: {}", message.getTaskId());
        
        ProcessingTask task = createProcessingTask(message);
        processingTaskRepository.save(task);
        
        // Send notification
        if (message.getPayload() != null && message.getPayload().containsKey("email")) {
            String email = (String) message.getPayload().get("email");
            String subject = (String) message.getPayload().get("subject");
            String body = (String) message.getPayload().get("body");
            
            notificationService.sendEmailAsync(email, subject, body)
                .exceptionally(ex -> {
                    log.error("Failed to send notification: {}", ex.getMessage());
                    return null;
                });
        }
    }
    
    private void processCancellation(TaskMessage message) {
        log.info("Processing cancellation task: {}", message.getJobId());
        
        Optional<RasterJob> jobOpt = rasterJobRepository
            .findById(UUID.fromString(message.getJobId()));
        
        if (jobOpt.isPresent()) {
            RasterJob job = jobOpt.get();
            job.setStatus("CANCELLED");
            job.setUpdatedAt(LocalDateTime.now());
            rasterJobRepository.save(job);
            
            auditService.logAsync(
                "raster_job",
                job.getId().toString(),
                "CANCEL",
                "Job cancelled via Kafka"
            );
        }
    }
    
    private void processRetry(TaskMessage message) {
        log.info("Processing retry task: {}", message.getJobId());
        
        Optional<RasterJob> jobOpt = rasterJobRepository
            .findById(UUID.fromString(message.getJobId()));
        
        if (jobOpt.isPresent()) {
            RasterJob job = jobOpt.get();
            job.setStatus("PENDING");
            job.setRetryCount(job.getRetryCount() + 1);
            job.setUpdatedAt(LocalDateTime.now());
            rasterJobRepository.save(job);
            
            auditService.logAsync(
                "raster_job",
                job.getId().toString(),
                "RETRY",
                "Job retry triggered via Kafka"
            );
        }
    }
    
    private ProcessingTask createProcessingTask(TaskMessage message) {
        ProcessingTask task = new ProcessingTask();
        task.setId(UUID.randomUUID());
        task.setExternalId(message.getTaskId());
        task.setType(message.getTaskType());
        task.setJobId(message.getJobId());
        task.setGlacierId(message.getGlacierId());
        task.setStatus("PROCESSING");
        task.setPriority(message.getPriority());
        task.setPayload(message.getPayload() != null ? 
            message.getPayload().toString() : null);
        task.setCreatedAt(LocalDateTime.now());
        task.setUpdatedAt(LocalDateTime.now());
        task.setCreatedBy("kafka-consumer");
        return task;
    }
    
    private void updateJobStatus(TaskMessage message) {
        Optional<RasterJob> jobOpt = rasterJobRepository
            .findById(UUID.fromString(message.getJobId()));
        
        if (jobOpt.isPresent()) {
            RasterJob job = jobOpt.get();
            
            if ("COMPLETED".equals(message.getStatus())) {
                job.setStatus("COMPLETED");
                job.setCompletedAt(LocalDateTime.now());
            } else if ("FAILED".equals(message.getStatus())) {
                job.setStatus("FAILED");
                job.setErrorMessage(message.getErrorMessage());
            }
            
            job.setUpdatedAt(LocalDateTime.now());
            rasterJobRepository.save(job);
        }
    }
    
    private boolean shouldNotify(TaskMessage message) {
        // Notify on completion or failure
        return "COMPLETED".equals(message.getStatus()) || 
               "FAILED".equals(message.getStatus());
    }
    
    private void sendNotification(TaskMessage message) {
        // Implementation would depend on notification preferences
        log.info("Sending notification for task: {}", message.getTaskId());
    }
    
    private void handleRetry(TaskMessage message, String errorMessage) {
        log.info("Retrying task {}: {}/{}", 
            message.getTaskId(), message.getRetryCount() + 1, message.getMaxRetries());
        
        message.incrementRetryCount();
        message.setErrorMessage(errorMessage);
        
        // Could re-publish to Kafka for retry
        // For now, just log the retry attempt
    }
    
    private void handleMaxRetriesExceeded(TaskMessage message, String errorMessage) {
        log.error("Max retries exceeded for task {}: {}", 
            message.getTaskId(), errorMessage);
        
        // Mark task as failed
        Optional<ProcessingTask> taskOpt = processingTaskRepository
            .findByExternalId(message.getTaskId());
        
        if (taskOpt.isPresent()) {
            ProcessingTask task = taskOpt.get();
            task.setStatus("FAILED");
            task.setErrorMessage(errorMessage);
            task.setUpdatedAt(LocalDateTime.now());
            processingTaskRepository.save(task);
        }
        
        // Send failure notification
        auditService.logAsync(
            "task",
            message.getTaskId(),
            "FAILED",
            "Max retries exceeded: " + errorMessage
        );
    }
}