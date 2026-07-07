package kz.glacier.repository;

import kz.glacier.model.AnalysisReport;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

@Repository
public interface AnalysisReportRepository extends JpaRepository<AnalysisReport, UUID> {

    @Query("SELECT a FROM AnalysisReport a WHERE a.glacier.id = :glacierId ORDER BY a.createdAt DESC")
    List<AnalysisReport> findByGlacierId(@Param("glacierId") UUID glacierId);

    @Query("SELECT a FROM AnalysisReport a WHERE a.reportType = :reportType ORDER BY a.createdAt DESC")
    Page<AnalysisReport> findByReportType(@Param("reportType") String reportType, Pageable pageable);

    @Query("SELECT a FROM AnalysisReport a WHERE a.status = :status")
    Page<AnalysisReport> findByStatus(@Param("status") String status, Pageable pageable);

    @Query("SELECT a FROM AnalysisReport a WHERE a.reportDate BETWEEN :from AND :to ORDER BY a.reportDate DESC")
    List<AnalysisReport> findByDateRange(@Param("from") LocalDate from, @Param("to") LocalDate to);

    @Query("SELECT a FROM AnalysisReport a WHERE a.changeDetected = true ORDER BY a.changeMagnitudePercent DESC")
    List<AnalysisReport> findReportsWithChanges();

    @Query("SELECT a FROM AnalysisReport a WHERE a.createdByUserId = :userId ORDER BY a.createdAt DESC")
    List<AnalysisReport> findByCreatedByUserId(@Param("userId") UUID userId);

    @Query("SELECT a FROM AnalysisReport a WHERE a.glacier.id = :glacierId AND a.reportType = :reportType AND a.status = 'COMPLETED' ORDER BY a.reportDate DESC")
    List<AnalysisReport> findCompletedByGlacierAndType(@Param("glacierId") UUID glacierId, @Param("reportType") String reportType);

    @Query("SELECT a FROM AnalysisReport a WHERE a.trendDirection = :direction")
    List<AnalysisReport> findByTrendDirection(@Param("direction") String direction);

    @Query("SELECT a FROM AnalysisReport a WHERE a.confidenceScore >= :minConfidence ORDER BY a.confidenceScore DESC")
    List<AnalysisReport> findByMinConfidence(@Param("minConfidence") double minConfidence);

    @Query("SELECT a FROM AnalysisReport a WHERE a.status = 'DRAFT'")
    Page<AnalysisReport> findDraftReports(Pageable pageable);

    @Query("SELECT a FROM AnalysisReport a WHERE a.approvedByUserId IS NOT NULL ORDER BY a.approvedAt DESC")
    Page<AnalysisReport> findApprovedReports(Pageable pageable);

    @Query("SELECT a FROM AnalysisReport a WHERE a.periodStart >= :periodStart AND a.periodEnd <= :periodEnd")
    List<AnalysisReport> findByPeriodRange(@Param("periodStart") LocalDate periodStart, @Param("periodEnd") LocalDate periodEnd);

    @Query("SELECT a FROM AnalysisReport a WHERE a.glacier.region = :region ORDER BY a.createdAt DESC")
    List<AnalysisReport> findByRegion(@Param("region") String region);

    @Query("SELECT COUNT(a) FROM AnalysisReport a WHERE a.reportType = :reportType AND a.status = :status")
    long countByTypeAndStatus(@Param("reportType") String reportType, @Param("status") String status);
}
