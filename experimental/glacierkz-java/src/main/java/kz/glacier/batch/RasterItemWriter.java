package kz.glacier.batch;

import kz.glacier.model.RasterJob;
import kz.glacier.repository.RasterJobRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.batch.item.Chunk;
import org.springframework.batch.item.ItemWriter;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Component
public class RasterItemWriter implements ItemWriter<RasterJob> {
    
    private static final Logger log = LoggerFactory.getLogger(RasterItemWriter.class);
    
    @Autowired
    private RasterJobRepository rasterJobRepository;
    
    @Override
    @Transactional
    public void write(Chunk<? extends RasterJob> chunk) throws Exception {
        List<? extends RasterJob> jobs = chunk.getItems();
        log.info("Writing {} RasterJobs to database", jobs.size());
        
        if (jobs.isEmpty()) {
            log.debug("No jobs to write");
            return;
        }
        
        List<RasterJob> savedJobs = new ArrayList<>();
        List<RasterJob> failedJobs = new ArrayList<>();
        
        for (RasterJob job : jobs) {
            try {
                // Validate job before saving
                if (!validateJob(job)) {
                    log.warn("Invalid job skipped: {}", job.getId());
                    failedJobs.add(job);
                    continue;
                }
                
                // Check for duplicate jobs
                if (isDuplicateJob(job)) {
                    log.warn("Duplicate job detected: {}", job.getId());
                    continue;
                }
                
                // Set metadata
                if (job.getCreatedAt() == null) {
                    job.setCreatedAt(LocalDateTime.now());
                }
                job.setUpdatedAt(LocalDateTime.now());
                
                // Save the job
                RasterJob savedJob = rasterJobRepository.save(job);
                savedJobs.add(savedJob);
                
                log.debug("Successfully saved job: {}", savedJob.getId());
                
            } catch (Exception e) {
                log.error("Failed to save job {}: {}", job.getId(), 
                    e.getMessage(), e);
                failedJobs.add(job);
            }
        }
        
        log.info("Write complete: {} successful, {} failed out of {} total", 
            savedJobs.size(), failedJobs.size(), jobs.size());
        
        if (!failedJobs.isEmpty()) {
            log.warn("Failed jobs: {}", failedJobs.stream()
                .map(j -> j.getId().toString())
                .reduce((a, b) -> a + ", " + b)
                .orElse("unknown"));
        }
    }
    
    private boolean validateJob(RasterJob job) {
        if (job == null) {
            return false;
        }
        
        if (job.getGlacierId() == null) {
            log.warn("Job missing glacier ID");
            return false;
        }
        
        if (job.getRasterPath() == null || job.getRasterPath().isEmpty()) {
            log.warn("Job missing raster path");
            return false;
        }
        
        if (job.getStatus() == null || job.getStatus().isEmpty()) {
            log.warn("Job missing status");
            return false;
        }
        
        // Validate status is one of allowed values
        String[] allowedStatuses = {"PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"};
        boolean validStatus = false;
        for (String status : allowedStatuses) {
            if (status.equals(job.getStatus())) {
                validStatus = true;
                break;
            }
        }
        
        if (!validStatus) {
            log.warn("Invalid job status: {}", job.getStatus());
            return false;
        }
        
        // Validate retry count
        if (job.getRetryCount() == null) {
            job.setRetryCount(0);
        }
        
        if (job.getMaxRetries() == null) {
            job.setMaxRetries(3);
        }
        
        if (job.getRetryCount() > job.getMaxRetries()) {
            log.warn("Job retry count exceeds max retries");
            return false;
        }
        
        // Validate priority
        if (job.getPriority() == null) {
            job.setPriority(5);
        }
        
        if (job.getPriority() < 1 || job.getPriority() > 10) {
            log.warn("Invalid priority value: {}", job.getPriority());
            job.setPriority(5);
        }
        
        return true;
    }
    
    private boolean isDuplicateJob(RasterJob job) {
        if (job.getId() == null) {
            return false;
        }
        
        // Check if job with same glacier and raster path already exists
        // (excluding current job)
        List<RasterJob> existingJobs = rasterJobRepository
            .findByGlacierId(job.getGlacierId());
        
        for (RasterJob existing : existingJobs) {
            if (!existing.getId().equals(job.getId()) &&
                existing.getRasterPath().equals(job.getRasterPath()) &&
                !existing.getStatus().equals("FAILED")) {
                return true;
            }
        }
        
        return false;
    }
}