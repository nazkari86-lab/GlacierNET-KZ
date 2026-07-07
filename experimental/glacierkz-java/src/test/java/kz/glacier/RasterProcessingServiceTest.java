package kz.glacier;

import kz.glacier.dto.JobDto;
import kz.glacier.model.RasterJob;
import kz.glacier.repository.RasterJobRepository;
import kz.glacier.service.AuditService;
import kz.glacier.service.CacheService;
import kz.glacier.service.RasterProcessingService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.LocalDateTime;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
public class RasterProcessingServiceTest {
    
    @Mock
    private RasterJobRepository rasterJobRepository;
    
    @Mock
    private KafkaTemplate<String, Object> kafkaTemplate;
    
    @Mock
    private AuditService auditService;
    
    @Mock
    private CacheService cacheService;
    
    @InjectMocks
    private RasterProcessingService rasterProcessingService;
    
    private RasterJob testJob;
    private JobDto testJobDto;
    
    @BeforeEach
    void setUp() {
        testJob = new RasterJob();
        testJob.setId(UUID.randomUUID());
        testJob.setGlacierId(UUID.randomUUID());
        testJob.setRasterPath("/data/rasters/test.tif");
        testJob.setOriginalPath("/data/original/test.tif");
        testJob.setStatus("PENDING");
        testJob.setPriority(5);
        testJob.setParameters("{\"resolution\": 10}");
        testJob.setRetryCount(0);
        testJob.setMaxRetries(3);
        testJob.setCreatedAt(LocalDateTime.now());
        testJob.setUpdatedAt(LocalDateTime.now());
        testJob.setCreatedBy("test-user");
        
        testJobDto = JobDto.of(testJob);
        
        ReflectionTestUtils.setField(rasterProcessingService, 
            "processingTopic", "glacier.task.events");
    }
    
    @Test
    void testSubmitJob() {
        // Given
        when(rasterJobRepository.save(any(RasterJob.class)))
            .thenReturn(testJob);
        when(kafkaTemplate.send(anyString(), anyString(), any()))
            .thenReturn(null);
        
        // When
        JobDto result = rasterProcessingService.submitJob(testJobDto);
        
        // Then
        assertNotNull(result);
        assertEquals("PENDING", result.getStatus());
        
        verify(rasterJobRepository).save(any(RasterJob.class));
        verify(kafkaTemplate).send(anyString(), anyString(), any());
    }
    
    @Test
    void testStartProcessing() {
        // Given
        when(rasterJobRepository.findById(testJob.getId()))
            .thenReturn(Optional.of(testJob));
        when(rasterJobRepository.save(any(RasterJob.class)))
            .thenReturn(testJob);
        
        // When
        rasterProcessingService.startProcessing(testJob.getId());
        
        // Then
        assertEquals("RUNNING", testJob.getStatus());
        assertNotNull(testJob.getStartedAt());
        
        verify(rasterJobRepository).findById(testJob.getId());
        verify(rasterJobRepository).save(any(RasterJob.class));
    }
    
    @Test
    void testStartProcessing_JobNotFound() {
        // Given
        UUID nonExistentId = UUID.randomUUID();
        when(rasterJobRepository.findById(nonExistentId))
            .thenReturn(Optional.empty());
        
        // When & Then
        assertThrows(RuntimeException.class, 
            () -> rasterProcessingService.startProcessing(nonExistentId));
        
        verify(rasterJobRepository).findById(nonExistentId);
        verify(rasterJobRepository, never()).save(any(RasterJob.class));
    }
    
    @Test
    void testCompleteProcessing() {
        // Given
        when(rasterJobRepository.findById(testJob.getId()))
            .thenReturn(Optional.of(testJob));
        when(rasterJobRepository.save(any(RasterJob.class)))
            .thenReturn(testJob);
        
        String resultPath = "/data/results/test_result.tif";
        
        // When
        rasterProcessingService.completeProcessing(testJob.getId(), resultPath);
        
        // Then
        assertEquals("COMPLETED", testJob.getStatus());
        assertEquals(resultPath, testJob.getResultPath());
        assertNotNull(testJob.getCompletedAt());
        
        verify(rasterJobRepository).findById(testJob.getId());
        verify(rasterJobRepository).save(any(RasterJob.class));
        verify(cacheService).evictAll();
    }
    
