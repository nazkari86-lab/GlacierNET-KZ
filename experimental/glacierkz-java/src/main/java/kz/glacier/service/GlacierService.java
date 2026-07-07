package kz.glacier.service;

import kz.glacier.dto.GlacierDto;
import kz.glacier.model.Glacier;
import kz.glacier.repository.AuditLogRepository;
import kz.glacier.repository.GlacierRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class GlacierService {

    private final GlacierRepository glacierRepository;
    private final AuditLogRepository auditLogRepository;

    @Transactional(readOnly = true)
    public Page<Glacier> listAll(Pageable pageable) {
        return glacierRepository.findAll(pageable);
    }

    @Transactional(readOnly = true)
    public Glacier findById(UUID id) {
        return glacierRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Glacier not found: " + id));
    }

    @Transactional(readOnly = true)
    public List<Glacier> findByRegion(String region) {
        return glacierRepository.findByRegion(region, Pageable.unpaged()).getContent();
    }

    @Transactional(readOnly = true)
    public List<Glacier> findByName(String name) {
        return glacierRepository.findByNameContaining(name, Pageable.unpaged()).getContent();
    }

    @Transactional(readOnly = true)
    public List<Glacier> findWithinDistance(double lat, double lon, double distanceMeters) {
        String wkt = String.format("POINT(%f %f)", lon, lat);
        return glacierRepository.findWithinDistance(wkt, distanceMeters);
    }

    @Transactional(readOnly = true)
    public List<Glacier> findInBoundingBox(double minLon, double minLat, double maxLon, double maxLat) {
        return glacierRepository.findInBoundingBox(minLon, minLat, maxLon, maxLat);
    }

    @Transactional
    public Glacier create(GlacierDto dto) {
        Glacier glacier = new Glacier();
        applyDtoToEntity(dto, glacier);
        glacier.setDeleted(false);
        Glacier saved = glacierRepository.save(glacier);
        log.info("Created glacier: {} ({})", saved.getName(), saved.getId());
        return saved;
    }

    @Transactional
    public Glacier update(UUID id, GlacierDto dto) {
        Glacier glacier = findById(id);
        applyDtoToEntity(dto, glacier);
        Glacier saved = glacierRepository.save(glacier);
        log.info("Updated glacier: {} ({})", saved.getName(), saved.getId());
        return saved;
    }

    @Transactional
    public void softDelete(UUID id) {
        Glacier glacier = findById(id);
        glacier.setDeleted(true);
        glacierRepository.save(glacier);
        log.info("Soft-deleted glacier: {} ({})", glacier.getName(), id);
    }

    @Transactional(readOnly = true)
    public List<String> getDistinctRegions() {
        return glacierRepository.findDistinctRegions();
    }

    @Transactional(readOnly = true)
    public List<String> getDistinctMountainRanges() {
        return glacierRepository.findDistinctMountainRanges();
    }

    @Transactional(readOnly = true)
    public List<Glacier> getRetreatingGlaciers() {
        return glacierRepository.findRetreatingGlaciers(Pageable.unpaged()).getContent();
    }

    @Transactional(readOnly = true)
    public List<Glacier> getLargeGlaciers(double minArea) {
        return glacierRepository.findLargeGlaciers(minArea);
    }

    @Transactional(readOnly = true)
    public List<Glacier> findByElevationRange(double min, double max) {
        return glacierRepository.findByElevationRange(min, max);
    }

    @Transactional(readOnly = true)
    public List<Glacier> findByMountainRange(String mountainRange) {
        return glacierRepository.findByMountainRange(mountainRange);
    }

    @Transactional(readOnly = true)
    public List<Glacier> findNeedingResurvey(java.time.LocalDate beforeDate) {
        return glacierRepository.findNeedingResurvey(beforeDate);
    }

    @Transactional(readOnly = true)
    public long countActive() {
        return glacierRepository.countActive();
    }

    @Transactional(readOnly = true)
    public List<Glacier> findIntersecting(String wkt) {
        return glacierRepository.findIntersecting(wkt);
    }

    private void applyDtoToEntity(GlacierDto dto, Glacier glacier) {
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
    }
}
