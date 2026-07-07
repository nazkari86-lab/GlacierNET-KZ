package kz.glacier.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import kz.glacier.dto.PageResponse;
import kz.glacier.dto.ReportDto;
import kz.glacier.model.AnalysisReport;
import kz.glacier.repository.AnalysisReportRepository;
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

import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/reports")
@RequiredArgsConstructor
@Slf4j
@Tag(name = "Report", description = "Analysis report operations")
public class ReportController {

    private final AnalysisReportRepository analysisReportRepository;

    @GetMapping
    @Operation(summary = "List reports with filtering and pagination")
    public ResponseEntity<PageResponse<ReportDto>> listReports(
            @RequestParam(required = false) String reportType,
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {

        Page<AnalysisReport> reports;
        if (reportType != null && !reportType.isBlank()) {
            reports = analysisReportRepository.findByReportType(reportType, PageRequest.of(page, size, Sort.by("createdAt").descending()));
        } else if (status != null && !status.isBlank()) {
            reports = analysisReportRepository.findByStatus(status, PageRequest.of(page, size, Sort.by("createdAt").descending()));
        } else {
            reports = analysisReportRepository.findAll(PageRequest.of(page, size, Sort.by("createdAt").descending()));
        }

        return ResponseEntity.ok(PageResponse.of(reports.map(ReportDto::of)));
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get report by ID")
    public ResponseEntity<ReportDto> getReport(@PathVariable UUID id) {
        AnalysisReport report = analysisReportRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Report not found"));
        return ResponseEntity.ok(ReportDto.of(report));
    }

    @GetMapping("/by-glacier/{glacierId}")
    @Operation(summary = "List reports for a specific glacier")
    public ResponseEntity<List<ReportDto>> reportsByGlacier(@PathVariable UUID glacierId) {
        List<AnalysisReport> reports = analysisReportRepository.findByGlacierId(glacierId);
        return ResponseEntity.ok(reports.stream().map(ReportDto::of).toList());
    }

    @GetMapping("/with-changes")
    @Operation(summary = "List reports where change was detected")
    public ResponseEntity<List<ReportDto>> reportsWithChanges() {
        List<AnalysisReport> reports = analysisReportRepository.findReportsWithChanges();
        return ResponseEntity.ok(reports.stream().map(ReportDto::of).toList());
    }

    @GetMapping("/drafts")
    @Operation(summary = "List draft reports")
    public ResponseEntity<PageResponse<ReportDto>> draftReports(
            @RequestParam(defaultValue = "0") int page, @RequestParam(defaultValue = "20") int size) {
        Page<AnalysisReport> drafts = analysisReportRepository.findDraftReports(PageRequest.of(page, size));
        return ResponseEntity.ok(PageResponse.of(drafts.map(ReportDto::of)));
    }

    @GetMapping("/approved")
    @Operation(summary = "List approved reports")
    public ResponseEntity<PageResponse<ReportDto>> approvedReports(
            @RequestParam(defaultValue = "0") int page, @RequestParam(defaultValue = "20") int size) {
        Page<AnalysisReport> approved = analysisReportRepository.findApprovedReports(PageRequest.of(page, size));
        return ResponseEntity.ok(PageResponse.of(approved.map(ReportDto::of)));
    }

    @GetMapping("/by-date-range")
    @Operation(summary = "List reports within a date range")
    public ResponseEntity<List<ReportDto>> reportsByDateRange(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to) {
        List<AnalysisReport> reports = analysisReportRepository.findByDateRange(from, to);
        return ResponseEntity.ok(reports.stream().map(ReportDto::of).toList());
    }

    @GetMapping("/by-region/{region}")
    @Operation(summary = "List reports for a specific region")
    public ResponseEntity<List<ReportDto>> reportsByRegion(@PathVariable String region) {
        List<AnalysisReport> reports = analysisReportRepository.findByRegion(region);
        return ResponseEntity.ok(reports.stream().map(ReportDto::of).toList());
    }

    @GetMapping("/by-trend/{direction}")
    @Operation(summary = "List reports by trend direction")
    public ResponseEntity<List<ReportDto>> reportsByTrend(@PathVariable String direction) {
        List<AnalysisReport> reports = analysisReportRepository.findByTrendDirection(direction.toUpperCase());
        return ResponseEntity.ok(reports.stream().map(ReportDto::of).toList());
    }

    @GetMapping("/high-confidence")
    @Operation(summary = "List reports with high confidence")
    public ResponseEntity<List<ReportDto>> highConfidenceReports(
            @RequestParam(defaultValue = "0.8") double minConfidence) {
        List<AnalysisReport> reports = analysisReportRepository.findByMinConfidence(minConfidence);
        return ResponseEntity.ok(reports.stream().map(ReportDto::of).toList());
    }

    @PostMapping("/{id}/approve")
    @Operation(summary = "Approve a report")
    public ResponseEntity<ReportDto> approveReport(@PathVariable UUID id) {
        AnalysisReport report = analysisReportRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Report not found"));
        report.setStatus("APPROVED");
        report.setApprovedAt(java.time.LocalDateTime.now());
        AnalysisReport saved = analysisReportRepository.save(report);
        log.info("Approved report: {} ({})", report.getReportType(), id);
        return ResponseEntity.ok(ReportDto.of(saved));
    }

    @PostMapping("/{id}/reject")
    @Operation(summary = "Reject a report")
    public ResponseEntity<ReportDto> rejectReport(@PathVariable UUID id) {
        AnalysisReport report = analysisReportRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Report not found"));
        report.setStatus("REJECTED");
        AnalysisReport saved = analysisReportRepository.save(report);
        log.info("Rejected report: {} ({})", report.getReportType(), id);
        return ResponseEntity.ok(ReportDto.of(saved));
    }

    @GetMapping("/statistics")
    @Operation(summary = "Get report statistics")
    public ResponseEntity<Map<String, Object>> statistics() {
        Map<String, Object> stats = new java.util.HashMap<>();
        stats.put("total", analysisReportRepository.count());
        stats.put("completed", analysisReportRepository.countByTypeAndStatus("ANNUAL", "COMPLETED"));
        stats.put("pendingApproval", analysisReportRepository.countByTypeAndStatus("ANNUAL", "DRAFT"));
        return ResponseEntity.ok(stats);
    }
}
