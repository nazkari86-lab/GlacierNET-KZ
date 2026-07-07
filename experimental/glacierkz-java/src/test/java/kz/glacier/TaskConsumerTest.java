package kz.glacier;

import kz.glacier.kafka.TaskConsumer;
import kz.glacier.kafka.TaskMessage;
import kz.glacier.model.ProcessingTask;
import kz.glacier.model.RasterJob;
import kz.glacier.repository.ProcessingTaskRepository;
import kz.glacier.repository.RasterJobRepository;
import kz.glacier.service.AuditService;
import kz.glacier.service.NotificationService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.kafka.support.Acknowledgment;

import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
public class TaskConsumerTest {
    
    @Mock
    private RasterJobRepository rasterJobRepository;
    
    @Mock
    private ProcessingTaskRepository processingTaskRepository;
    
    @Mock
    private AuditService auditService;
    
    @Mock
    private NotificationService notificationService;
    
    @Mock
    private Acknowledgment acknowledgment;
    
    @InjectMocks
    private TaskConsumer taskConsumer;
    
    private TaskMessage testMessage;
    private RasterJob testJob;
    private ProcessingTask testTask;
    
    @BeforeEach
    void setUp() {
        testMessage = new TaskMessage();
        testMessage.setTaskId(UUID.randomUUID().toString());
        testMessage.setTaskType("PROCESSING");
        testMessage.setJobId(UUID.randomUUID().toString());
        testMessage.setGlacierId(UUID.randomUUID().toString());
        testMessage.setStatus("QUEUED");
        testMessage.setPriority("HIGH");
        testMessage.setSource("test-producer");
        testMessage.setTimestamp(LocalDateTime.now());
        
        Map<String, Object> payload = new HashMap<>();
        payload.put("resolution", 10);
        payload.put("bands", Arrays.asList("B02", "B03", "B04", "B08"));
        testMessage.setPayload(payload);
        
        testJob = new RasterJob();
        testJob.setId(UUID.fromString(testMessage.getJobId()));
        testJob.setGlacierId(UUID.fromString(testMessage.getGlacierId()));
        testJob.setStatus("PENDING");
        testJob.setRetryCount(0);
        testJob.setMaxRetries(3);
        testJob.setCreatedAt(LocalDateTime.now());
        
        testTask = new ProcessingTask();
        testTask.setId(UUID.randomUUID());
        testTask.setExternalId(testMessage.getTaskId());
        testTask.setType(testMessage.getTaskType());
        testTask.setJobId(testMessage.getJobId());
        testTask.setGlacierId(testMessage.getGlacierId());
        testTask.setStatus("PROCESSING");
        testTask.setCreatedAt(LocalDateTime.now());
    }
    
    @Test
    void testConsumeTaskEvents_ValidMessage() {
        // Given
        when(processingTaskRepository.findByExternalId(testMessage.getTaskId()))
            .thenReturn(Optional.empty());
        when(rasterJobRepository.findById(UUID.fromString(testMessage.getJobId())))
            .thenReturn(Optional.of(testJob));
        when(rasterJobRepository.save(any(RasterJob.class)))
            .thenReturn(testJob);
        when(processingTaskRepository.save(any(ProcessingTask.class)))
            .thenReturn(testTask);
        
        // When
        taskConsumer.consumeTaskEvents(
            testMessage,
            "glacier.task.events",
            0,
            0L,
            acknowledgment
        );
        
        // Then
        verify(acknowledgment).acknowledge();
        verify(processingTaskRepository).findByExternalId(testMessage.getTaskId());
        verify(rasterJobRepository).findById(UUID.fromString(testMessage.getJobId()));
        verify(rasterJobRepository).save(any(RasterJob.class));
        verify(processingTaskRepository).save(any(ProcessingTask.class));
        verify(auditService).logAsync(
            eq("raster_job"),
            eq(testJob.getId().toString()),
            eq("START"),
            contains("started processing")
        );
    }
    
    @Test
    void testConsumeTaskEvents_DuplicateMessage() {
        // Given
        when(processingTaskRepository.findByExternalId(testMessage.getTaskId()))
            .thenReturn(Optional.of(testTask));
        
        // When
        taskConsumer.consumeTaskEvents(
            testMessage,
            "glacier.task.events",
            0,
            0L,
            acknowledgment
        );
        
        // Then
        verify(acknowledgment).acknowledge();
        verify(processingTaskRepository).findByExternalId(testMessage.getTaskId());
        verify(rasterJobRepository, never()).findById(any(UUID.class));
        verify(rasterJobRepository, never()).save(any(RasterJob.class));
    }
    
    @Test
    void testConsumeTaskEvents_InvalidMessage_NullTaskId() {
        // Given
        testMessage.setTaskId(null);
        
        // When
        taskConsumer.consumeTaskEvents(
            testMessage,
            "glacier.task.events",
            0,
            0L,
            acknowledgment
        );
        
        // Then
        verify(acknowledgment).acknowledge();
        verify(processingTaskRepository, never()).findByExternalId(anyString());
    }
    
    @Test
    void testConsumeTaskEvents_InvalidMessage_EmptyJobId() {
        // Given
        testMessage.setJobId("");
        
        // When
        taskConsumer.consumeTaskEvents(
            testMessage,
            "glacier.task.events",
            0,
            0L,
            acknowledgment
        );
        
        // Then
        verify(acknowledgment).acknowledge();
        verify(processingTaskRepository, never()).findByExternalId(anyString());
    }
    
