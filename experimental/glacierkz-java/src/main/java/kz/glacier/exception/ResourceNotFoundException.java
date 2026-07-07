package kz.glacier.exception;

public class ResourceNotFoundException extends RuntimeException {
    
    public ResourceNotFoundException(String message) {
        super(message);
    }
    
    public ResourceNotFoundException(String resourceType, String resourceId) {
        super(String.format("%s with ID %s not found", resourceType, resourceId));
    }
    
    public ResourceNotFoundException(String resourceType, String field, String value) {
        super(String.format("%s with %s '%s' not found", resourceType, field, value));
    }
}