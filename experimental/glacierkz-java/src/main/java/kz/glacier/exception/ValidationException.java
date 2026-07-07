package kz.glacier.exception;

import java.util.Map;

public class ValidationException extends RuntimeException {
    
    private final Map<String, String> fieldErrors;
    
    public ValidationException(String message) {
        super(message);
        this.fieldErrors = null;
    }
    
    public ValidationException(String message, Map<String, String> fieldErrors) {
        super(message);
        this.fieldErrors = fieldErrors;
    }
    
    public ValidationException(String resourceType, String field, String value) {
        super(String.format("Validation failed for %s: %s '%s' is invalid", resourceType, field, value));
        this.fieldErrors = null;
    }
    
    public Map<String, String> getFieldErrors() {
        return fieldErrors;
    }
    
    public boolean hasFieldErrors() {
        return fieldErrors != null && !fieldErrors.isEmpty();
    }
}