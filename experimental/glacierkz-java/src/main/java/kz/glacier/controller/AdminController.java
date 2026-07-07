package kz.glacier.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import kz.glacier.model.AuditLog;
import kz.glacier.model.BatchResult;
import kz.glacier.model.SatelliteImage;
import kz.glacier.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/admin")
@RequiredArgsConstructor
@Slf4j
@Tag(name = "Admin", description = "Administrative operations and statistics")
public class AdminController {

    private final GlacierRepository glacierRepository;
    private final RasterJobRepository rasterJobRepository;
    private final BatchResultRepository batchResultRepository;
    private final SatelliteImageRepository satelliteImageRepository;
    private final AnalysisReportRepository analysisReportRepository;
    private final AuditLogRepository auditLogRepository;
    private final UserRepository userRepository;

    @GetMapping("/dashboard")
    @Operation(summary = "Get admin dashboard statistics")
    public ResponseEntity<Map<String, Object>> dashboard() {
        Map<String, Object> stats = new java.util.HashMap<>();
        stats.put("glaciers", glacierRepository.countActive());
        stats.put("jobs", Map.of(
                "pending", rasterJobRepository.countByStatus("PENDING"),
                "running", rasterJobRepository.countByStatus("RUNNING"),
                "completed", rasterJobRepository.countByStatus("COMPLETED"),
                "failed", rasterJobRepository.countByStatus("FAILED")
        ));
        stats.put("results", Map.of(
                "completed", batchResultRepository.countByStatus("COMPLETED"),
                "failed", batchResultRepository.countByStatus("FAILED")
        ));
        stats.put("images", satelliteImageRepository.count());
        stats.put("reports", analysisReportRepository.count());
        stats.put("users", userRepository.countActive());
        return ResponseEntity.ok(stats);
    }

    @GetMapping("/audit-logs")
    @Operation(summary = "Get audit logs with pagination")
    public ResponseEntity<Page<AuditLog>> auditLogs(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "50") int size,
            @RequestParam(required = false) String action,
            @RequestParam(required = false) UUID userId) {

        Page<AuditLog> logs;
        if (userId != null) {
            logs = auditLogRepository.findByUserId(userId, PageRequest.of(page, size, Sort.by("createdAt").descending()));
        } else if (action != null && !action.isBlank()) {
            logs = auditLogRepository.findByAction(action, PageRequest.of(page, size, Sort.by("createdAt").descending()));
        } else {
            logs = auditLogRepository.findAll(PageRequest.of(page, size, Sort.by("createdAt").descending()));
        }
        return ResponseEntity.ok(logs);
    }

    @GetMapping("/audit-logs/failed")
    @Operation(summary = "Get failed audit log entries")
    public ResponseEntity<Page<AuditLog>> failedAuditLogs(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "50") int size) {
        return ResponseEntity.ok(auditLogRepository.findFailedActions(PageRequest.of(page, size)));
    }

    @GetMapping("/audit-logs/slow")
    @Operation(summary = "Get slow operations from audit logs")
    public ResponseEntity<List<AuditLog>> slowOperations(
            @RequestParam(defaultValue = "5000") long thresholdMs) {
        return ResponseEntity.ok(auditLogRepository.findSlowOperations(thresholdMs));
    }

    @GetMapping("/audit-logs/by-date-range")
    @Operation(summary = "Get audit logs within a date range")
    public ResponseEntity<Page<AuditLog>> auditLogsByDateRange(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.INSTANT) Instant from,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.INSTANT) Instant to,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "50") int size) {
        return ResponseEntity.ok(auditLogRepository.findByDateRange(from, to, PageRequest.of(page, size)));
    }

    @GetMapping("/audit-logs/by-ip/{ipAddress}")
    @Operation(summary = "Get audit logs from a specific IP")
    public ResponseEntity<List<AuditLog>> auditLogsByIp(@PathVariable String ipAddress) {
        return ResponseEntity.ok(auditLogRepository.findByIpAddress(ipAddress));
    }

    @GetMapping("/satellite-images")
    @Operation(summary = "List satellite images")
    public ResponseEntity<Page<SatelliteImage>> satelliteImages(
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Page<SatelliteImage> images;
        if (status != null && !status.isBlank()) {
            images = satelliteImageRepository.findByProcessingStatus(status, PageRequest.of(page, size, Sort.by("captureDate").descending()));
        } else {
            images = satelliteImageRepository.findAll(PageRequest.of(page, size, Sort.by("captureDate").descending()));
        }
        return ResponseEntity.ok(images);
    }

    @GetMapping("/satellite-images/pending")
    @Operation(summary = "List pending satellite images")
    public ResponseEntity<List<SatelliteImage>> pendingImages() {
        return ResponseEntity.ok(satelliteImageRepository.findPendingImages());
    }

    @GetMapping("/batch-results")
    @Operation(summary = "List batch processing results")
    public ResponseEntity<List<BatchResult>> batchResults(
            @RequestParam(required = false) UUID jobId) {
        if (jobId != null) {
            return ResponseEntity.ok(batchResultRepository.findByRasterJobId(jobId));
        }
        return ResponseEntity.ok(batchResultRepository.findAll(PageRequest.of(0, 100, Sort.by("createdAt").descending())).getContent());
    }

    @GetMapping("/health")
    @Operation(summary = "System health check")
    public ResponseEntity<Map<String, Object>> health() {
        Map<String, Object> health = new java.util.HashMap<>();
        health.put("status", "UP");
        health.put("timestamp", Instant.now().toString());
        health.put("glacierCount", glacierRepository.countActive());
        health.put("runningJobs", rasterJobRepository.countByStatus("RUNNING"));
        health.put("pendingJobs", rasterJobRepository.countByStatus("PENDING"));
        return ResponseEntity.ok(health);
    }
}
