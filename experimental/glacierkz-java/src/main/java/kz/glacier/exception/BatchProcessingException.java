package kz.glacier.exception;

public class BatchProcessingException extends RuntimeException {
    
    private final String jobId;
    private final String step;
    
    public BatchProcessingException(String message) {
        super(message);
        this.jobId = null;
        this.step = null;
    }
    
    public BatchProcessingException(String message, String jobId, String step) {
        super(message);
        this.jobId = jobId;
        this.step = step;
    }
    
    public BatchProcessingException(String message, String jobId, String step, Throwable cause) {
        super(message, cause);
        this.jobId = jobId;
        this.step = step;
    }
    
    public String getJobId() {
        return jobId;
    }
    
    public String getStep() {
        return step;
    }
    
    public String getFormattedMessage() {
        StringBuilder sb = new StringBuilder();
        if (jobId != null) {
            sb.append("Job ").append(jobId);
        }
        if (step != null) {
            sb.append(" Step ").append(step);
        }
        sb.append(": ").append(getMessage());
        return sb.toString();
    }
}