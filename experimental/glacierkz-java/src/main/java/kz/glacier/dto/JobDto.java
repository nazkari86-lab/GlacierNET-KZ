package kz.glacier.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;
import java.util.UUID;

@Schema(description = "Raster processing job data transfer object")
public record JobDto(
        @Schema(description = "Job unique identifier") UUID id,
        @Schema(description = "Glacier ID") UUID glacierId,
        @Schema(description = "Glacier name") String glacierName,
        @Schema(description = "Job type", example = "NDVI") String jobType,
        @Schema(description = "Current job status", example = "RUNNING") String status,
        @Schema(description = "Job priority (1=highest)") Integer priority,
        @Schema(description = "Batch execution ID") Long batchExecutionId,
        @Schema(description = "Error message if failed") String errorMessage,
        @Schema(description = "Total processing steps") Integer totalSteps,
        @Schema(description = "Completed processing steps") Integer completedSteps,
        @Schema(description = "Retry count") Integer retryCount,
        @Schema(description = "Maximum retries allowed") Integer maxRetries,
        @Schema(description = "Who created the job") String createdBy,
        @Schema(description = "Job creation time") Instant createdAt,
        @Schema(description = "When processing started") Instant startedAt,
        @Schema(description = "When processing completed") Instant completedAt,
        @Schema(description = "Duration in milliseconds") Long durationMs
) {
    public static JobDto of(kz.glacier.model.RasterJob r) {
        return new JobDto(
                r.getId(), r.getGlacier() != null ? r.getGlacier().getId() : null,
                r.getGlacier() != null ? r.getGlacier().getName() : null,
                r.getJobType(), r.getStatus(), r.getPriority(),
                r.getBatchExecutionId(), r.getErrorMessage(),
                r.getTotalSteps(), r.getCompletedSteps(),
                r.getRetryCount(), r.getMaxRetries(),
                r.getCreatedBy(), r.getCreatedAt(), r.getStartedAt(),
                r.getCompletedAt(), r.getDurationMs()
        );
    }
}
