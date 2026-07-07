using Microsoft.EntityFrameworkCore;
using GlacierNET.Analysis.Data;
using GlacierNET.Analysis.Models;

namespace GlacierNET.Analysis.Services;

public class PagedResult<T>
{
    public List<T> Items { get; set; } = new();
    public int TotalCount { get; set; }
    public int Page { get; set; }
    public int PageSize { get; set; }
    public int TotalPages => (int)Math.Ceiling((double)TotalCount / PageSize);
}

public class TaskStatistics
{
    public int Total { get; set; }
    public int Active { get; set; }
    public int Completed { get; set; }
    public int Failed { get; set; }
    public int Queued { get; set; }
    public double AverageCompletionTimeMinutes { get; set; }
}

public class ProcessingTaskService
{
    private readonly GlacierDbContext _context;
    private readonly ILogger<ProcessingTaskService> _logger;

    public ProcessingTaskService(GlacierDbContext context, ILogger<ProcessingTaskService> logger)
    {
        _context = context;
        _logger = logger;
    }

    public async Task<PagedResult<ProcessingTask>> GetAllTasksAsync(int page, int pageSize)
    {
        var query = _context.ProcessingTasks.OrderByDescending(t => t.CreatedAt);
        var total = await query.CountAsync();
        var items = await query.Skip((page - 1) * pageSize).Take(pageSize).ToListAsync();

        return new PagedResult<ProcessingTask>
        {
            Items = items,
            TotalCount = total,
            Page = page,
            PageSize = pageSize
        };
    }

    public async Task<ProcessingTask?> GetTaskByIdAsync(Guid id)
    {
        return await _context.ProcessingTasks.FindAsync(id);
    }

    public async Task<ProcessingTask> CreateTaskAsync(ProcessingTask task)
    {
        task.Id = Guid.NewGuid();
        task.CreatedAt = DateTime.UtcNow;
        task.UpdatedAt = DateTime.UtcNow;
        _context.ProcessingTasks.Add(task);
        await _context.SaveChangesAsync();
        return task;
    }

    public async Task<ProcessingTask?> StartTaskAsync(Guid id)
    {
        var task = await _context.ProcessingTasks.FindAsync(id);
        if (task == null) return null;

        task.Status = TaskStatusType.Running;
        task.StartedAt = DateTime.UtcNow;
        task.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();
        return task;
    }

    public async Task<ProcessingTask?> PauseTaskAsync(Guid id)
    {
        var task = await _context.ProcessingTasks.FindAsync(id);
        if (task == null) return null;

        task.Status = TaskStatusType.Paused;
        task.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();
        return task;
    }

    public async Task<ProcessingTask?> ResumeTaskAsync(Guid id)
    {
        var task = await _context.ProcessingTasks.FindAsync(id);
        if (task == null) return null;

        task.Status = TaskStatusType.Running;
        task.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();
        return task;
    }

    public async Task<ProcessingTask?> CancelTaskAsync(Guid id)
    {
        var task = await _context.ProcessingTasks.FindAsync(id);
        if (task == null) return null;

        task.Status = TaskStatusType.Cancelled;
        task.UpdatedAt = DateTime.UtcNow;
        task.ErrorMessage = "Cancelled by user";
        await _context.SaveChangesAsync();
        return task;
    }

    public async Task<List<ProcessingTask>> GetTasksByStatusAsync(TaskStatusType status)
    {
        return await _context.ProcessingTasks
            .Where(t => t.Status == status)
            .OrderByDescending(t => t.CreatedAt)
            .ToListAsync();
    }

    public async Task<List<ProcessingTask>> GetActiveTasksAsync()
    {
        return await _context.ProcessingTasks
            .Where(t => t.Status == TaskStatusType.Running || t.Status == TaskStatusType.Queued)
            .OrderByDescending(t => t.CreatedAt)
            .ToListAsync();
    }

    public async Task<TaskStatistics> GetTaskStatisticsAsync()
    {
        var tasks = await _context.ProcessingTasks.ToListAsync();

        return new TaskStatistics
        {
            Total = tasks.Count,
            Active = tasks.Count(t => t.Status == TaskStatusType.Running),
            Completed = tasks.Count(t => t.Status == TaskStatusType.Completed),
            Failed = tasks.Count(t => t.Status == TaskStatusType.Failed),
            Queued = tasks.Count(t => t.Status == TaskStatusType.Queued),
            AverageCompletionTimeMinutes = tasks
                .Where(t => t.Status == TaskStatusType.Completed && t.StartedAt.HasValue && t.CompletedAt.HasValue)
                .Select(t => (t.CompletedAt!.Value - t.StartedAt!.Value).TotalMinutes)
                .DefaultIfEmpty(0)
                .Average()
        };
    }

    public async Task<bool> DeleteTaskAsync(Guid id)
    {
        var task = await _context.ProcessingTasks.FindAsync(id);
        if (task == null) return false;

        _context.ProcessingTasks.Remove(task);
        await _context.SaveChangesAsync();
        return true;
    }
}
