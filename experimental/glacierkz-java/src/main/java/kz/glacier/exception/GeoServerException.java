package kz.glacier.exception;

public class GeoServerException extends RuntimeException {
    
    public GeoServerException(String message) {
        super(message);
    }
    
    public GeoServerException(String message, Throwable cause) {
        super(message, cause);
    }
    
    public GeoServerException(String operation, String resource, String reason) {
        super(String.format("GeoServer operation failed for %s on %s: %s", operation, resource, reason));
    }
}