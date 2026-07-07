using System.Text.Json;
using Microsoft.AspNetCore.SignalR;
using GlacierNET.Analysis.Data;
using GlacierNET.Analysis.Hubs;
using GlacierNET.Analysis.Models;

namespace GlacierNET.Analysis.Services;

public class NotificationService
{
    private readonly IHubContext<MonitoringHub> _monitoringHub;
    private readonly IHubContext<TaskProgressHub> _taskHub;
    private readonly ILogger<NotificationService> _logger;

    public NotificationService(
        IHubContext<MonitoringHub> monitoringHub,
        IHubContext<TaskProgressHub> taskHub,
        ILogger<NotificationService> logger)
    {
        _monitoringHub = monitoringHub;
        _taskHub = taskHub;
        _logger = logger;
    }

    public async Task NotifyGlacierUpdatedAsync(Glacier glacier)
    {
        var message = new
        {
            type = "glacier_updated",
            glacierId = glacier.Id,
            name = glacier.Name,
            region = glacier.Region,
            status = glacier.Status.ToString(),
            updatedAt = glacier.UpdatedAt
        };

        await _monitoringHub.Clients.All.SendAsync("GlacierUpdated", message);
        _logger.LogDebug("Notified clients of glacier update: {Id}", glacier.Id);
    }

    public async Task NotifyGlacierCreatedAsync(Glacier glacier)
    {
        var message = new
        {
            type = "glacier_created",
            glacierId = glacier.Id,
            name = glacier.Name,
            region = glacier.Region,
            createdAt = glacier.CreatedAt
        };

        await _monitoringHub.Clients.All.SendAsync("GlacierCreated", message);
    }

    public async Task NotifyGlacierDeletedAsync(Guid glacierId)
    {
        await _monitoringHub.Clients.All.SendAsync("GlacierDeleted", new { glacierId, deletedAt = DateTime.UtcNow });
    }

    public async Task NotifyAnalysisCompletedAsync(AnalysisResult result)
    {
        var message = new
        {
            type = "analysis_completed",
            resultId = result.Id,
            glacierId = result.GlacierId,
            analysisType = result.AnalysisType.ToString(),
            value = result.Value,
            unit = result.Unit,
            isAnomaly = result.IsAnomaly,
            completedAt = result.CreatedAt
        };

        await _monitoringHub.Clients.All.SendAsync("AnalysisCompleted", message);

        if (result.IsAnomaly)
        {
            await NotifyAnomalyDetectedAsync(result);
        }
    }

    public async Task NotifyAnomalyDetectedAsync(AnalysisResult anomaly)
    {
        var message = new
        {
            type = "anomaly_detected",
            resultId = anomaly.Id,
            glacierId = anomaly.GlacierId,
            analysisType = anomaly.AnalysisType.ToString(),
            value = anomaly.Value,
            severity = anomaly.AnomalySeverity?.ToString() ?? "Unknown",
            detectedAt = DateTime.UtcNow
        };

        await _monitoringHub.Clients.All.SendAsync("AnomalyDetected", message);
        _logger.LogWarning("Anomaly detected for glacier {GlacierId}: {Type} = {Value}",
            anomaly.GlacierId, anomaly.AnalysisType, anomaly.Value);
    }

    public async Task NotifyTaskProgressAsync(ProcessingTask task)
    {
        var message = new
        {
            taskId = task.Id,
            name = task.Name,
            status = task.Status.ToString(),
            progressPercent = task.ProgressPercent,
            completedItems = task.CompletedItems,
            totalItems = task.TotalItems,
            failedItems = task.FailedItems,
            estimatedTimeRemaining = task.EstimatedTimeRemaining?.TotalSeconds,
            updatedAt = task.UpdatedAt
        };

        await _taskHub.Clients.All.SendAsync("TaskProgress", message);
    }

    public async Task NotifyTaskCompletedAsync(ProcessingTask task)
    {
        var message = new
        {
            taskId = task.Id,
            name = task.Name,
            status = "Completed",
            progressPercent = 100.0,
            completedItems = task.CompletedItems,
            totalItems = task.TotalItems,
            completedAt = task.CompletedAt ?? DateTime.UtcNow,
            actualDuration = task.ActualDurationSeconds
        };

        await _taskHub.Clients.All.SendAsync("TaskCompleted", message);
    }

    public async Task NotifyTaskFailedAsync(ProcessingTask task)
    {
        var message = new
        {
            taskId = task.Id,
            name = task.Name,
            status = "Failed",
            errorMessage = task.ErrorMessage,
            failedAt = DateTime.UtcNow
        };

        await _taskHub.Clients.All.SendAsync("TaskFailed", message);
        _logger.LogError("Task {TaskId} failed: {Error}", task.Id, task.ErrorMessage);
    }

    public async Task SendSystemAlertAsync(string title, string message, SeverityLevel severity)
    {
        var alert = new
        {
            type = "system_alert",
            title,
            message,
            severity = severity.ToString(),
            timestamp = DateTime.UtcNow
        };

        await _monitoringHub.Clients.All.SendAsync("SystemAlert", alert);
        _logger.LogWarning("System alert [{Severity}]: {Title} — {Message}", severity, title, message);
    }

    public async Task NotifyDataExportedAsync(string format, int recordCount, string requestedBy)
    {
        var message = new
        {
            type = "data_exported",
            format,
            recordCount,
            requestedBy,
            exportedAt = DateTime.UtcNow
        };

        await _monitoringHub.Clients.All.SendAsync("DataExported", message);
    }

    public async Task BroadcastStatusUpdateAsync(object statusData)
    {
        await _monitoringHub.Clients.All.SendAsync("StatusUpdate", statusData);
    }
}
