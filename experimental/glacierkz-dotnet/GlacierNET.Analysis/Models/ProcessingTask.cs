using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace GlacierNET.Analysis.Models;

[Table("processing_tasks")]
public class ProcessingTask
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; } = Guid.NewGuid();

    [Required]
    [MaxLength(200)]
    [Column("name")]
    public string Name { get; set; } = string.Empty;

    [MaxLength(500)]
    [Column("description")]
    public string? Description { get; set; }

    [Required]
    [Column("task_type")]
    public string TaskType { get; set; } = string.Empty;

    [Required]
    [Column("status")]
    public TaskStatusType Status { get; set; } = TaskStatusType.Pending;

    [Column("priority")]
    public int Priority { get; set; } = 1;

    [Column("progress_percent")]
    public double ProgressPercent { get; set; }

    [Column("total_items")]
    public int TotalItems { get; set; }

    [Column("completed_items")]
    public int CompletedItems { get; set; }

    [Column("failed_items")]
    public int FailedItems { get; set; }

    [Column("started_at")]
    public DateTime? StartedAt { get; set; }

    [Column("completed_at")]
    public DateTime? CompletedAt { get; set; }

    [Column("estimated_duration_seconds")]
    public int? EstimatedDurationSeconds { get; set; }

    [Column("actual_duration_seconds")]
    public double? ActualDurationSeconds { get; set; }

    [MaxLength(100)]
    [Column("requested_by")]
    public string? RequestedBy { get; set; }

    [Column("parameters_json")]
    public string? ParametersJson { get; set; }

    [Column("result_json")]
    public string? ResultJson { get; set; }

    [Column("error_message")]
    public string? ErrorMessage { get; set; }

    [Column("retry_count")]
    public int RetryCount { get; set; }

    [Column("max_retries")]
    public int MaxRetries { get; set; } = 3;

    [Column("created_at")]
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [Column("updated_at")]
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;

    [NotMapped]
    public bool IsTerminal =>
        Status is TaskStatusType.Completed or TaskStatusType.Failed or TaskStatusType.Cancelled;

    [NotMapped]
    public bool CanRetry =>
        Status == TaskStatusType.Failed && RetryCount < MaxRetries;

    [NotMapped]
    public TimeSpan? ElapsedTime =>
        StartedAt.HasValue
            ? (CompletedAt ?? DateTime.UtcNow) - StartedAt.Value
            : null;

    [NotMapped]
    public TimeSpan? EstimatedTimeRemaining
    {
        get
        {
            if (!StartedAt.HasValue || ProgressPercent <= 0) return null;
            var elapsed = (CompletedAt ?? DateTime.UtcNow) - StartedAt.Value;
            var estimatedTotal = elapsed.TotalSeconds / (ProgressPercent / 100.0);
            return TimeSpan.FromSeconds(Math.Max(0, estimatedTotal - elapsed.TotalSeconds));
        }
    }
}
