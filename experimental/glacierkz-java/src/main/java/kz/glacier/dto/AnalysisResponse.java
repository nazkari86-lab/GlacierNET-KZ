package kz.glacier.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;
import java.util.UUID;

@Schema(description = "Analysis response with processing status")
public record AnalysisResponse(
        @Schema(description = "Generated job ID") UUID jobId,
        @Schema(description = "Glacier ID being analyzed") UUID glacierId,
        @Schema(description = "Analysis type requested") String analysisType,
        @Schema(description = "Current processing status", example = "RUNNING") String status,
        @Schema(description = "Progress percentage (0-100)") Double progressPercent,
        @Schema(description = "Processing result summary") String resultSummary,
        @Schema(description = "Output file path if completed") String outputPath,
        @Schema(description = "Output file format") String outputFormat,
        @Schema(description = "Output CRS") String outputCrs,
        @Schema(description = "Processing start time") Instant startedAt,
        @Schema(description = "Processing end time") Instant completedAt,
        @Schema(description = "Processing duration in ms") Long durationMs,
        @Schema(description = "Error message if failed") String errorMessage,
        @Schema(description = "Request correlation ID") String correlationId,
        @Schema(description = "Estimated completion time") Instant estimatedCompletion
) {
    public static AnalysisResponse pending(UUID jobId, UUID glacierId, String analysisType, String correlationId) {
        return new AnalysisResponse(jobId, glacierId, analysisType, "PENDING", 0.0, null, null, null, null,
                null, null, null, null, correlationId, null);
    }

    public static AnalysisResponse running(UUID jobId, UUID glacierId, String analysisType, double progress, Instant startedAt) {
        return new AnalysisResponse(jobId, glacierId, analysisType, "RUNNING", progress, null, null, null, null,
                startedAt, null, null, null, null, null);
    }

    public static AnalysisResponse completed(UUID jobId, UUID glacierId, String analysisType, String outputPath,
                                             String outputFormat, Instant startedAt, Instant completedAt, long durationMs) {
        return new AnalysisResponse(jobId, glacierId, analysisType, "COMPLETED", 100.0, "Analysis completed successfully",
                outputPath, outputFormat, "EPSG:4326", startedAt, completedAt, durationMs, null, null, null);
    }

    public static AnalysisResponse failed(UUID jobId, UUID glacierId, String analysisType, String error) {
        return new AnalysisResponse(jobId, glacierId, analysisType, "FAILED", null, null, null, null, null,
                null, null, null, error, null, null);
    }
}
