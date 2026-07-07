package kz.glacier.batch;

import kz.glacier.model.SatelliteImage;
import kz.glacier.repository.SatelliteImageRepository;
import kz.glacier.service.AuditService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.batch.item.ItemProcessor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Optional;
import java.util.UUID;

@Component
public class SatelliteImageProcessor implements ItemProcessor<SatelliteImage, SatelliteImage> {
    
    private static final Logger log = LoggerFactory.getLogger(SatelliteImageProcessor.class);
    private static final DateTimeFormatter DATE_FORMATTER = 
        DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    
    @Autowired
    private SatelliteImageRepository satelliteImageRepository;
    
    @Autowired
    private AuditService auditService;
    
    @Override
    @Transactional
    public SatelliteImage process(SatelliteImage item) throws Exception {
        log.info("Processing satellite image metadata: {}", item.getId());
        
        if (item == null || item.getId() == null) {
            log.warn("Null or invalid satellite image received");
            return null;
        }
        
        try {
            // Validate image metadata
            if (!validateMetadata(item)) {
                log.warn("Invalid metadata for image {}", item.getId());
                markAsFailed(item, "Invalid metadata");
                return null;
            }
            
            // Check for duplicate checksum
            if (item.getChecksum() != null) {
                Optional<SatelliteImage> existing = satelliteImageRepository
                    .findByChecksum(item.getChecksum());
                if (existing.isPresent() && !existing.get().getId().equals(item.getId())) {
                    log.info("Duplicate image detected, marking as duplicate");
                    item.setStatus("DUPLICATE");
                    item.setUpdatedAt(LocalDateTime.now());
                    return satelliteImageRepository.save(item);
                }
            }
            
            // Validate cloud cover
            if (item.getCloudCover() != null && item.getCloudCover() > 100) {
                log.warn("Invalid cloud cover: {}%", item.getCloudCover());
                item.setCloudCover(100.0);
            }
            
            // Validate resolution
            if (item.getResolution() != null && item.getResolution() <= 0) {
                log.warn("Invalid resolution: {}", item.getResolution());
                item.setResolution(10.0);
            }
            
            // Process based on satellite type
            SatelliteImage processed = processBySatellite(item);
            
            if (processed != null) {
                processed.setStatus("PROCESSED");
                processed.setUpdatedAt(LocalDateTime.now());
                
                // Log processing in audit
                auditService.logAsync(
                    "satellite_image",
                    item.getId().toString(),
                    "PROCESS",
                    String.format("Processed satellite image from %s with %.1f%% cloud cover",
                        item.getSatellite(), 
                        item.getCloudCover() != null ? item.getCloudCover() : 0.0)
                );
                
                return satelliteImageRepository.save(processed);
            }
            
            return null;
            
        } catch (Exception e) {
            log.error("Failed to process satellite image {}: {}", 
                item.getId(), e.getMessage(), e);
            markAsFailed(item, e.getMessage());
            return null;
        }
    }
    
    private boolean validateMetadata(SatelliteImage item) {
        // Validate required fields
        if (item.getFilePath() == null || item.getFilePath().isEmpty()) {
            log.warn("Missing file path");
            return false;
        }
        
        if (item.getSatellite() == null || item.getSatellite().isEmpty()) {
            log.warn("Missing satellite identifier");
            return false;
        }
        
        // Validate file path format
        if (!item.getFilePath().matches(".*\\.(tif|tiff|jp2|img)$")) {
            log.warn("Invalid file format: {}", item.getFilePath());
            return false;
        }
        
        // Validate acquisition date
        if (item.getAcquisitionDate() != null) {
            if (item.getAcquisitionDate().isAfter(LocalDateTime.now())) {
                log.warn("Future acquisition date: {}", item.getAcquisitionDate());
                return false;
            }
        }
        
        return true;
    }
    
    private SatelliteImage processBySatellite(SatelliteImage item) {
        String satellite = item.getSatellite().toUpperCase();
        
        switch (satellite) {
            case "SENTINEL-2":
            case "SENTINEL2":
                return processSentinel2(item);
            case "LANDSAT-8":
            case "LANDSAT8":
                return processLandsat8(item);
            case "LANDSAT-9":
            case "LANDSAT9":
                return processLandsat9(item);
            case "MODIS":
                return processModis(item);
            case "ALOS":
                return processAlos(item);
            default:
                log.warn("Unknown satellite type: {}", satellite);
                return processGeneric(item);
        }
    }
    
    private SatelliteImage processSentinel2(SatelliteImage item) {
        log.debug("Processing Sentinel-2 image");
        
        // Sentinel-2 specific processing
        if (item.getResolution() == null) {
            item.setResolution(10.0); // Default 10m resolution
        }
        
        // Validate Sentinel-2 specific metadata
        if (item.getFilePath().contains("MSI")) {
            log.debug("Multispectral image detected");
        }
        
        return item;
    }
    
    private SatelliteImage processLandsat8(SatelliteImage item) {
        log.debug("Processing Landsat-8 image");
        
        if (item.getResolution() == null) {
            item.setResolution(30.0); // Default 30m resolution
        }
        
        return item;
    }
    
    private SatelliteImage processLandsat9(SatelliteImage item) {
        log.debug("Processing Landsat-9 image");
        
        if (item.getResolution() == null) {
            item.setResolution(30.0);
        }
        
        return item;
    }
    
    private SatelliteImage processModis(SatelliteImage item) {
        log.debug("Processing MODIS image");
        
        if (item.getResolution() == null) {
            item.setResolution(250.0); // 250m to 1km resolution
        }
        
        return item;
    }
    
    private SatelliteImage processAlos(SatelliteImage item) {
        log.debug("Processing ALOS image");
        
        if (item.getResolution() == null) {
            item.setResolution(2.5); // PRISM 2.5m
        }
        
        return item;
    }
    
    private SatelliteImage processGeneric(SatelliteImage item) {
        log.debug("Processing generic satellite image");
        
        if (item.getResolution() == null) {
            item.setResolution(10.0);
        }
        
        return item;
    }
    
    private void markAsFailed(SatelliteImage item, String reason) {
        item.setStatus("FAILED");
        item.setErrorMessage(reason);
        item.setUpdatedAt(LocalDateTime.now());
        satelliteImageRepository.save(item);
        
        auditService.logAsync(
            "satellite_image",
            item.getId().toString(),
            "FAILED",
            reason
        );
    }
}