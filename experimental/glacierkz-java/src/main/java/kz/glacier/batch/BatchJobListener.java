package kz.glacier.batch;

import kz.glacier.model.BatchResult;
import kz.glacier.repository.BatchResultRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.batch.core.*;
import org.springframework.batch.core.scope.context.ChunkContext;
import org.springframework.batch.core.StepExecutionListener;
import org.springframework.batch.core.scope.context.StepContext;
import org.springframework.batch.item.Chunk;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@Component
public class BatchJobListener implements JobExecutionListener, StepExecutionListener {
    
    private static final Logger log = LoggerFactory.getLogger(BatchJobListener.class);
    
    @Autowired
    private BatchResultRepository batchResultRepository;
    
    private Map<String, Long> jobStartTimes = new HashMap<>();
    private Map<String, Long> stepStartTimes = new HashMap<>();
    
    @Override
    @Transactional
    public void beforeJob(JobExecution jobExecution) {
        String jobName = jobExecution.getJobInstance().getJobName();
        Long startTime = System.currentTimeMillis();
        jobStartTimes.put(jobExecution.getJobInstance().getInstanceId().toString(), startTime);
        
        log.info("Starting batch job: {} (ID: {})", jobName, jobExecution.getJobId());
        
        // Create batch result record
        BatchResult result = new BatchResult();
        result.setId(UUID.randomUUID());
        result.setJobName(jobName);
        result.setStartTime(LocalDateTime.now());
        result.setStatus("RUNNING");
        result.setTotalItems(0);
        result.setProcessedItems(0);
        result.setFailedItems(0);
        result.setSkippedItems(0);
        result.setExecutionTimeMs(0L);
        result.setCreatedAt(LocalDateTime.now());
        result.setCreatedBy("batch-listener");
        
        batchResultRepository.save(result);
    }
    
    @Override
    @Transactional
    public void afterJob(JobExecution jobExecution) {
        String jobName = jobExecution.getJobInstance().getJobName();
        String instanceId = jobExecution.getJobInstance().getInstanceId().toString();
        Long startTime = jobStartTimes.remove(instanceId);
        
        if (startTime == null) {
            log.warn("No start time found for job: {}", jobName);
            return;
        }
        
        long executionTime = System.currentTimeMillis() - startTime;
        
        // Find the batch result for this job
        BatchResult result = batchResultRepository
            .findByJobNameAndStatus(jobName, "RUNNING")
            .stream()
            .findFirst()
            .orElse(null);
        
        if (result == null) {
            log.warn("No running batch result found for job: {}", jobName);
            return;
        }
        
        // Update with final status
        result.setEndTime(LocalDateTime.now());
        result.setExecutionTimeMs(executionTime);
        
        switch (jobExecution.getStatus()) {
            case COMPLETED:
                result.setStatus("COMPLETED");
                log.info("Job {} completed successfully in {} ms", jobName, executionTime);
                break;
            case FAILED:
                result.setStatus("FAILED");
                result.setErrorMessage(jobExecution.getAllFailureExceptions().toString());
                log.error("Job {} failed after {} ms", jobName, executionTime);
                break;
            case STOPPED:
                result.setStatus("STOPPED");
                log.warn("Job {} was stopped after {} ms", jobName, executionTime);
                break;
            default:
                result.setStatus("UNKNOWN");
                log.warn("Job {} ended with status: {}", jobName, jobExecution.getStatus());
        }
        
        // Calculate totals from step executions
        int totalItems = 0;
        int processedItems = 0;
        int failedItems = 0;
        int skippedItems = 0;
        
        for (StepExecution stepExecution : jobExecution.getStepExecutions()) {
            totalItems += stepExecution.getReadCount() + stepExecution.getSkipCount();
            processedItems += stepExecution.getWriteCount();
            failedItems += stepExecution.getProcessSkipCount() + 
                          stepExecution.getWriteSkipCount();
            skippedItems += stepExecution.getSkipCount();
        }
        
        result.setTotalItems(totalItems);
        result.setProcessedItems(processedItems);
        result.setFailedItems(failedItems);
        result.setSkippedItems(skippedItems);
        result.setUpdatedAt(LocalDateTime.now());
        
        batchResultRepository.save(result);
        
        log.info("Job {} statistics: total={}, processed={}, failed={}, skipped={}",
            jobName, totalItems, processedItems, failedItems, skippedItems);
    }
    
    @Override
    public void beforeStep(StepExecution stepExecution) {
        String stepName = stepExecution.getStepName();
        String jobInstanceId = stepExecution.getJobExecution()
            .getJobInstance().getInstanceId().toString();
        Long startTime = System.currentTimeMillis();
        stepStartTimes.put(jobInstanceId + "_" + stepName, startTime);
        
        log.info("Starting step: {} in job: {}", 
            stepName, stepExecution.getJobExecution().getJobInstance().getJobName());
    }
    
    @Override
    @Transactional
    public ExitStatus afterStep(StepExecution stepExecution) {
        String stepName = stepExecution.getStepName();
        String jobInstanceId = stepExecution.getJobExecution()
            .getJobInstance().getInstanceId().toString();
        Long startTime = stepStartTimes.remove(jobInstanceId + "_" + stepName);
        
        if (startTime == null) {
            log.warn("No start time found for step: {}", stepName);
            return null;
        }
        
        long executionTime = System.currentTimeMillis() - startTime;
        
        log.info("Step {} completed: read={}, written={}, skipped={}, failed={}, time={} ms",
            stepName,
            stepExecution.getReadCount(),
            stepExecution.getWriteCount(),
            stepExecution.getSkipCount(),
            stepExecution.getProcessSkipCount() + stepExecution.getWriteSkipCount(),
            executionTime);
        
        // Update batch result with step statistics
        String jobName = stepExecution.getJobExecution()
            .getJobInstance().getJobName();
        
        batchResultRepository.findByJobNameAndStatus(jobName, "RUNNING")
            .stream()
            .findFirst()
            .ifPresent(result -> {
                result.setProcessedItems(result.getProcessedItems() + 
                    stepExecution.getWriteCount());
                result.setFailedItems(result.getFailedItems() + 
                    stepExecution.getProcessSkipCount() + 
                    stepExecution.getWriteSkipCount());
                result.setSkippedItems(result.getSkippedItems() + 
                    stepExecution.getSkipCount());
                result.setUpdatedAt(LocalDateTime.now());
                batchResultRepository.save(result);
            });
        
        return null;
    }
    
    @Override
    public void beforeChunk(ChunkContext context) {
        String stepName = context.getStepContext().getStepName();
        log.debug("Starting chunk processing for step: {}", stepName);
    }
    
    @Override
    public void afterChunk(ChunkContext context) {
        String stepName = context.getStepContext().getStepName();
        int readCount = context.getStepContext().getStepExecution().getReadCount();
        int writeCount = context.getStepContext().getStepExecution().getWriteCount();
        
        log.debug("Chunk completed for step {}: read={}, written={}", 
            stepName, readCount, writeCount);
    }
    
    @Override
    public void afterChunkError(ChunkContext context) {
        String stepName = context.getStepContext().getStepName();
        log.error("Chunk error occurred in step: {}", stepName);
        
        // Could implement error handling logic here
        // For now, just log the error
    }
}