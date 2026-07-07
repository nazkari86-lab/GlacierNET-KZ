package kz.glacier.repository;

import kz.glacier.model.SatelliteImage;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

@Repository
public interface SatelliteImageRepository extends JpaRepository<SatelliteImage, UUID> {

    @Query("SELECT s FROM SatelliteImage s WHERE s.glacier.id = :glacierId ORDER BY s.captureDate DESC")
    List<SatelliteImage> findByGlacierId(@Param("glacierId") UUID glacierId);

    @Query("SELECT s FROM SatelliteImage s WHERE s.processingStatus = :status")
    Page<SatelliteImage> findByProcessingStatus(@Param("status") String status, Pageable pageable);

    @Query("SELECT s FROM SatelliteImage s WHERE s.dataSource = :dataSource")
    List<SatelliteImage> findByDataSource(@Param("dataSource") String dataSource);

    @Query("SELECT s FROM SatelliteImage s WHERE s.captureDate BETWEEN :from AND :to ORDER BY s.captureDate DESC")
    List<SatelliteImage> findByCaptureDateRange(@Param("from") LocalDate from, @Param("to") LocalDate to);

    @Query("SELECT s FROM SatelliteImage s WHERE s.satelliteName = :satelliteName ORDER BY s.captureDate DESC")
    List<SatelliteImage> findBySatelliteName(@Param("satelliteName") String satelliteName);

    @Query("SELECT s FROM SatelliteImage s WHERE s.cloudCoverPercent <= :maxCloudCover AND s.processingStatus = 'COMPLETED' ORDER BY s.captureDate DESC")
    List<SatelliteImage> findCloudFreeImages(@Param("maxCloudCover") double maxCloudCover);

    @Query("SELECT s FROM SatelliteImage s WHERE s.glacier.id = :glacierId AND s.captureDate BETWEEN :from AND :to ORDER BY s.captureDate DESC")
    List<SatelliteImage> findByGlacierAndDateRange(@Param("glacierId") UUID glacierId, @Param("from") LocalDate from, @Param("to") LocalDate to);

    @Query("SELECT s FROM SatelliteImage s WHERE s.processingStatus = 'PENDING' ORDER BY s.createdAt ASC")
    List<SatelliteImage> findPendingImages();

    @Query("SELECT s FROM SatelliteImage s WHERE s.spatialResolutionM <= :maxResolution ORDER BY s.spatialResolutionM ASC")
    List<SatelliteImage> findHighResolution(@Param("maxResolution") double maxResolution);

    @Query("SELECT s FROM SatelliteImage s WHERE s.checksumSha256 = :checksum")
    List<SatelliteImage> findByChecksum(@Param("checksum") String checksum);

    @Query("SELECT COUNT(s) FROM SatelliteImage s WHERE s.glacier.id = :glacierId AND s.processingStatus = :status")
    long countByGlacierAndStatus(@Param("glacierId") UUID glacierId, @Param("status") String status);

    @Query("SELECT s FROM SatelliteImage s WHERE s.glacier.id = :glacierId AND s.captureDate = " +
            "(SELECT MAX(s2.captureDate) FROM SatelliteImage s2 WHERE s2.glacier.id = :glacierId AND s2.processingStatus = 'COMPLETED')")
    SatelliteImage findLatestCompletedForGlacier(@Param("glacierId") UUID glacierId);

    @Query("SELECT s FROM SatelliteImage s WHERE s.createdAt > :since AND s.processingStatus = 'FAILED'")
    List<SatelliteImage> findRecentFailed(@Param("since") Instant since);

    @Query("SELECT DISTINCT s.satelliteName FROM SatelliteImage s WHERE s.satelliteName IS NOT NULL")
    List<String> findDistinctSatelliteNames();

    @Query("SELECT DISTINCT s.dataSource FROM SatelliteImage s WHERE s.dataSource IS NOT NULL")
    List<String> findDistinctDataSources();
}