    @Test
    void testConsumeTaskEvents_OldMessage() {
        // Given
        testMessage.setTimestamp(LocalDateTime.now().minusHours(25));
        
        // When
        taskConsumer.consumeTaskEvents(
            testMessage,
            "glacier.task.events",
            0,
            0L,
            acknowledgment
        );
        
        // Then
        verify(acknowledgment).acknowledge();
        verify(processingTaskRepository, never()).findByExternalId(anyString());
    }
    
    @Test
    void testConsumeTaskEvents_JobNotFound() {
        // Given
        when(processingTaskRepository.findByExternalId(testMessage.getTaskId()))
            .thenReturn(Optional.empty());
        when(rasterJobRepository.findById(UUID.fromString(testMessage.getJobId())))
            .thenReturn(Optional.empty());
        
        // When
        taskConsumer.consumeTaskEvents(
            testMessage,
            "glacier.task.events",
            0,
            0L,
            acknowledgment
        );
        
        // Then
        verify(acknowledgment).acknowledge();
        verify(rasterJobRepository).findById(UUID.fromString(testMessage.getJobId()));
        verify(rasterJobRepository, never()).save(any(RasterJob.class));
    }
    
    @Test
    void testConsumeTaskEvents_ProcessingException() {
        // Given
        when(processingTaskRepository.findByExternalId(testMessage.getTaskId()))
            .thenReturn(Optional.empty());
        when(rasterJobRepository.findById(UUID.fromString(testMessage.getJobId())))
            .thenThrow(new RuntimeException("Database connection failed"));
        
        // When
        taskConsumer.consumeTaskEvents(
            testMessage,
            "glacier.task.events",
            0,
            0L,
            acknowledgment
        );
        
        // Then
        verify(acknowledgment).acknowledge();
        verify(auditService).logAsync(
            eq("task"),
            eq(testMessage.getTaskId()),
            eq("FAILED"),
            contains("Database connection failed")
        );
    }
    
    @Test
    void testConsumeResultEvents_Completed() {
        // Given
        testMessage.setStatus("COMPLETED");
        when(rasterJobRepository.findById(UUID.fromString(testMessage.getJobId())))
            .thenReturn(Optional.of(testJob));
        when(rasterJobRepository.save(any(RasterJob.class)))
            .thenReturn(testJob);
        
        // When
        taskConsumer.consumeResultEvents(
            testMessage,
            "glacier.result.events",
            0,
            0L,
            acknowledgment
        );
        
        // Then
        verify(acknowledgment).acknowledge();
        verify(rasterJobRepository).findById(UUID.fromString(testMessage.getJobId()));
        verify(rasterJobRepository).save(any(RasterJob.class));
        assertEquals("COMPLETED", testJob.getStatus());
        assertNotNull(testJob.getCompletedAt());
    }
    
    @Test
    void testConsumeResultEvents_Failed() {
        // Given
        testMessage.setStatus("FAILED");
        testMessage.setErrorMessage("Processing failed");
        
        when(rasterJobRepository.findById(UUID.fromString(testMessage.getJobId())))
            .thenReturn(Optional.of(testJob));
        when(rasterJobRepository.save(any(RasterJob.class)))
            .thenReturn(testJob);
        
        // When
        taskConsumer.consumeResultEvents(
            testMessage,
            "glacier.result.events",
            0,
            0L,
            acknowledgment
        );
        
        // Then
        verify(acknowledgment).acknowledge();
        verify(rasterJobRepository).findById(UUID.fromString(testMessage.getJobId()));
        verify(rasterJobRepository).save(any(RasterJob.class));
        assertEquals("FAILED", testJob.getStatus());
        assertEquals("Processing failed", testJob.getErrorMessage());
    }
    
    @Test
    void testConsumeResultEvents_CancelTask() {
        // Given
        testMessage.setTaskType("CANCEL");
        
        when(rasterJobRepository.findById(UUID.fromString(testMessage.getJobId())))
            .thenReturn(Optional.of(testJob));
        when(rasterJobRepository.save(any(RasterJob.class)))
            .thenReturn(testJob);
        
        // When
        taskConsumer.consumeTaskEvents(
            testMessage,
            "glacier.task.events",
            0,
            0L,
            acknowledgment
        );
        
        // Then
        verify(acknowledgment).acknowledge();
        verify(rasterJobRepository).findById(UUID.fromString(testMessage.getJobId()));
        verify(rasterJobRepository).save(any(RasterJob.class));
        assertEquals("CANCELLED", testJob.getStatus());
    }
    
    @Test
    void testConsumeResultEvents_MaxRetriesExceeded() {
        // Given
        testMessage.setRetryCount(3);
        testMessage.setMaxRetries(3);
        testMessage.setTaskType("PROCESSING");
        testMessage.setStatus("FAILED");
        
        when(processingTaskRepository.findByExternalId(testMessage.getTaskId()))
            .thenReturn(Optional.empty());
        when(rasterJobRepository.findById(UUID.fromString(testMessage.getJobId())))
            .thenReturn(Optional.of(testJob));
        when(rasterJobRepository.save(any(RasterJob.class)))
            .thenReturn(testJob);
        when(processingTaskRepository.save(any(ProcessingTask.class)))
            .thenReturn(testTask);
        
        // When
        taskConsumer.consumeTaskEvents(
            testMessage,
            "glacier.task.events",
            0,
            0L,
            acknowledgment
        );
        
        // Then
        verify(acknowledgment).acknowledge();
        verify(auditService).logAsync(
            eq("task"),
            eq(testMessage.getTaskId()),
            eq("FAILED"),
            contains("Max retries exceeded")
        );
    }
}