    @Test
    void testFailProcessing() {
        // Given
        when(rasterJobRepository.findById(testJob.getId()))
            .thenReturn(Optional.of(testJob));
        when(rasterJobRepository.save(any(RasterJob.class)))
            .thenReturn(testJob);
        
        String errorMessage = "Processing failed due to invalid raster format";
        
        // When
        rasterProcessingService.failProcessing(testJob.getId(), errorMessage);
        
        // Then
        assertEquals("FAILED", testJob.getStatus());
        assertEquals(errorMessage, testJob.getErrorMessage());
        assertNotNull(testJob.getCompletedAt());
        
        verify(rasterJobRepository).findById(testJob.getId());
        verify(rasterJobRepository).save(any(RasterJob.class));
    }
    
    @Test
    void testUpdateProgress() {
        // Given
        when(rasterJobRepository.findById(testJob.getId()))
            .thenReturn(Optional.of(testJob));
        when(rasterJobRepository.save(any(RasterJob.class)))
            .thenReturn(testJob);
        
        // When
        rasterProcessingService.updateProgress(testJob.getId(), 75);
        
        // Then
        assertEquals(75, testJob.getProgress());
        
        verify(rasterJobRepository).findById(testJob.getId());
        verify(rasterJobRepository).save(any(RasterJob.class));
    }
    
    @Test
    void testUpdateProgress_InvalidPercentage() {
        // Given
        when(rasterJobRepository.findById(testJob.getId()))
            .thenReturn(Optional.of(testJob));
        
        // When & Then - negative percentage
        assertThrows(IllegalArgumentException.class,
            () -> rasterProcessingService.updateProgress(testJob.getId(), -10));
        
        // When & Then - over 100%
        assertThrows(IllegalArgumentException.class,
            () -> rasterProcessingService.updateProgress(testJob.getId(), 150));
        
        verify(rasterJobRepository, never()).save(any(RasterJob.class));
    }
    
    @Test
    void testRetryJob() {
        // Given
        testJob.setStatus("FAILED");
        testJob.setRetryCount(1);
        
        when(rasterJobRepository.findById(testJob.getId()))
            .thenReturn(Optional.of(testJob));
        when(rasterJobRepository.save(any(RasterJob.class)))
            .thenReturn(testJob);
        when(kafkaTemplate.send(anyString(), anyString(), any()))
            .thenReturn(null);
        
        // When
        JobDto result = rasterProcessingService.retryJob(testJob.getId());
        
        // Then
        assertNotNull(result);
        assertEquals("PENDING", testJob.getStatus());
        assertEquals(2, testJob.getRetryCount());
        
        verify(rasterJobRepository).findById(testJob.getId());
        verify(rasterJobRepository).save(any(RasterJob.class));
        verify(kafkaTemplate).send(anyString(), anyString(), any());
    }
    
    @Test
    void testRetryJob_MaxRetriesExceeded() {
        // Given
        testJob.setStatus("FAILED");
        testJob.setRetryCount(3);
        testJob.setMaxRetries(3);
        
        when(rasterJobRepository.findById(testJob.getId()))
            .thenReturn(Optional.of(testJob));
        
        // When & Then
        assertThrows(RuntimeException.class,
            () -> rasterProcessingService.retryJob(testJob.getId()));
        
        verify(rasterJobRepository).findById(testJob.getId());
        verify(rasterJobRepository, never()).save(any(RasterJob.class));
    }
    
    @Test
    void testCancelJob() {
        // Given
        testJob.setStatus("RUNNING");
        
        when(rasterJobRepository.findById(testJob.getId()))
            .thenReturn(Optional.of(testJob));
        when(rasterJobRepository.save(any(RasterJob.class)))
            .thenReturn(testJob);
        
        // When
        rasterProcessingService.cancelJob(testJob.getId());
        
        // Then
        assertEquals("CANCELLED", testJob.getStatus());
        
        verify(rasterJobRepository).findById(testJob.getId());
        verify(rasterJobRepository).save(any(RasterJob.class));
    }
    
    @Test
    void testCancelJob_AlreadyCompleted() {
        // Given
        testJob.setStatus("COMPLETED");
        
        when(rasterJobRepository.findById(testJob.getId()))
            .thenReturn(Optional.of(testJob));
        
        // When & Then
        assertThrows(RuntimeException.class,
            () -> rasterProcessingService.cancelJob(testJob.getId()));
        
        verify(rasterJobRepository).findById(testJob.getId());
        verify(rasterJobRepository, never()).save(any(RasterJob.class));
    }
}