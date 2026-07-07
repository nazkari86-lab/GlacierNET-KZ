package kz.glacier.exception;

public class ProcessingException extends RuntimeException {
    
    public ProcessingException(String message) {
        super(message);
    }
    
    public ProcessingException(String message, Throwable cause) {
        super(message, cause);
    }
    
    public ProcessingException(String resourceType, String operation, String reason) {
        super(String.format("Processing failed for %s during %s: %s", resourceType, operation, reason));
    }
}