package kz.glacier.exception;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@RestControllerAdvice
public class GlobalExceptionHandler {
    
    private static final Logger logger = LoggerFactory.getLogger(GlobalExceptionHandler.class);
    
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<Map<String, Object>> handleResourceNotFound(ResourceNotFoundException ex) {
        logger.error("Resource not found: {}", ex.getMessage());
        
        Map<String, Object> errorResponse = new HashMap<>();
        errorResponse.put("error", "Resource Not Found");
        errorResponse.put("message", ex.getMessage());
        errorResponse.put("timestamp", LocalDateTime.now());
        errorResponse.put("traceId", UUID.randomUUID().toString());
        
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(errorResponse);
    }
    
    @ExceptionHandler(ValidationException.class)
    public ResponseEntity<Map<String, Object>> handleValidation(ValidationException ex) {
        logger.error("Validation failed: {}", ex.getMessage());
        
        Map<String, Object> errorResponse = new HashMap<>();
        errorResponse.put("error", "Validation Failed");
        errorResponse.put("message", ex.getMessage());
        errorResponse.put("timestamp", LocalDateTime.now());
        errorResponse.put("traceId", UUID.randomUUID().toString());
        
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(errorResponse);
    }
    
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, Object>> handleMethodArgumentNotValid(MethodArgumentNotValidException ex) {
        logger.error("Method argument validation failed: {}", ex.getMessage());
        
        Map<String, Object> errorResponse = new HashMap<>();
        errorResponse.put("error", "Validation Failed");
        errorResponse.put("message", "Invalid input parameters");
        errorResponse.put("timestamp", LocalDateTime.now());
        errorResponse.put("traceId", UUID.randomUUID().toString());
        
        // Collect field errors
        Map<String, String> fieldErrors = new HashMap<>();
        ex.getBindingResult().getFieldErrors().forEach(fieldError -> {
            fieldErrors.put(fieldError.getField(), fieldError.getDefaultMessage());
        });
        errorResponse.put("fieldErrors", fieldErrors);
        
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(errorResponse);
    }
    
    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Map<String, Object>> handleIllegalArgument(IllegalArgumentException ex) {
        logger.error("Illegal argument: {}", ex.getMessage());
        
        Map<String, Object> errorResponse = new HashMap<>();
        errorResponse.put("error", "Bad Request");
        errorResponse.put("message", ex.getMessage());
        errorResponse.put("timestamp", LocalDateTime.now());
        errorResponse.put("traceId", UUID.randomUUID().toString());
        
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(errorResponse);
    }
    
    @ExceptionHandler(IllegalStateException.class)
    public ResponseEntity<Map<String, Object>> handleIllegalState(IllegalStateException ex) {
        logger.error("Illegal state: {}", ex.getMessage());
        
        Map<String, Object> errorResponse = new HashMap<>();
        errorResponse.put("error", "Conflict");
        errorResponse.put("message", ex.getMessage());
        errorResponse.put("timestamp", LocalDateTime.now());
        errorResponse.put("traceId", UUID.randomUUID().toString());
        
        return ResponseEntity.status(HttpStatus.CONFLICT).body(errorResponse);
    }
    
    @ExceptionHandler(SecurityException.class)
    public ResponseEntity<Map<String, Object>> handleSecurityException(SecurityException ex) {
        logger.error("Security exception: {}", ex.getMessage());
        
        Map<String, Object> errorResponse = new HashMap<>();
        errorResponse.put("error", "Forbidden");
        errorResponse.put("message", "Access denied");
        errorResponse.put("timestamp", LocalDateTime.now());
        errorResponse.put("traceId", UUID.randomUUID().toString());
        
        return ResponseEntity.status(HttpStatus.FORBIDDEN).body(errorResponse);
    }
    
    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleGenericException(Exception ex) {
        logger.error("Unexpected error occurred", ex);
        
        Map<String, Object> errorResponse = new HashMap<>();
        errorResponse.put("error", "Internal Server Error");
        errorResponse.put("message", "An unexpected error occurred");
        errorResponse.put("timestamp", LocalDateTime.now());
        errorResponse.put("traceId", UUID.randomUUID().toString());
        
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
    }
    
    @ExceptionHandler(BatchProcessingException.class)
    public ResponseEntity<Map<String, Object>> handleBatchProcessingException(BatchProcessingException ex) {
        logger.error("Batch processing error: {}", ex.getMessage());
        
        Map<String, Object> errorResponse = new HashMap<>();
        errorResponse.put("error", "Batch Processing Failed");
        errorResponse.put("message", ex.getMessage());
        errorResponse.put("timestamp", LocalDateTime.now());
        errorResponse.put("traceId", UUID.randomUUID().toString());
        errorResponse.put("jobId", ex.getJobId());
        errorResponse.put("step", ex.getStep());
        
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
    }
    
    @ExceptionHandler(ProcessingException.class)
    public ResponseEntity<Map<String, Object>> handleProcessingException(ProcessingException ex) {
        logger.error("Processing error: {}", ex.getMessage());
        
        Map<String, Object> errorResponse = new HashMap<>();
        errorResponse.put("error", "Processing Failed");
        errorResponse.put("message", ex.getMessage());
        errorResponse.put("timestamp", LocalDateTime.now());
        errorResponse.put("traceId", UUID.randomUUID().toString());
        
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
    }
    
    @ExceptionHandler(CacheException.class)
    public ResponseEntity<Map<String, Object>> handleCacheException(CacheException ex) {
        logger.error("Cache error: {}", ex.getMessage());
        
        Map<String, Object> errorResponse = new HashMap<>();
        errorResponse.put("error", "Cache Error");
        errorResponse.put("message", ex.getMessage());
        errorResponse.put("timestamp", LocalDateTime.now());
        errorResponse.put("traceId", UUID.randomUUID().toString());
        
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(errorResponse);
    }
    
    @ExceptionHandler(GeoServerException.class)
    public ResponseEntity<Map<String, Object>> handleGeoServerException(GeoServerException ex) {
        logger.error("GeoServer error: {}", ex.getMessage());
        
        Map<String, Object> errorResponse = new HashMap<>();
        errorResponse.put("error", "GeoServer Error");
        errorResponse.put("message", ex.getMessage());
        errorResponse.put("timestamp", LocalDateTime.now());
        errorResponse.put("traceId", UUID.randomUUID().toString());
        
        return ResponseEntity.status(HttpStatus.BAD_GATEWAY).body(errorResponse);
    }
}