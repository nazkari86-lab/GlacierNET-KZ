package kz.glacier.service;

import kz.glacier.model.AuditLog;
import kz.glacier.repository.AuditLogRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

@Service
@RequiredArgsConstructor
@Slf4j
public class AuditService {

    private final AuditLogRepository auditLogRepository;

    @Async
    @Transactional
    public CompletableFuture<Void> logAction(String username, UUID userId, String action,
                                              String entityType, String entityId,
                                              String requestUri, String method,
                                              String ipAddress, String correlationId,
                                              boolean success, long executionTimeMs,
                                              String serviceName, String details) {
        AuditLog auditLog = new AuditLog();
        auditLog.setUsername(username);
        auditLog.setUserId(userId);
        auditLog.setAction(action);
        auditLog.setEntityType(entityType);
        auditLog.setEntityId(entityId);
        auditLog.setRequestUri(requestUri);
        auditLog.setHttpMethod(method);
        auditLog.setIpAddress(ipAddress);
        auditLog.setCorrelationId(correlationId);
        auditLog.setSuccess(success);
        auditLog.setExecutionTimeMs(executionTimeMs);
        auditLog.setServiceName(serviceName);
        auditLog.setDetails(details);

        auditLogRepository.save(auditLog);
        log.debug("Audit: {} {} by {} ({}ms)", action, entityType, username, executionTimeMs);
        return CompletableFuture.completedFuture(null);
    }

    @Transactional
    public AuditLog logSync(String username, UUID userId, String action,
                            String entityType, String entityId,
                            String requestUri, String method,
                            String ipAddress, String correlationId,
                            boolean success, long executionTimeMs,
                            String serviceName) {
        AuditLog auditLog = new AuditLog();
        auditLog.setUsername(username);
        auditLog.setUserId(userId);
        auditLog.setAction(action);
        auditLog.setEntityType(entityType);
        auditLog.setEntityId(entityId);
        auditLog.setRequestUri(requestUri);
        auditLog.setHttpMethod(method);
        auditLog.setIpAddress(ipAddress);
        auditLog.setCorrelationId(correlationId);
        auditLog.setSuccess(success);
        auditLog.setExecutionTimeMs(executionTimeMs);
        auditLog.setServiceName(serviceName);

        return auditLogRepository.save(auditLog);
    }

    @Transactional(readOnly = true)
    public Page<AuditLog> findByUserId(UUID userId, Pageable pageable) {
        return auditLogRepository.findByUserId(userId, pageable);
    }

    @Transactional(readOnly = true)
    public Page<AuditLog> findByAction(String action, Pageable pageable) {
        return auditLogRepository.findByAction(action, pageable);
    }

    @Transactional(readOnly = true)
    public List<AuditLog> findByEntity(String entityType, String entityId) {
        return auditLogRepository.findByEntity(entityType, entityId);
    }

    @Transactional(readOnly = true)
    public Page<AuditLog> findByDateRange(Instant from, Instant to, Pageable pageable) {
        return auditLogRepository.findByDateRange(from, to, pageable);
    }

    @Transactional(readOnly = true)
    public Page<AuditLog> findFailedActions(Pageable pageable) {
        return auditLogRepository.findFailedActions(pageable);
    }

    @Transactional(readOnly = true)
    public List<AuditLog> findByIpAddress(String ipAddress) {
        return auditLogRepository.findByIpAddress(ipAddress);
    }

    @Transactional(readOnly = true)
    public List<AuditLog> findSlowOperations(long thresholdMs) {
        return auditLogRepository.findSlowOperations(thresholdMs);
    }

    @Transactional(readOnly = true)
    public List<AuditLog> findByCorrelationId(String correlationId) {
        return auditLogRepository.findByCorrelationId(correlationId);
    }

    @Transactional(readOnly = true)
    public List<AuditLog> findByUsernameSince(String username, Instant since) {
        return auditLogRepository.findByUsernameSince(username, since);
    }

    @Transactional(readOnly = true)
    public Page<AuditLog> findByServiceAndDateRange(String serviceName, Instant from, Instant to, Pageable pageable) {
        return auditLogRepository.findByServiceAndDateRange(serviceName, from, to, pageable);
    }

    @Transactional
    public void cleanupOldLogs(Instant olderThan) {
        List<AuditLog> oldLogs = auditLogRepository.findByDateRange(Instant.EPOCH, olderThan, Pageable.unpaged()).getContent();
        auditLogRepository.deleteAll(oldLogs);
        log.info("Cleaned up {} old audit log entries", oldLogs.size());
    }
}
