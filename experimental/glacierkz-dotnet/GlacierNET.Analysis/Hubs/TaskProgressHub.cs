using Microsoft.AspNetCore.SignalR;

namespace GlacierNET.Analysis.Hubs;

public class TaskProgressHub : Hub
{
    private readonly ILogger<TaskProgressHub> _logger;

    public TaskProgressHub(ILogger<TaskProgressHub> logger)
    {
        _logger = logger;
    }

    public override async Task OnConnectedAsync()
    {
        _logger.LogInformation("Client connected to TaskProgressHub: {ConnectionId}", Context.ConnectionId);
        await Groups.AddToGroupAsync(Context.ConnectionId, "TaskWatchers");
        await base.OnConnectedAsync();
    }

    public override async Task OnDisconnectedAsync(Exception? exception)
    {
        _logger.LogInformation("Client disconnected from TaskProgressHub: {ConnectionId}", Context.ConnectionId);
        await base.OnDisconnectedAsync(exception);
    }

    public async Task WatchTask(Guid taskId)
    {
        await Groups.AddToGroupAsync(Context.ConnectionId, $"task-{taskId}");
        _logger.LogDebug("Client {ConnectionId} watching task {TaskId}", Context.ConnectionId, taskId);
    }

    public async Task StopWatchingTask(Guid taskId)
    {
        await Groups.RemoveFromGroupAsync(Context.ConnectionId, $"task-{taskId}");
    }

    public async Task CancelTask(Guid taskId)
    {
        await Clients.Group("TaskWatchers").SendAsync("TaskCancellationRequested", new
        {
            taskId,
            requestedBy = Context.ConnectionId,
            requestedAt = DateTime.UtcNow
        });
        _logger.LogWarning("Task cancellation requested: {TaskId} by {ConnectionId}", taskId, Context.ConnectionId);
    }

    public async Task GetTaskSummary()
    {
        await Clients.Caller.SendAsync("TaskSummary", new
        {
            message = "Task monitoring active",
            subscribedAt = DateTime.UtcNow
        });
    }
}
