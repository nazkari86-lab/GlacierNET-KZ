package kz.glacier.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDate;
import java.util.UUID;

@Schema(description = "Analysis request payload")
public record AnalysisRequest(
        @Schema(description = "Glacier ID to analyze") UUID glacierId,
        @Schema(description = "Type of analysis", required = true) AnalysisType analysisType,
        @Schema(description = "Analysis period start date") LocalDate periodStart,
        @Schema(description = "Analysis period end date") LocalDate periodEnd,
        @Schema(description = "Cloud cover threshold percent") Double maxCloudCover,
        @Schema(description = "Target spatial resolution in meters") Double targetResolution,
        @Schema(description = "Processing priority (1=highest)", example = "5") Integer priority,
        @Schema(description = "Output format", example = "GEOTIFF") String outputFormat,
        @Schema(description = "Target CRS", example = "EPSG:4326") String targetCrs,
        @Schema(description = "Additional parameters") java.util.Map<String, String> parameters,
        @Schema(description = "Callback webhook URL") String callbackUrl
) {
    @Schema(description = "Supported analysis types")
    public enum AnalysisType {
        NDVI, NDWI, SNOW_COVER, GLACIER_CHANGE, SURFACE_VELOCITY,
        ELA_DETECTION, MASS_BALANCE, THICKNESS_CHANGE, ALL
    }
}
