package kz.glacier.service;

import kz.glacier.model.AnalysisReport;
import kz.glacier.model.Glacier;
import kz.glacier.repository.AnalysisReportRepository;
import kz.glacier.repository.GlacierRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class ReportService {

    private final AnalysisReportRepository analysisReportRepository;
    private final GlacierRepository glacierRepository;
    private final NotificationService notificationService;

    @Transactional(readOnly = true)
    public Page<AnalysisReport> listReports(Pageable pageable) {
        return analysisReportRepository.findAll(pageable);
    }

    @Transactional(readOnly = true)
    public AnalysisReport findById(UUID id) {
        return analysisReportRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Report not found: " + id));
    }

    @Transactional(readOnly = true)
    public List<AnalysisReport> findByGlacierId(UUID glacierId) {
        return analysisReportRepository.findByGlacierId(glacierId);
    }

    @Transactional(readOnly = true)
    public List<AnalysisReport> findByReportType(String reportType) {
        return analysisReportRepository.findByReportType(reportType, Pageable.unpaged()).getContent();
    }

    @Transactional(readOnly = true)
    public List<AnalysisReport> findReportsWithChanges() {
        return analysisReportRepository.findReportsWithChanges();
    }

    @Transactional(readOnly = true)
    public List<AnalysisReport> findByDateRange(LocalDate from, LocalDate to) {
        return analysisReportRepository.findByDateRange(from, to);
    }

    @Transactional(readOnly = true)
    public List<AnalysisReport> findByRegion(String region) {
        return analysisReportRepository.findByRegion(region);
    }

    @Transactional(readOnly = true)
    public List<AnalysisReport> findHighConfidence(double minConfidence) {
        return analysisReportRepository.findByMinConfidence(minConfidence);
    }

    @Transactional
    public AnalysisReport createReport(UUID glacierId, String reportType, LocalDate periodStart, LocalDate periodEnd) {
        Glacier glacier = glacierRepository.findById(glacierId)
                .orElseThrow(() -> new RuntimeException("Glacier not found: " + glacierId));

        AnalysisReport report = new AnalysisReport();
        report.setGlacier(glacier);
        report.setReportType(reportType);
        report.setStatus("DRAFT");
        report.setReportDate(LocalDate.now());
        report.setPeriodStart(periodStart);
        report.setPeriodEnd(periodEnd);
        report.setChangeDetected(false);
        report.setChangeMagnitudePercent(0.0);
        report.setTrendDirection("STABLE");
        report.setConfidenceScore(0.0);

        AnalysisReport saved = analysisReportRepository.save(report);
        log.info("Created report: type={} glacier={} id={}", reportType, glacierId, saved.getId());
        return saved;
    }

    @Transactional
    public AnalysisReport approveReport(UUID reportId, UUID approverUserId) {
        AnalysisReport report = findById(reportId);
        report.setStatus("APPROVED");
        report.setApprovedByUserId(approverUserId);
        report.setApprovedAt(java.time.LocalDateTime.now());
        AnalysisReport saved = analysisReportRepository.save(report);
        log.info("Approved report: {} by user {}", reportId, approverUserId);
        return saved;
    }

    @Transactional
    public AnalysisReport rejectReport(UUID reportId) {
        AnalysisReport report = findById(reportId);
        report.setStatus("REJECTED");
        AnalysisReport saved = analysisReportRepository.save(report);
        log.info("Rejected report: {}", reportId);
        return saved;
    }

    @Transactional
    public AnalysisReport submitForReview(UUID reportId) {
        AnalysisReport report = findById(reportId);
        report.setStatus("PENDING_REVIEW");
        AnalysisReport saved = analysisReportRepository.save(report);
        log.info("Submitted report for review: {}", reportId);
        return saved;
    }

    @Transactional(readOnly = true)
    public List<AnalysisReport> findByTrendDirection(String direction) {
        return analysisReportRepository.findByTrendDirection(direction.toUpperCase());
    }

    @Transactional(readOnly = true)
    public List<AnalysisReport> findByCreatedByUserId(UUID userId) {
        return analysisReportRepository.findByCreatedByUserId(userId);
    }

    @Transactional
    public void updateReportSummary(UUID reportId, String summary, Double confidenceScore, boolean changeDetected,
                                    Double changeMagnitudePercent, String trendDirection) {
        AnalysisReport report = findById(reportId);
        report.setSummary(summary);
        report.setConfidenceScore(confidenceScore);
        report.setChangeDetected(changeDetected);
        report.setChangeMagnitudePercent(changeMagnitudePercent);
        report.setTrendDirection(trendDirection);
        analysisReportRepository.save(report);
        log.info("Updated report summary: {}", reportId);
    }

    @Transactional(readOnly = true)
    public long countByTypeAndStatus(String reportType, String status) {
        return analysisReportRepository.countByTypeAndStatus(reportType, status);
    }
}
