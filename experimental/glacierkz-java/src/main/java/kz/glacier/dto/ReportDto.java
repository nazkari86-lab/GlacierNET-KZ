package kz.glacier.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.UUID;

@Schema(description = "Analysis report data transfer object")
public record ReportDto(
        @Schema(description = "Report unique identifier") UUID id,
        @Schema(description = "Glacier ID") UUID glacierId,
        @Schema(description = "Glacier name") String glacierName,
        @Schema(description = "Report type", example = "ANNUAL") String reportType,
        @Schema(description = "Current status", example = "COMPLETED") String status,
        @Schema(description = "Report date") LocalDate reportDate,
        @Schema(description = "Analysis period start") LocalDate periodStart,
        @Schema(description = "Analysis period end") LocalDate periodEnd,
        @Schema(description = "Change detected") Boolean changeDetected,
        @Schema(description = "Change magnitude percent") Double changeMagnitudePercent,
        @Schema(description = "Trend direction", example = "DECLINING") String trendDirection,
        @Schema(description = "Confidence score (0-1)") Double confidenceScore,
        @Schema(description = "Summary text") String summary,
        @Schema(description = "Generated file path") String outputPath,
        @Schema(description = "Report author user ID") UUID createdByUserId,
        @Schema(description = "Approved by user ID") UUID approvedByUserId,
        @Schema(description = "Approval timestamp") LocalDateTime approvedAt,
        @Schema(description = "Creation timestamp") LocalDateTime createdAt
) {
    public static ReportDto of(kz.glacier.model.AnalysisReport r) {
        return new ReportDto(
                r.getId(), r.getGlacier() != null ? r.getGlacier().getId() : null,
                r.getGlacier() != null ? r.getGlacier().getName() : null,
                r.getReportType(), r.getStatus(), r.getReportDate(),
                r.getPeriodStart(), r.getPeriodEnd(), r.isChangeDetected(),
                r.getChangeMagnitudePercent(), r.getTrendDirection(), r.getConfidenceScore(),
                r.getSummary(), r.getOutputPath(), r.getCreatedByUserId(),
                r.getApprovedByUserId(), r.getApprovedAt(), r.getCreatedAt()
        );
    }
}
