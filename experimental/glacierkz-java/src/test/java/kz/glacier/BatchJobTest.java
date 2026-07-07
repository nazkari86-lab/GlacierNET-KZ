package kz.glacier;

import kz.glacier.config.BatchConfig;
import kz.glacier.model.SatelliteImage;
import kz.glacier.model.RasterJob;
import kz.glacier.repository.SatelliteImageRepository;
import kz.glacier.repository.RasterJobRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.batch.core.*;
import org.springframework.batch.test.JobLauncherTestUtils;
import org.springframework.batch.test.JobRepositoryTestUtils;
import org.springframework.batch.test.context.SpringBatchTest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit.jupiter.SpringExtension;

import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(SpringExtension.class)
@SpringBatchTest
@ContextConfiguration(classes = {BatchConfig.class})
public class BatchJobTest {
    
    @Autowired
    private JobLauncherTestUtils jobLauncherTestUtils;
    
    @Autowired
    private JobRepositoryTestUtils jobRepositoryTestUtils;
    
    @MockBean
    private SatelliteImageRepository satelliteImageRepository;
    
    @MockBean
    private RasterJobRepository rasterJobRepository;
    
    private SatelliteImage testSatelliteImage;
    private RasterJob testRasterJob;
    
    @BeforeEach
    void setUp() {
        jobRepositoryTestUtils.removeJobExecutions();
        
        testSatelliteImage = new SatelliteImage();
        testSatelliteImage.setId(UUID.randomUUID());
        testSatelliteImage.setGlacierId(UUID.randomUUID());
        testSatelliteImage.setFilePath("/data/sentinel2/test.tif");
        testSatelliteImage.setSatellite("SENTINEL-2");
        testSatelliteImage.setCloudCover(15.5);
        testSatelliteImage.setResolution(10.0);
        testSatelliteImage.setStatus("NEW");
        testSatelliteImage.setChecksum("abc123def456");
        testSatelliteImage.setCreatedAt(LocalDateTime.now());
        
        testRasterJob = new RasterJob();
        testRasterJob.setId(UUID.randomUUID());
        testRasterJob.setGlacierId(testSatelliteImage.getGlacierId());
        testRasterJob.setRasterPath(testSatelliteImage.getFilePath());
        testRasterJob.setStatus("PENDING");
        testRasterJob.setPriority(3);
        testRasterJob.setRetryCount(0);
        testRasterJob.setMaxRetries(3);
        testRasterJob.setCreatedAt(LocalDateTime.now());
    }
    
    @Test
    void testSatelliteImageProcessingJob() throws Exception {
        // Given
        List<SatelliteImage> images = Arrays.asList(testSatelliteImage);
        
        when(satelliteImageRepository.findByStatus("NEW"))
            .thenReturn(images);
        when(rasterJobRepository.save(any(RasterJob.class)))
            .thenReturn(testRasterJob);
        when(satelliteImageRepository.save(any(SatelliteImage.class)))
            .thenReturn(testSatelliteImage);
        
        // When
        JobParameters jobParameters = new JobParametersBuilder()
            .addLong("time", System.currentTimeMillis())
            .toJobParameters();
        
        JobExecution jobExecution = jobLauncherTestUtils
            .run("satelliteImageProcessingJob", jobParameters);
        
        // Then
        assertNotNull(jobExecution);
        assertEquals(BatchStatus.COMPLETED, jobExecution.getStatus());
        
        List<StepExecution> stepExecutions = jobExecution.getStepExecutions()
            .stream()
            .collect(java.util.stream.Collectors.toList());
        
        assertFalse(stepExecutions.isEmpty());
        
        verify(satelliteImageRepository).findByStatus("NEW");
        verify(rasterJobRepository, atLeastOnce()).save(any(RasterJob.class));
    }
    
    @Test
    void testJobWithNoImages() throws Exception {
        // Given
        when(satelliteImageRepository.findByStatus("NEW"))
            .thenReturn(Arrays.asList());
        
        // When
        JobParameters jobParameters = new JobParametersBuilder()
            .addLong("time", System.currentTimeMillis())
            .toJobParameters();
        
        JobExecution jobExecution = jobLauncherTestUtils
            .run("satelliteImageProcessingJob", jobParameters);
        
        // Then
        assertNotNull(jobExecution);
        assertEquals(BatchStatus.COMPLETED, jobExecution.getStatus());
        
        verify(satelliteImageRepository).findByStatus("NEW");
        verify(rasterJobRepository, never()).save(any(RasterJob.class));
    }
    
