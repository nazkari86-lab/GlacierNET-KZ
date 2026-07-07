package kz.glacier.repository;

import kz.glacier.model.Glacier;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface GlacierRepository extends JpaRepository<Glacier, UUID> {

    @Query("SELECT g FROM Glacier g WHERE g.deleted = false AND g.region = :region")
    Page<Glacier> findByRegion(@Param("region") String region, Pageable pageable);

    @Query("SELECT g FROM Glacier g WHERE g.deleted = false AND g.status = :status")
    Page<Glacier> findByStatus(@Param("status") String status, Pageable pageable);

    @Query("SELECT g FROM Glacier g WHERE g.deleted = false AND g.mountainRange = :mountainRange")
    List<Glacier> findByMountainRange(@Param("mountainRange") String mountainRange);

    @Query("SELECT g FROM Glacier g WHERE g.deleted = false AND LOWER(g.name) LIKE LOWER(CONCAT('%', :name, '%'))")
    Page<Glacier> findByNameContaining(@Param("name") String name, Pageable pageable);

    @Query("SELECT g FROM Glacier g WHERE g.deleted = false AND g.classification = :classification")
    List<Glacier> findByClassification(@Param("classification") String classification);

    @Query(value = "SELECT * FROM glaciers g WHERE g.deleted = false " +
            "AND ST_Within(g.geometry, ST_GeomFromText(:wkt, 4326))", nativeQuery = true)
    List<Glacier> findWithinGeometry(@Param("wkt") String wkt);

    @Query(value = "SELECT * FROM glaciers g WHERE g.deleted = false " +
            "AND ST_DWithin(g.geometry::geography, ST_GeomFromText(:wkt, 4326)::geography, :distanceMeters)", nativeQuery = true)
    List<Glacier> findWithinDistance(@Param("wkt") String wkt, @Param("distanceMeters") double distanceMeters);

    @Query(value = "SELECT * FROM glaciers g WHERE g.deleted = false " +
            "AND ST_Intersects(g.geometry, ST_GeomFromText(:wkt, 4326))", nativeQuery = true)
    List<Glacier> findIntersecting(@Param("wkt") String wkt);

    @Query(value = "SELECT * FROM glaciers g WHERE g.deleted = false " +
            "AND ST_Envelope(g.geometry) && ST_MakeEnvelope(:minLon, :minLat, :maxLon, :maxLat, 4326)", nativeQuery = true)
    List<Glacier> findInBoundingBox(@Param("minLon") double minLon, @Param("minLat") double minLat,
                                    @Param("maxLon") double maxLon, @Param("maxLat") double maxLat);

    @Query(value = "SELECT * FROM glaciers g WHERE g.deleted = false " +
            "ORDER BY g.geometry <-> ST_GeomFromText(:wkt, 4326) LIMIT :limit", nativeQuery = true)
    List<Glacier> findNearest(@Param("wkt") String wkt, @Param("limit") int limit);

    @Query("SELECT g FROM Glacier g WHERE g.deleted = false AND g.massBalance < 0 ORDER BY g.massBalance ASC")
    Page<Glacier> findRetreatingGlaciers(Pageable pageable);

    @Query("SELECT g FROM Glacier g WHERE g.deleted = false AND g.areaSquareKm >= :minArea ORDER BY g.areaSquareKm DESC")
    List<Glacier> findLargeGlaciers(@Param("minArea") double minArea);

    @Query("SELECT DISTINCT g.region FROM Glacier g WHERE g.deleted = false ORDER BY g.region")
    List<String> findDistinctRegions();

    @Query("SELECT DISTINCT g.mountainRange FROM Glacier g WHERE g.deleted = false AND g.mountainRange IS NOT NULL ORDER BY g.mountainRange")
    List<String> findDistinctMountainRanges();

    @Query("SELECT g FROM Glacier g WHERE g.deleted = false AND g.lastSurveyDate < :beforeDate")
    List<Glacier> findNeedingResurvey(@Param("beforeDate") java.time.LocalDate beforeDate);

    @Query("SELECT g FROM Glacier g WHERE g.deleted = false ORDER BY g.areaSquareKm DESC LIMIT 1")
    Optional<Glacier> findLargestGlacier();

    @Query("SELECT COUNT(g) FROM Glacier g WHERE g.deleted = false")
    long countActive();

    @Query("SELECT g FROM Glacier g WHERE g.deleted = false AND g.region = :region AND g.mountainRange = :mountainRange")
    List<Glacier> findByRegionAndMountainRange(@Param("region") String region, @Param("mountainRange") String mountainRange);

    @Query("SELECT g FROM Glacier g WHERE g.deleted = false AND g.elevationMax >= :minElevation AND g.elevationMax <= :maxElevation")
    List<Glacier> findByElevationRange(@Param("minElevation") double minElevation, @Param("maxElevation") double maxElevation);
}
