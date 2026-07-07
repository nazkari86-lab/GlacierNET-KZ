package kz.glacier.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import kz.glacier.dto.JobDto;
import kz.glacier.dto.PageResponse;
import kz.glacier.model.RasterJob;
import kz.glacier.repository.RasterJobRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/jobs")
@RequiredArgsConstructor
@Slf4j
@Tag(name = "Job", description = "Raster processing job management")
public class JobController {

    private final RasterJobRepository rasterJobRepository;

    @GetMapping
    @Operation(summary = "List jobs with filtering and pagination")
    public ResponseEntity<PageResponse<JobDto>> listJobs(
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String jobType,
            @RequestParam(required = false) String username,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(defaultValue = "createdAt") String sortBy,
            @RequestParam(defaultValue = "DESC") String sortDir) {

        Sort sort = Sort.by(Sort.Direction.fromString(sortDir), sortBy);
        PageRequest pageable = PageRequest.of(page, size, sort);
        Page<RasterJob> jobs;

        if (status != null && !status.isBlank()) {
            jobs = rasterJobRepository.findByStatus(status, pageable);
        } else if (username != null && !username.isBlank()) {
            jobs = rasterJobRepository.findByCreatedBy(username, pageable);
        } else {
            jobs = rasterJobRepository.findAll(pageable);
        }

        log.info("Listed {} jobs", jobs.getContent().size());
        return ResponseEntity.ok(PageResponse.of(jobs.map(JobDto::of)));
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get job by ID")
    public ResponseEntity<JobDto> getJob(@PathVariable UUID id) {
        RasterJob job = rasterJobRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Job not found"));
        return ResponseEntity.ok(JobDto.of(job));
    }

    @GetMapping("/running")
    @Operation(summary = "List currently running jobs")
    public ResponseEntity<List<JobDto>> runningJobs() {
        List<RasterJob> running = rasterJobRepository.findRunningJobs();
        return ResponseEntity.ok(running.stream().map(JobDto::of).toList());
    }

    @GetMapping("/pending")
    @Operation(summary = "List pending jobs")
    public ResponseEntity<List<JobDto>> pendingJobs() {
        List<RasterJob> pending = rasterJobRepository.findPendingOrRunningJobs();
        return ResponseEntity.ok(pending.stream().map(JobDto::of).toList());
    }

    @GetMapping("/retryable")
    @Operation(summary = "List failed jobs eligible for retry")
    public ResponseEntity<List<JobDto>> retryableJobs() {
        List<RasterJob> retryable = rasterJobRepository.findRetryableFailedJobs();
        return ResponseEntity.ok(retryable.stream().map(JobDto::of).toList());
    }

    @GetMapping("/by-glacier/{glacierId}")
    @Operation(summary = "List jobs for a specific glacier")
    public ResponseEntity<List<JobDto>> jobsByGlacier(@PathVariable UUID glacierId) {
        List<RasterJob> jobs = rasterJobRepository.findByGlacierId(glacierId);
        return ResponseEntity.ok(jobs.stream().map(JobDto::of).toList());
    }

    @GetMapping("/completed-by-glacier/{glacierId}")
    @Operation(summary = "List completed jobs for a specific glacier")
    public ResponseEntity<List<JobDto>> completedJobsByGlacier(@PathVariable UUID glacierId) {
        List<RasterJob> jobs = rasterJobRepository.findCompletedByGlacierId(glacierId);
        return ResponseEntity.ok(jobs.stream().map(JobDto::of).toList());
    }

    @GetMapping("/by-date-range")
    @Operation(summary = "List jobs within a date range")
    public ResponseEntity<PageResponse<JobDto>> jobsByDateRange(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.INSTANT) Instant from,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.INSTANT) Instant to,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Page<RasterJob> jobs = rasterJobRepository.findByDateRange(from, to, PageRequest.of(page, size, Sort.by("createdAt").descending()));
        return ResponseEntity.ok(PageResponse.of(jobs.map(JobDto::of)));
    }

    @GetMapping("/high-priority")
    @Operation(summary = "List high-priority pending jobs")
    public ResponseEntity<List<JobDto>> highPriorityJobs(
            @RequestParam(defaultValue = "3") int maxPriority) {
        List<RasterJob> jobs = rasterJobRepository.findHighPriorityPending(maxPriority);
        return ResponseEntity.ok(jobs.stream().map(JobDto::of).toList());
    }

    @GetMapping("/statistics")
    @Operation(summary = "Get job statistics")
    public ResponseEntity<Map<String, Object>> statistics() {
        Map<String, Object> stats = new java.util.HashMap<>();
        stats.put("pending", rasterJobRepository.countByStatus("PENDING"));
        stats.put("running", rasterJobRepository.countByStatus("RUNNING"));
        stats.put("completed", rasterJobRepository.countByStatus("COMPLETED"));
        stats.put("failed", rasterJobRepository.countByStatus("FAILED"));
        return ResponseEntity.ok(stats);
    }

    @PostMapping("/{id}/cancel")
    @Operation(summary = "Cancel a running or pending job")
    public ResponseEntity<JobDto> cancelJob(@PathVariable UUID id) {
        RasterJob job = rasterJobRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Job not found"));

        if (!"PENDING".equals(job.getStatus()) && !"RUNNING".equals(job.getStatus())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Job is not cancellable in current state: " + job.getStatus());
        }

        job.setStatus("CANCELLED");
        job.setErrorMessage("Cancelled by user");
        RasterJob saved = rasterJobRepository.save(job);
        log.info("Cancelled job: {} ({})", saved.getJobType(), id);
        return ResponseEntity.ok(JobDto.of(saved));
    }

    @PostMapping("/{id}/retry")
    @Operation(summary = "Retry a failed job")
    public ResponseEntity<JobDto> retryJob(@PathVariable UUID id) {
        RasterJob job = rasterJobRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Job not found"));

        if (!"FAILED".equals(job.getStatus())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Only failed jobs can be retried");
        }

        if (job.getRetryCount() >= job.getMaxRetries()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Maximum retries exceeded");
        }

        job.setStatus("PENDING");
        job.setRetryCount(job.getRetryCount() + 1);
        job.setErrorMessage(null);
        job.setStartedAt(null);
        job.setCompletedAt(null);
        job.setDurationMs(null);
        RasterJob saved = rasterJobRepository.save(job);
        log.info("Retried job: {} ({}) attempt {}/{}", saved.getJobType(), id, saved.getRetryCount(), saved.getMaxRetries());
        return ResponseEntity.ok(JobDto.of(saved));
    }
}
