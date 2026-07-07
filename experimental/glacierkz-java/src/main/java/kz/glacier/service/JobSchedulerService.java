package kz.glacier.service;

import kz.glacier.model.RasterJob;
import kz.glacier.repository.RasterJobRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;

@Service
@RequiredArgsConstructor
@Slf4j
public class JobSchedulerService {

    private final RasterJobRepository rasterJobRepository;
    private final RasterProcessingService rasterProcessingService;

    @Scheduled(fixedDelay = 60000, initialDelay = 30000)
    @Transactional
    public void processPendingJobs() {
        List<RasterJob> pendingJobs = rasterJobRepository.findPendingOrRunningJobs();
        long pendingCount = pendingJobs.stream().filter(j -> "PENDING".equals(j.getStatus())).count();
        long runningCount = pendingJobs.stream().filter(j -> "RUNNING".equals(j.getStatus())).count();

        log.debug("Job queue: {} pending, {} running", pendingCount, runningCount);

        List<RasterJob> runnable = pendingJobs.stream()
                .filter(j -> "PENDING".equals(j.getStatus()))
                .limit(5)
                .toList();

        for (RasterJob job : runnable) {
            try {
                rasterProcessingService.startJob(job.getId());
                log.info("Auto-started job: {} ({})", job.getJobType(), job.getId());
            } catch (Exception e) {
                log.error("Failed to start job {}: {}", job.getId(), e.getMessage());
            }
        }
    }

    @Scheduled(fixedDelay = 120000, initialDelay = 60000)
    @Transactional
    public void detectStaleJobs() {
        Instant staleThreshold = Instant.now().minusMillis(3600000);
        List<RasterJob> staleJobs = rasterJobRepository.findStaleRunningJobs(staleThreshold);

        for (RasterJob job : staleJobs) {
            log.warn("Detected stale job: {} started at {}", job.getId(), job.getStartedAt());
            try {
                rasterProcessingService.failJob(job.getId(), "Job timed out - marked as stale");
            } catch (Exception e) {
                log.error("Failed to mark stale job {}: {}", job.getId(), e.getMessage());
            }
        }
    }

    @Scheduled(cron = "0 0 3 * * *")
    @Transactional
    public void retryFailedJobs() {
        List<RasterJob> retryable = rasterJobRepository.findRetryableFailedJobs();
        log.info("Found {} retryable failed jobs", retryable.size());

        for (RasterJob job : retryable) {
            try {
                rasterProcessingService.retryJob(job.getId());
                log.info("Auto-retried job: {} ({})", job.getJobType(), job.getId());
            } catch (Exception e) {
                log.error("Failed to retry job {}: {}", job.getId(), e.getMessage());
            }
        }
    }

    @Scheduled(cron = "0 0 4 * * *")
    @Transactional(readOnly = true)
    public void generateDailyStats() {
        long pending = rasterJobRepository.countByStatus("PENDING");
        long running = rasterJobRepository.countByStatus("RUNNING");
        long completed = rasterJobRepository.countByStatus("COMPLETED");
        long failed = rasterJobRepository.countByStatus("FAILED");

        log.info("Daily job stats - pending={}, running={}, completed={}, failed={}",
                pending, running, completed, failed);
    }

    @Scheduled(fixedDelay = 300000)
    @Transactional(readOnly = true)
    public void monitorQueueHealth() {
        long pending = rasterJobRepository.countByStatus("PENDING");
        if (pending > 100) {
            log.warn("High pending job count: {}. Queue may be backlogged.", pending);
        }
        long failed = rasterJobRepository.countByStatus("FAILED");
        if (failed > 50) {
            log.warn("High failed job count: {}. Check for systemic issues.", failed);
        }
    }
}
