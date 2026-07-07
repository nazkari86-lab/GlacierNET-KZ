package kz.glacier.repository;

import kz.glacier.model.AuditLog;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Repository
public interface AuditLogRepository extends JpaRepository<AuditLog, UUID> {

    @Query("SELECT a FROM AuditLog a WHERE a.userId = :userId ORDER BY a.createdAt DESC")
    Page<AuditLog> findByUserId(@Param("userId") UUID userId, Pageable pageable);

    @Query("SELECT a FROM AuditLog a WHERE a.action = :action ORDER BY a.createdAt DESC")
    Page<AuditLog> findByAction(@Param("action") String action, Pageable pageable);

    @Query("SELECT a FROM AuditLog a WHERE a.entityType = :entityType AND a.entityId = :entityId")
    List<AuditLog> findByEntity(@Param("entityType") String entityType, @Param("entityId") String entityId);

    @Query("SELECT a FROM AuditLog a WHERE a.createdAt BETWEEN :from AND :to ORDER BY a.createdAt DESC")
    Page<AuditLog> findByDateRange(@Param("from") Instant from, @Param("to") Instant to, Pageable pageable);

    @Query("SELECT a FROM AuditLog a WHERE a.success = false ORDER BY a.createdAt DESC")
    Page<AuditLog> findFailedActions(Pageable pageable);

    @Query("SELECT a FROM AuditLog a WHERE a.ipAddress = :ipAddress ORDER BY a.createdAt DESC")
    List<AuditLog> findByIpAddress(@Param("ipAddress") String ipAddress);

    @Query("SELECT a FROM AuditLog a WHERE a.correlationId = :correlationId")
    List<AuditLog> findByCorrelationId(@Param("correlationId") String correlationId);

    @Query("SELECT a FROM AuditLog a WHERE a.userId = :userId AND a.action = :action AND a.createdAt > :since")
    List<AuditLog> findByUserAndActionSince(@Param("userId") UUID userId, @Param("action") String action, @Param("since") Instant since);

    @Query("SELECT a FROM AuditLog a WHERE a.serviceName = :serviceName AND a.createdAt BETWEEN :from AND :to ORDER BY a.createdAt DESC")
    Page<AuditLog> findByServiceAndDateRange(@Param("serviceName") String serviceName, @Param("from") Instant from, @Param("to") Instant to, Pageable pageable);

    @Query("SELECT a FROM AuditLog a WHERE a.executionTimeMs > :thresholdMs ORDER BY a.executionTimeMs DESC")
    List<AuditLog> findSlowOperations(@Param("thresholdMs") long thresholdMs);

    @Query("SELECT a FROM AuditLog a WHERE a.requestUri LIKE CONCAT('%', :uriPattern, '%') ORDER BY a.createdAt DESC")
    Page<AuditLog> findByUriPattern(@Param("uriPattern") String uriPattern, Pageable pageable);

    @Query("SELECT a FROM AuditLog a WHERE a.username = :username AND a.createdAt > :since ORDER BY a.createdAt DESC")
    List<AuditLog> findByUsernameSince(@Param("username") String username, @Param("since") Instant since);
}
