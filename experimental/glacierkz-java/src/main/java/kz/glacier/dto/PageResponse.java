package kz.glacier.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

@Schema(description = "Generic paginated response wrapper")
public record PageResponse<T>(
        @Schema(description = "List of items") List<T> content,
        @Schema(description = "Total number of items") long totalElements,
        @Schema(description = "Total number of pages") int totalPages,
        @Schema(description = "Current page number (0-based)") int pageNumber,
        @Schema(description = "Page size") int pageSize,
        @Schema(description = "Is this the first page") boolean first,
        @Schema(description = "Is this the last page") boolean last,
        @Schema(description = "Is this page empty") boolean empty
) {
    public static <T> PageResponse<T> of(org.springframework.data.domain.Page<T> page) {
        return new PageResponse<>(
                page.getContent(), page.getTotalElements(), page.getTotalPages(),
                page.getNumber(), page.getSize(), page.isFirst(), page.isLast(), page.isEmpty()
        );
    }

    public static <T> PageResponse<T> empty(int pageSize) {
        return new PageResponse<>(List.of(), 0, 0, 0, pageSize, true, true, true);
    }
}
