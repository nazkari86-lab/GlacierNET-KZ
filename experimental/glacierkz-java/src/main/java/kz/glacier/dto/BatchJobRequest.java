package kz.glacier.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;
import java.util.UUID;

@Schema(description = "Batch job submission request")
public record BatchJobRequest(
        @Schema(description = "List of glacier IDs to process") List<UUID> glacierIds,
        @Schema(description = "Processing job type", required = true) String jobType,
        @Schema(description = "Processing priority", example = "5") Integer priority,
        @Schema(description = "Number of parallel workers", example = "4") Integer parallelism,
        @Schema(description = "Output format", example = "GEOTIFF") String outputFormat,
        @Schema(description = "Target CRS", example = "EPSG:4326") String targetCrs,
        @Schema(description = "Max cloud cover percent") Double maxCloudCover,
        @Schema(description = "Date range start", example = "2024-01-01") String dateRangeStart,
        @Schema(description = "Date range end", example = "2024-12-31") String dateRangeEnd,
        @Schema(description = "Chunk size for processing") Integer chunkSize,
        @Schema(description = "Skip failed items and continue") Boolean continueOnFailure,
        @Schema(description = "Notification email on completion") String notifyEmail,
        @Schema(description = "Description for the batch job") String description,
        @Schema(description = "Tags for categorization") List<String> tags
) {
    public static BatchJobRequest defaultRequest(List<UUID> glacierIds, String jobType) {
        return new BatchJobRequest(glacierIds, jobType, 5, 4, "GEOTIFF", "EPSG:4326",
                30.0, null, null, 100, true, null, "Auto-generated batch job", List.of());
    }
}
