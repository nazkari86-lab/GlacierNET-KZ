using Microsoft.AspNetCore.SignalR.Client;
using Microsoft.Extensions.Logging;

namespace GlacierNET.Blazor.Services;

public class SignalRService : IAsyncDisposable
{
    private HubConnection? _monitoringHub;
    private HubConnection? _taskHub;
    private readonly ILogger<SignalRService> _logger;
    private readonly string _monitoringUrl;
    private readonly string _taskUrl;

    public event Action<object>? OnGlacierUpdated;
    public event Action<object>? OnAnalysisCompleted;
    public event Action<object>? OnAnomalyDetected;
    public event Action<object>? OnSystemAlert;
    public event Action<object>? OnTaskProgress;
    public event Action<object>? OnTaskCompleted;
    public event Action<object>? OnTaskFailed;
    public event Action<object>? OnStatusUpdate;
    public event Action<Exception>? OnConnectionError;
    public event Action<string>? OnConnectionStateChanged;

    public bool IsMonitoringConnected => _monitoringHub?.State == HubConnectionState.Connected;
    public bool IsTaskConnected => _taskHub?.State == HubConnectionState.Connected;

    public SignalRService(ILogger<SignalRService> logger, string baseUrl = "https://localhost:5001")
    {
        _logger = logger;
        _monitoringUrl = $"{baseUrl}/hubs/monitoring";
        _taskUrl = $"{baseUrl}/hubs/tasks";
    }

    public async Task StartMonitoringAsync()
    {
        try
        {
            _monitoringHub = new HubConnectionBuilder()
                .WithUrl(_monitoringUrl)
                .WithAutomaticReconnect(new[] { TimeSpan.Zero, TimeSpan.FromSeconds(2), TimeSpan.FromSeconds(5), TimeSpan.FromSeconds(10) })
                .ConfigureLogging(logging => logging.SetMinimumLevel(LogLevel.Information))
                .Build();

            _monitoringHub.On<object>("GlacierUpdated", data =>
            {
                _logger.LogDebug("Glacier updated received");
                OnGlacierUpdated?.Invoke(data);
            });

            _monitoringHub.On<object>("GlacierCreated", data =>
            {
                _logger.LogDebug("Glacier created received");
                OnStatusUpdate?.Invoke(data);
            });

            _monitoringHub.On<object>("GlacierDeleted", data =>
            {
                _logger.LogDebug("Glacier deleted received");
                OnStatusUpdate?.Invoke(data);
            });

            _monitoringHub.On<object>("AnalysisCompleted", data =>
            {
                _logger.LogDebug("Analysis completed received");
                OnAnalysisCompleted?.Invoke(data);
            });

            _monitoringHub.On<object>("AnomalyDetected", data =>
            {
                _logger.LogWarning("Anomaly detected received");
                OnAnomalyDetected?.Invoke(data);
            });

            _monitoringHub.On<object>("SystemAlert", data =>
            {
                _logger.LogWarning("System alert received");
                OnSystemAlert?.Invoke(data);
            });

            _monitoringHub.On<object>("StatusUpdate", data =>
            {
                OnStatusUpdate?.Invoke(data);
            });

            _monitoringHub.Reconnecting += exception =>
            {
                _logger.LogWarning("Monitoring hub reconnecting: {Message}", exception?.Message);
                OnConnectionStateChanged?.Invoke("Reconnecting");
                return Task.CompletedTask;
            };

            _monitoringHub.Reconnected += connectionId =>
            {
                _logger.LogInformation("Monitoring hub reconnected: {ConnectionId}", connectionId);
                OnConnectionStateChanged?.Invoke("Connected");
                return Task.CompletedTask;
            };

            _monitoringHub.Closed += exception =>
            {
                _logger.LogWarning("Monitoring hub closed: {Message}", exception?.Message);
                OnConnectionStateChanged?.Invoke("Disconnected");
                return Task.CompletedTask;
            };

            await _monitoringHub.StartAsync();
            OnConnectionStateChanged?.Invoke("Connected");
            _logger.LogInformation("Monitoring hub connected");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to start monitoring hub");
            OnConnectionError?.Invoke(ex);
        }
    }

    public async Task StartTaskMonitoringAsync()
    {
        try
        {
            _taskHub = new HubConnectionBuilder()
                .WithUrl(_taskUrl)
                .WithAutomaticReconnect(new[] { TimeSpan.Zero, TimeSpan.FromSeconds(2), TimeSpan.FromSeconds(5) })
                .ConfigureLogging(logging => logging.SetMinimumLevel(LogLevel.Information))
                .Build();

            _taskHub.On<object>("TaskProgress", data =>
            {
                _logger.LogDebug("Task progress received");
                OnTaskProgress?.Invoke(data);
            });

            _taskHub.On<object>("TaskCompleted", data =>
            {
                _logger.LogInformation("Task completed received");
                OnTaskCompleted?.Invoke(data);
            });

            _taskHub.On<object>("TaskFailed", data =>
            {
                _logger.LogWarning("Task failed received");
                OnTaskFailed?.Invoke(data);
            });

            _taskHub.Reconnecting += exception =>
            {
                _logger.LogWarning("Task hub reconnecting: {Message}", exception?.Message);
                return Task.CompletedTask;
            };

            await _taskHub.StartAsync();
            _logger.LogInformation("Task hub connected");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to start task hub");
            OnConnectionError?.Invoke(ex);
        }
    }

    public async Task SubscribeToGlacierAsync(Guid glacierId)
    {
        if (_monitoringHub?.State == HubConnectionState.Connected)
        {
            await _monitoringHub.InvokeAsync("SubscribeToGlacier", glacierId);
            _logger.LogDebug("Subscribed to glacier {GlacierId}", glacierId);
        }
    }

    public async Task UnsubscribeFromGlacierAsync(Guid glacierId)
    {
        if (_monitoringHub?.State == HubConnectionState.Connected)
        {
            await _monitoringHub.InvokeAsync("UnsubscribeFromGlacier", glacierId);
        }
    }

    public async Task WatchTaskAsync(Guid taskId)
    {
        if (_taskHub?.State == HubConnectionState.Connected)
        {
            await _taskHub.InvokeAsync("WatchTask", taskId);
        }
    }

    public async Task StopWatchingTaskAsync(Guid taskId)
    {
        if (_taskHub?.State == HubConnectionState.Connected)
        {
            await _taskHub.InvokeAsync("StopWatchingTask", taskId);
        }
    }

    public async Task SendHeartbeatAsync()
    {
        if (_monitoringHub?.State == HubConnectionState.Connected)
        {
            await _monitoringHub.InvokeAsync("SendHeartbeat");
        }
    }

    public async Task StopAllAsync()
    {
        if (_monitoringHub != null)
        {
            await _monitoringHub.StopAsync();
            await _monitoringHub.DisposeAsync();
            _monitoringHub = null;
        }

        if (_taskHub != null)
        {
            await _taskHub.StopAsync();
            await _taskHub.DisposeAsync();
            _taskHub = null;
        }
    }

    public async ValueTask DisposeAsync()
    {
        await StopAllAsync();
        GC.SuppressFinalize(this);
    }
}
