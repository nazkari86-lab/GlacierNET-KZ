package kz.glacier.batch;

import kz.glacier.model.SatelliteImage;
import kz.glacier.model.RasterJob;
import kz.glacier.repository.SatelliteImageRepository;
import kz.glacier.repository.RasterJobRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.batch.item.ItemProcessor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Optional;
import java.util.UUID;

@Component
public class RasterItemProcessor implements ItemProcessor<SatelliteImage, RasterJob> {
    
    private static final Logger log = LoggerFactory.getLogger(RasterItemProcessor.class);
    
    @Autowired
    private SatelliteImageRepository satelliteImageRepository;
    
    @Autowired
    private RasterJobRepository rasterJobRepository;
    
    @Override
    @Transactional
    public RasterJob process(SatelliteImage item) throws Exception {
        log.info("Processing satellite image: {}", item.getId());
        
        // Validate the satellite image
        if (item == null || item.getId() == null) {
            log.warn("Null or invalid satellite image received");
            return null;
        }
        
        // Check if image already processed
        if (item.getStatus() != null && item.getStatus().equals("COMPLETED")) {
            log.info("Image {} already completed, skipping", item.getId());
            return null;
        }
        
        // Check for duplicate checksum
        if (item.getChecksum() != null) {
            Optional<SatelliteImage> existing = satelliteImageRepository
                .findByChecksum(item.getChecksum());
            if (existing.isPresent() && !existing.get().getId().equals(item.getId())) {
                log.warn("Duplicate checksum detected for image {}, skipping", item.getId());
                return null;
            }
        }
        
        try {
            // Create corresponding RasterJob
            RasterJob job = new RasterJob();
            job.setId(UUID.randomUUID());
            job.setGlacierId(item.getGlacierId());
            job.setRasterPath(item.getFilePath());
            job.setOriginalPath(item.getFilePath());
            job.setStatus("PENDING");
            job.setPriority(item.getCloudCover() != null ? 
                calculatePriority(item.getCloudCover()) : 5);
            job.setParameters(createProcessingParameters(item));
            job.setCreatedAt(LocalDateTime.now());
            job.setUpdatedAt(LocalDateTime.now());
            job.setCreatedBy("batch-processor");
            job.setRetryCount(0);
            job.setMaxRetries(3);
            
            // Update satellite image status
            item.setStatus("QUEUED");
            item.setUpdatedAt(LocalDateTime.now());
            satelliteImageRepository.save(item);
            
            // Save and return the job
            RasterJob savedJob = rasterJobRepository.save(job);
            log.info("Created RasterJob {} for satellite image {}", 
                savedJob.getId(), item.getId());
            
            return savedJob;
            
        } catch (Exception e) {
            log.error("Failed to process satellite image {}: {}", 
                item.getId(), e.getMessage(), e);
            
            // Mark image as failed
            item.setStatus("FAILED");
            item.setErrorMessage(e.getMessage());
            item.setUpdatedAt(LocalDateTime.now());
            satelliteImageRepository.save(item);
            
            return null;
        }
    }
    
    private int calculatePriority(Integer cloudCover) {
        // Lower cloud cover = higher priority
        if (cloudCover == null) return 5;
        if (cloudCover < 10) return 1;
        if (cloudCover < 30) return 2;
        if (cloudCover < 50) return 3;
        if (cloudCover < 70) return 4;
        return 5;
    }
    
    private String createProcessingParameters(SatelliteImage item) {
        StringBuilder params = new StringBuilder();
        params.append("{");
        params.append("\"satellite\": \"").append(item.getSatellite() != null ? 
            item.getSatellite() : "UNKNOWN").append("\", ");
        params.append("\"resolution\": ").append(item.getResolution() != null ? 
            item.getResolution() : 10).append(", ");
        params.append("\"bands\": [\"B02\", \"B03\", \"B04\", \"B08\"], ");
        params.append("\"processing_level\": \"L2A\", ");
        params.append("\"cloud_masking\": true, ");
        params.append("\"atmospheric_correction\": true");
        params.append("}");
        return params.toString();
    }
}