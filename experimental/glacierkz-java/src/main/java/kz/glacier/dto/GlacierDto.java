package kz.glacier.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.UUID;

@Schema(description = "Glacier entity data transfer object")
public record GlacierDto(
        @Schema(description = "Glacier unique identifier") UUID id,
        @Schema(description = "Glacier name", example = "Tien Shan No. 7") String name,
        @Schema(description = "Geographic region", example = "Tien Shan") String region,
        @Schema(description = "Mountain range", example = "Trans-Ili Alatau") String mountainRange,
        @Schema(description = "Geographic latitude") Double latitude,
        @Schema(description = "Geographic longitude") Double longitude,
        @Schema(description = "Elevation above sea level in meters") Double elevation,
        @Schema(description = "Area in square kilometers") Double area,
        @Schema(description = "Current status", example = "ACTIVE") String status,
        @Schema(description = "Classification by area size", example = "MEDIUM") String classification,
        @Schema(description = "Mass balance in meters water equivalent") Double massBalance,
        @Schema(description = "Terminus type", example = "VALLEY") String terminusType,
        @Schema(description = "Snow line altitude in meters") Double snowLineAltitude,
        @Schema(description = "Date of last survey") LocalDate lastSurveyDate,
        @Schema(description = "Creation timestamp") LocalDateTime createdAt,
        @Schema(description = "Last update timestamp") LocalDateTime updatedAt
) {
    public static GlacierDto of(kz.glacier.model.Glacier g) {
        return new GlacierDto(
                g.getId(), g.getName(), g.getRegion(), g.getMountainRange(),
                g.getLatitude(), g.getLongitude(), g.getElevation(),
                g.getAreaSquareKm(), g.getStatus(), g.getClassification(),
                g.getMassBalance(), g.getTerminusType(), g.getSnowLineAltitude(),
                g.getLastSurveyDate(), g.getCreatedAt(), g.getUpdatedAt()
        );
    }
}
