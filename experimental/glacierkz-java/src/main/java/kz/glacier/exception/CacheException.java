package kz.glacier.exception;

public class CacheException extends RuntimeException {
    
    public CacheException(String message) {
        super(message);
    }
    
    public CacheException(String message, Throwable cause) {
        super(message, cause);
    }
    
    public CacheException(String cacheName, String operation, String reason) {
        super(String.format("Cache operation failed for '%s' during %s: %s", cacheName, operation, reason));
    }
}