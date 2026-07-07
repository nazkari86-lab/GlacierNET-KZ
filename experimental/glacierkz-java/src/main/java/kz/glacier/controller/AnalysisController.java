package kz.glacier.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import kz.glacier.dto.AnalysisRequest;
import kz.glacier.dto.AnalysisResponse;
import kz.glacier.model.RasterJob;
import kz.glacier.repository.GlacierRepository;
import kz.glacier.repository.RasterJobRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import jakarta.validation.Valid;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

@RestController
@RequestMapping("/api/v1/analysis")
@RequiredArgsConstructor
@Slf4j
@Tag(name = "Analysis", description = "Glacier analysis operations")
public class AnalysisController {

    private final RasterJobRepository rasterJobRepository;
    private final GlacierRepository glacierRepository;
    private final KafkaTemplate<String, Object> kafkaTemplate;

    @PostMapping
    @Operation(summary = "Submit a new analysis request")
    public ResponseEntity<AnalysisResponse> submitAnalysis(@RequestBody @Valid AnalysisRequest request) {
        if (!glacierRepository.existsById(request.glacierId())) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Glacier not found");
        }

        RasterJob job = new RasterJob();
        job.setGlacier(glacierRepository.getReferenceById(request.glacierId()));
        job.setJobType(request.analysisType().name());
        job.setStatus("PENDING");
        job.setPriority(request.priority() != null ? request.priority() : 5);
        job.setMaxRetries(3);
        job.setRetryCount(0);
        job.setCreatedBy("api-user");
        job.setTotalSteps(1);
        job.setCompletedSteps(0);

        RasterJob saved = rasterJobRepository.save(job);

        String correlationId = UUID.randomUUID().toString();
        try {
            kafkaTemplate.send("glacier.task.events", saved.getId().toString(),
                    Map.of("jobId", saved.getId(), "type", request.analysisType().name(),
                            "correlationId", correlationId));
        } catch (Exception e) {
            log.warn("Failed to send Kafka message for job {}: {}", saved.getId(), e.getMessage());
        }

        log.info("Submitted analysis: type={} glacier={} jobId={}", request.analysisType(), request.glacierId(), saved.getId());
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(
                AnalysisResponse.pending(saved.getId(), request.glacierId(), request.analysisType().name(), correlationId));
    }

    @GetMapping("/{jobId}")
    @Operation(summary = "Get analysis status")
    public ResponseEntity<AnalysisResponse> getAnalysisStatus(@PathVariable UUID jobId) {
        RasterJob job = rasterJobRepository.findById(jobId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Analysis job not found"));

        double progress = job.getTotalSteps() != null && job.getTotalSteps() > 0
                ? (double) job.getCompletedSteps() / job.getTotalSteps() * 100.0
                : 0.0;

        return ResponseEntity.ok(new AnalysisResponse(
                job.getId(),
                job.getGlacier() != null ? job.getGlacier().getId() : null,
                job.getJobType(),
                job.getStatus(),
                progress,
                job.getErrorMessage(),
                null, null, null,
                job.getStartedAt(), job.getCompletedAt(), job.getDurationMs(),
                job.getErrorMessage(), null, null
        ));
    }

    @PostMapping("/batch")
    @Operation(summary = "Submit batch analysis for multiple glaciers")
    public ResponseEntity<Map<String, Object>> submitBatchAnalysis(@RequestBody @Valid AnalysisRequest request) {
        if (!glacierRepository.existsById(request.glacierId())) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Glacier not found");
        }

        RasterJob job = new RasterJob();
        job.setGlacier(glacierRepository.getReferenceById(request.glacierId()));
        job.setJobType(request.analysisType().name());
        job.setStatus("PENDING");
        job.setPriority(request.priority() != null ? request.priority() : 5);
        job.setMaxRetries(3);
        job.setRetryCount(0);
        job.setCreatedBy("api-user");
        job.setTotalSteps(1);
        job.setCompletedSteps(0);

        RasterJob saved = rasterJobRepository.save(job);

        return ResponseEntity.status(HttpStatus.ACCEPTED).body(Map.of(
                "jobId", saved.getId(), "status", "PENDING",
                "message", "Batch analysis submitted successfully"
        ));
    }

    @PostMapping("/{jobId}/cancel")
    @Operation(summary = "Cancel a running analysis")
    public ResponseEntity<Void> cancelAnalysis(@PathVariable UUID jobId) {
        RasterJob job = rasterJobRepository.findById(jobId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Analysis job not found"));

        if (!"PENDING".equals(job.getStatus()) && !"RUNNING".equals(job.getStatus())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Job cannot be cancelled in state: " + job.getStatus());
        }

        job.setStatus("CANCELLED");
        job.setErrorMessage("Cancelled via API");
        rasterJobRepository.save(job);

        log.info("Cancelled analysis: jobId={}", jobId);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/types")
    @Operation(summary = "List supported analysis types")
    public ResponseEntity<Map<String, Object>> listAnalysisTypes() {
        Map<String, Object> types = new java.util.HashMap<>();
        types.put("types", java.util.List.of(
                Map.of("name", "NDVI", "description", "Normalized Difference Vegetation Index"),
                Map.of("name", "NDWI", "description", "Normalized Difference Water Index"),
                Map.of("name", "SNOW_COVER", "description", "Snow cover extent analysis"),
                Map.of("name", "GLACIER_CHANGE", "description", "Glacier boundary change detection"),
                Map.of("name", "SURFACE_VELOCITY", "description", "Glacier surface velocity"),
                Map.of("name", "ELA_DETECTION", "description", "Equilibrium line altitude detection"),
                Map.of("name", "MASS_BALANCE", "description", "Mass balance estimation"),
                Map.of("name", "THICKNESS_CHANGE", "description", "Ice thickness change")
        ));
        return ResponseEntity.ok(types);
    }
}
