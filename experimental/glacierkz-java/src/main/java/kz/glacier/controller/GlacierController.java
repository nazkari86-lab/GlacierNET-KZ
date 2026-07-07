package kz.glacier.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import kz.glacier.dto.GlacierDto;
import kz.glacier.dto.PageResponse;
import kz.glacier.model.Glacier;
import kz.glacier.repository.GlacierRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/glaciers")
@RequiredArgsConstructor
@Slf4j
@Tag(name = "Glacier", description = "Glacier catalog management operations")
public class GlacierController {

    private final GlacierRepository glacierRepository;

    @GetMapping
    @Operation(summary = "List glaciers with filtering and pagination")
    public ResponseEntity<PageResponse<GlacierDto>> listGlaciers(
            @RequestParam(required = false) String region,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String mountainRange,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(defaultValue = "name") String sortBy,
            @RequestParam(defaultValue = "ASC") String sortDir) {

        Sort sort = Sort.by(Sort.Direction.fromString(sortDir), sortBy);
        PageRequest pageable = PageRequest.of(page, size, sort);
        Page<Glacier> glaciers;

        if (name != null && !name.isBlank()) {
            glaciers = glacierRepository.findByNameContaining(name, pageable);
        } else if (region != null && !region.isBlank()) {
            glaciers = glacierRepository.findByRegion(region, pageable);
        } else if (status != null && !status.isBlank()) {
            glaciers = glacierRepository.findByStatus(status, pageable);
        } else {
            glaciers = glacierRepository.findAll(pageable);
        }

        log.info("Listed {} glaciers (page {}/{})", glaciers.getContent().size(), page + 1, glaciers.getTotalPages());
        return ResponseEntity.ok(PageResponse.of(glaciers.map(GlacierDto::of)));
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get glacier by ID")
    public ResponseEntity<GlacierDto> getGlacier(@PathVariable UUID id) {
        Glacier glacier = glacierRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Glacier not found"));
        return ResponseEntity.ok(GlacierDto.of(glacier));
    }

    @GetMapping("/search")
    @Operation(summary = "Search glaciers by name")
    public ResponseEntity<PageResponse<GlacierDto>> searchGlaciers(
            @RequestParam @NotBlank String q,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Page<Glacier> results = glacierRepository.findByNameContaining(q, PageRequest.of(page, size, Sort.by("name")));
        return ResponseEntity.ok(PageResponse.of(results.map(GlacierDto::of)));
    }

    @GetMapping("/regions")
    @Operation(summary = "List distinct regions")
    public ResponseEntity<List<String>> listRegions() {
        return ResponseEntity.ok(glacierRepository.findDistinctRegions());
    }

    @GetMapping("/mountain-ranges")
    @Operation(summary = "List distinct mountain ranges")
    public ResponseEntity<List<String>> listMountainRanges() {
        return ResponseEntity.ok(glacierRepository.findDistinctMountainRanges());
    }

    @GetMapping("/statistics")
    @Operation(summary = "Get glacier statistics")
    public ResponseEntity<java.util.Map<String, Object>> getStatistics() {
        java.util.Map<String, Object> stats = new java.util.HashMap<>();
        stats.put("totalActive", glacierRepository.countActive());
        glacierRepository.findLargestGlacier().ifPresent(g -> stats.put("largest", GlacierDto.of(g)));
        return ResponseEntity.ok(stats);
    }

    @PostMapping
    @Operation(summary = "Create a new glacier")
    public ResponseEntity<GlacierDto> createGlacier(@RequestBody @Valid GlacierDto dto) {
        Glacier glacier = new Glacier();
        glacier.setName(dto.name());
        glacier.setRegion(dto.region());
        glacier.setMountainRange(dto.mountainRange());
        glacier.setLatitude(dto.latitude());
        glacier.setLongitude(dto.longitude());
        glacier.setElevation(dto.elevation());
        glacier.setAreaSquareKm(dto.area());
        glacier.setStatus(dto.status() != null ? dto.status() : "ACTIVE");
        glacier.setClassification(dto.classification());
        glacier.setMassBalance(dto.massBalance());
        glacier.setTerminusType(dto.terminusType());
        glacier.setSnowLineAltitude(dto.snowLineAltitude());
        glacier.setLastSurveyDate(dto.lastSurveyDate());
        glacier.setDeleted(false);

        Glacier saved = glacierRepository.save(glacier);
        log.info("Created glacier: {} ({})", saved.getName(), saved.getId());
        return ResponseEntity.status(HttpStatus.CREATED).body(GlacierDto.of(saved));
    }

    @PutMapping("/{id}")
    @Operation(summary = "Update an existing glacier")
    public ResponseEntity<GlacierDto> updateGlacier(@PathVariable UUID id, @RequestBody @Valid GlacierDto dto) {
        Glacier glacier = glacierRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Glacier not found"));

        glacier.setName(dto.name());
        glacier.setRegion(dto.region());
        glacier.setMountainRange(dto.mountainRange());
        glacier.setLatitude(dto.latitude());
        glacier.setLongitude(dto.longitude());
        glacier.setElevation(dto.elevation());
        glacier.setAreaSquareKm(dto.area());
        if (dto.status() != null) glacier.setStatus(dto.status());
        glacier.setClassification(dto.classification());
        glacier.setMassBalance(dto.massBalance());
        glacier.setTerminusType(dto.terminusType());
        glacier.setSnowLineAltitude(dto.snowLineAltitude());
        if (dto.lastSurveyDate() != null) glacier.setLastSurveyDate(dto.lastSurveyDate());

        Glacier saved = glacierRepository.save(glacier);
        log.info("Updated glacier: {} ({})", saved.getName(), saved.getId());
        return ResponseEntity.ok(GlacierDto.of(saved));
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Soft delete a glacier")
    public ResponseEntity<Void> deleteGlacier(@PathVariable UUID id) {
        Glacier glacier = glacierRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Glacier not found"));
        glacier.setDeleted(true);
        glacierRepository.save(glacier);
        log.info("Soft-deleted glacier: {} ({})", glacier.getName(), id);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/nearest")
    @Operation(summary = "Find glaciers nearest to a point")
    public ResponseEntity<List<GlacierDto>> findNearest(
            @RequestParam double latitude,
            @RequestParam double longitude,
            @RequestParam(defaultValue = "5") int limit) {
        String wkt = String.format("POINT(%f %f)", longitude, latitude);
        List<Glacier> nearest = glacierRepository.findNearest(wkt, limit);
        return ResponseEntity.ok(nearest.stream().map(GlacierDto::of).toList());
    }

    @GetMapping("/bbox")
    @Operation(summary = "Find glaciers within a bounding box")
    public ResponseEntity<List<GlacierDto>> findByBoundingBox(
            @RequestParam double minLon, @RequestParam double minLat,
            @RequestParam double maxLon, @RequestParam double maxLat) {
        List<Glacier> found = glacierRepository.findInBoundingBox(minLon, minLat, maxLon, maxLat);
        return ResponseEntity.ok(found.stream().map(GlacierDto::of).toList());
    }

    @GetMapping("/retreating")
    @Operation(summary = "List glaciers with negative mass balance (retreating)")
    public ResponseEntity<PageResponse<GlacierDto>> retreatingGlaciers(
            @RequestParam(defaultValue = "0") int page, @RequestParam(defaultValue = "20") int size) {
        Page<Glacier> retreating = glacierRepository.findRetreatingGlaciers(PageRequest.of(page, size));
        return ResponseEntity.ok(PageResponse.of(retreating.map(GlacierDto::of)));
    }

    @GetMapping("/elevation-range")
    @Operation(summary = "Find glaciers within elevation range")
    public ResponseEntity<List<GlacierDto>> byElevationRange(
            @RequestParam double min, @RequestParam double max) {
        List<Glacier> found = glacierRepository.findByElevationRange(min, max);
        return ResponseEntity.ok(found.stream().map(GlacierDto::of).toList());
    }
}
