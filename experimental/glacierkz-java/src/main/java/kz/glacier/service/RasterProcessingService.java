package kz.glacier.service;

import kz.glacier.model.RasterJob;
import kz.glacier.model.Glacier;
import kz.glacier.repository.RasterJobRepository;
import kz.glacier.repository.GlacierRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

@Service
@RequiredArgsConstructor
@Slf4j
public class RasterProcessingService {

    private final RasterJobRepository rasterJobRepository;
    private final GlacierRepository glacierRepository;
    private final KafkaTemplate<String, Object> kafkaTemplate;

    @Transactional
    public RasterJob submitJob(UUID glacierId, String jobType, int priority) {
        Glacier glacier = glacierRepository.findById(glacierId)
                .orElseThrow(() -> new RuntimeException("Glacier not found: " + glacierId));

        RasterJob job = new RasterJob();
        job.setGlacier(glacier);
        job.setJobType(jobType);
        job.setStatus("PENDING");
        job.setPriority(priority);
        job.setMaxRetries(3);
        job.setRetryCount(0);
        job.setCreatedBy("system");
        job.setTotalSteps(1);
        job.setCompletedSteps(0);

        RasterJob saved = rasterJobRepository.save(job);

        try {
            kafkaTemplate.send("glacier.task.events", saved.getId().toString(),
                    Map.of("jobId", saved.getId(), "type", jobType, "glacierId", glacierId.toString()));
            log.info("Sent Kafka task event for job: {}", saved.getId());
        } catch (Exception e) {
            log.error("Failed to send Kafka event for job {}: {}", saved.getId(), e.getMessage());
        }

        log.info("Submitted raster job: type={} glacier={} job={}", jobType, glacierId, saved.getId());
        return saved;
    }

    @Transactional
    public void startJob(UUID jobId) {
        RasterJob job = rasterJobRepository.findById(jobId)
                .orElseThrow(() -> new RuntimeException("Job not found: " + jobId));
        job.setStatus("RUNNING");
        job.setStartedAt(Instant.now());
        rasterJobRepository.save(job);
        log.info("Started job: {}", jobId);
    }

    @Transactional
    public void completeJob(UUID jobId) {
        RasterJob job = rasterJobRepository.findById(jobId)
                .orElseThrow(() -> new RuntimeException("Job not found: " + jobId));
        job.setStatus("COMPLETED");
        job.setCompletedAt(Instant.now());
        job.setCompletedSteps(job.getTotalSteps());
        if (job.getStartedAt() != null) {
            job.setDurationMs(Instant.now().toEpochMilli() - job.getStartedAt().toEpochMilli());
        }
        rasterJobRepository.save(job);

        try {
            kafkaTemplate.send("glacier.result.events", jobId.toString(),
                    Map.of("jobId", jobId.toString(), "status", "COMPLETED"));
        } catch (Exception e) {
            log.warn("Failed to send completion event for job {}: {}", jobId, e.getMessage());
        }

        log.info("Completed job: {} duration={}ms", jobId, job.getDurationMs());
    }

    @Transactional
    public void failJob(UUID jobId, String errorMessage) {
        RasterJob job = rasterJobRepository.findById(jobId)
                .orElseThrow(() -> new RuntimeException("Job not found: " + jobId));
        job.setStatus("FAILED");
        job.setErrorMessage(errorMessage);
        job.setCompletedAt(Instant.now());
        if (job.getStartedAt() != null) {
            job.setDurationMs(Instant.now().toEpochMilli() - job.getStartedAt().toEpochMilli());
        }
        rasterJobRepository.save(job);

        try {
            kafkaTemplate.send("glacier.result.events", jobId.toString(),
                    Map.of("jobId", jobId.toString(), "status", "FAILED", "error", errorMessage));
        } catch (Exception e) {
            log.warn("Failed to send failure event for job {}: {}", jobId, e.getMessage());
        }

        log.error("Failed job: {} error={}", jobId, errorMessage);
    }

    @Transactional
    public void updateProgress(UUID jobId, int completedSteps) {
        RasterJob job = rasterJobRepository.findById(jobId)
                .orElseThrow(() -> new RuntimeException("Job not found: " + jobId));
        job.setCompletedSteps(completedSteps);
        rasterJobRepository.save(job);
    }

    @Transactional
    public void retryJob(UUID jobId) {
        RasterJob job = rasterJobRepository.findById(jobId)
                .orElseThrow(() -> new RuntimeException("Job not found: " + jobId));

        if (!"FAILED".equals(job.getStatus())) {
            throw new RuntimeException("Only failed jobs can be retried");
        }
        if (job.getRetryCount() >= job.getMaxRetries()) {
            throw new RuntimeException("Maximum retries exceeded for job: " + jobId);
        }

        job.setStatus("PENDING");
        job.setRetryCount(job.getRetryCount() + 1);
        job.setErrorMessage(null);
        job.setStartedAt(null);
        job.setCompletedAt(null);
        job.setDurationMs(null);
        rasterJobRepository.save(job);
        log.info("Retried job: {} attempt {}/{}", jobId, job.getRetryCount(), job.getMaxRetries());
    }

    @Async
    public CompletableFuture<RasterJob> submitJobAsync(UUID glacierId, String jobType, int priority) {
        RasterJob job = submitJob(glacierId, jobType, priority);
        return CompletableFuture.completedFuture(job);
    }
}