    @Test
    void testJobWithMultipleImages() throws Exception {
        // Given
        SatelliteImage image2 = new SatelliteImage();
        image2.setId(UUID.randomUUID());
        image2.setGlacierId(UUID.randomUUID());
        image2.setFilePath("/data/sentinel2/test2.tif");
        image2.setSatellite("SENTINEL-2");
        image2.setCloudCover(25.0);
        image2.setResolution(10.0);
        image2.setStatus("NEW");
        image2.setChecksum("xyz789");
        image2.setCreatedAt(LocalDateTime.now());
        
        List<SatelliteImage> images = Arrays.asList(testSatelliteImage, image2);
        
        when(satelliteImageRepository.findByStatus("NEW"))
            .thenReturn(images);
        when(rasterJobRepository.save(any(RasterJob.class)))
            .thenReturn(testRasterJob);
        when(satelliteImageRepository.save(any(SatelliteImage.class)))
            .thenReturn(testSatelliteImage);
        
        // When
        JobParameters jobParameters = new JobParametersBuilder()
            .addLong("time", System.currentTimeMillis())
            .toJobParameters();
        
        JobExecution jobExecution = jobLauncherTestUtils
            .run("satelliteImageProcessingJob", jobParameters);
        
        // Then
        assertNotNull(jobExecution);
        assertEquals(BatchStatus.COMPLETED, jobExecution.getStatus());
        
        verify(satelliteImageRepository).findByStatus("NEW");
        verify(rasterJobRepository, times(2)).save(any(RasterJob.class));
        verify(satelliteImageRepository, times(2)).save(any(SatelliteImage.class));
    }
    
    @Test
    void testJobWithFailedProcessing() throws Exception {
        // Given
        when(satelliteImageRepository.findByStatus("NEW"))
            .thenReturn(Arrays.asList(testSatelliteImage));
        when(rasterJobRepository.save(any(RasterJob.class)))
            .thenThrow(new RuntimeException("Database error"));
        
        // When
        JobParameters jobParameters = new JobParametersBuilder()
            .addLong("time", System.currentTimeMillis())
            .toJobParameters();
        
        JobExecution jobExecution = jobLauncherTestUtils
            .run("satelliteImageProcessingJob", jobParameters);
        
        // Then
        assertNotNull(jobExecution);
        assertEquals(BatchStatus.FAILED, jobExecution.getStatus());
        
        verify(satelliteImageRepository).findByStatus("NEW");
        verify(rasterJobRepository).save(any(RasterJob.class));
    }
    
    @Test
    void testJobParameters() {
        // Given
        JobParameters expectedParams = new JobParametersBuilder()
            .addLong("time", 1234567890L)
            .addString("jobName", "testJob")
            .toJobParameters();
        
        // When
        jobLauncherTestUtils.setJobParameters(expectedParams);
        
        // Then
        assertNotNull(jobLauncherTestUtils.getJobParameters());
        assertEquals(1234567890L, 
            jobLauncherTestUtils.getJobParameters().getLong("time"));
        assertEquals("testJob", 
            jobLauncherTestUtils.getJobParameters().getString("jobName"));
    }
    
    @Test
    void testJobRestart() throws Exception {
        // Given
        when(satelliteImageRepository.findByStatus("NEW"))
            .thenReturn(Arrays.asList(testSatelliteImage));
        when(rasterJobRepository.save(any(RasterJob.class)))
            .thenReturn(testRasterJob);
        when(satelliteImageRepository.save(any(SatelliteImage.class)))
            .thenReturn(testSatelliteImage);
        
        // First execution
        JobParameters jobParameters = new JobParametersBuilder()
            .addLong("time", System.currentTimeMillis())
            .toJobParameters();
        
        JobExecution firstExecution = jobLauncherTestUtils
            .run("satelliteImageProcessingJob", jobParameters);
        
        // When - restart
        JobExecution restartExecution = jobLauncherTestUtils
            .restart(firstExecution.getJobInstance().getInstanceId().toString());
        
        // Then
        assertNotNull(restartExecution);
        // Restart should create new execution
    }
}