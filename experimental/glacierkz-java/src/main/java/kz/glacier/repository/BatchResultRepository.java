package kz.glacier.repository;

import kz.glacier.model.BatchResult;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface BatchResultRepository extends JpaRepository<BatchResult, UUID> {

    @Query("SELECT b FROM BatchResult b WHERE b.rasterJob.id = :jobId ORDER BY b.createdAt DESC")
    List<BatchResult> findByRasterJobId(@Param("jobId") UUID jobId);

    @Query("SELECT b FROM BatchResult b WHERE b.processingStatus = :status")
    Page<BatchResult> findByProcessingStatus(@Param("status") String status, Pageable pageable);

    @Query("SELECT b FROM BatchResult b WHERE b.resultType = :resultType")
    List<BatchResult> findByResultType(@Param("resultType") String resultType);

    @Query("SELECT b FROM BatchResult b WHERE b.rasterJob.glacier.id = :glacierId ORDER BY b.createdAt DESC")
    List<BatchResult> findByGlacierId(@Param("glacierId") UUID glacierId);

    @Query("SELECT b FROM BatchResult b WHERE b.outputFormat = :format")
    List<BatchResult> findByOutputFormat(@Param("format") String format);

    @Query("SELECT b FROM BatchResult b WHERE b.processingStatus = 'FAILED' AND b.errorCode = :errorCode")
    List<BatchResult> findFailedByErrorCode(@Param("errorCode") String errorCode);

    @Query("SELECT b FROM BatchResult b WHERE b.processingStatus = 'COMPLETED' AND b.outputFilePath IS NOT NULL")
    Page<BatchResult> findCompletedWithOutput(Pageable pageable);

    @Query("SELECT COUNT(b) FROM BatchResult b WHERE b.processingStatus = :status")
    long countByStatus(@Param("status") String status);

    @Query("SELECT b FROM BatchResult b WHERE b.processingStatus = 'COMPLETED' AND b.rasterJob.glacier.id = :glacierId ORDER BY b.createdAt DESC")
    List<BatchResult> findCompletedByGlacierId(@Param("glacierId") UUID glacierId);

    @Query("SELECT b FROM BatchResult b WHERE b.outputCrs = :crs AND b.processingStatus = 'COMPLETED'")
    List<BatchResult> findCompletedByCrs(@Param("crs") String crs);

    @Query("SELECT b FROM BatchResult b WHERE b.spatialResolutionM <= :maxResolution AND b.processingStatus = 'COMPLETED'")
    List<BatchResult> findHighResolution(@Param("maxResolution") double maxResolution);
}
