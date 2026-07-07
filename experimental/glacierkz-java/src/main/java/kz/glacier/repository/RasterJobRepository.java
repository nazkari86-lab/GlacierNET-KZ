package kz.glacier.repository;

import kz.glacier.model.RasterJob;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface RasterJobRepository extends JpaRepository<RasterJob, UUID> {

    @Query("SELECT r FROM RasterJob r WHERE r.status = :status")
    Page<RasterJob> findByStatus(@Param("status") String status, Pageable pageable);

    @Query("SELECT r FROM RasterJob r WHERE r.glacier.id = :glacierId ORDER BY r.createdAt DESC")
    List<RasterJob> findByGlacierId(@Param("glacierId") UUID glacierId);

    @Query("SELECT r FROM RasterJob r WHERE r.createdBy = :username")
    Page<RasterJob> findByCreatedBy(@Param("username") String username, Pageable pageable);

    @Query("SELECT r FROM RasterJob r WHERE r.jobType = :jobType AND r.status = :status")
    List<RasterJob> findByJobTypeAndStatus(@Param("jobType") String jobType, @Param("status") String status);

    @Query("SELECT r FROM RasterJob r WHERE r.status IN ('PENDING', 'RUNNING') ORDER BY r.priority ASC, r.createdAt ASC")
    List<RasterJob> findPendingOrRunningJobs();

    @Query("SELECT r FROM RasterJob r WHERE r.status = 'RUNNING' AND r.startedAt < :beforeTime")
    List<RasterJob> findStaleRunningJobs(@Param("beforeTime") Instant beforeTime);

    @Query("SELECT r FROM RasterJob r WHERE r.status = 'FAILED' AND r.retryCount < r.maxRetries")
    List<RasterJob> findRetryableFailedJobs();

    @Query("SELECT r FROM RasterJob r WHERE r.createdAt BETWEEN :from AND :to ORDER BY r.createdAt DESC")
    Page<RasterJob> findByDateRange(@Param("from") Instant from, @Param("to") Instant to, Pageable pageable);

    @Query("SELECT r FROM RasterJob r WHERE r.batchExecutionId = :executionId")
    Optional<RasterJob> findByBatchExecutionId(@Param("executionId") Long executionId);

    @Query("SELECT r FROM RasterJob r WHERE r.status = 'COMPLETED' AND r.completedAt BETWEEN :from AND :to")
    List<RasterJob> findCompletedInRange(@Param("from") Instant from, @Param("to") Instant to);

    @Query("SELECT r FROM RasterJob r WHERE r.glacier.id = :glacierId AND r.status = 'COMPLETED' ORDER BY r.completedAt DESC")
    List<RasterJob> findCompletedByGlacierId(@Param("glacierId") UUID glacierId);

    @Query("SELECT COUNT(r) FROM RasterJob r WHERE r.status = :status")
    long countByStatus(@Param("status") String status);

    @Query("SELECT r FROM RasterJob r WHERE r.priority <= :maxPriority AND r.status = 'PENDING' ORDER BY r.priority ASC, r.createdAt ASC")
    List<RasterJob> findHighPriorityPending(@Param("maxPriority") int maxPriority);

    @Query("SELECT r FROM RasterJob r WHERE r.status = 'RUNNING'")
    List<RasterJob> findRunningJobs();

    @Query(value = "SELECT r.* FROM raster_jobs r WHERE r.created_at > :since " +
            "AND r.status = 'COMPLETED' ORDER BY r.duration_ms ASC LIMIT :topN", nativeQuery = true)
    List<RasterJob> findTopPerformers(@Param("since") Instant since, @Param("topN") int topN);
}
