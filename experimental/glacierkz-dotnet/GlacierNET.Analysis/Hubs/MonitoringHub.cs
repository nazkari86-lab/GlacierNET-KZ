using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.SignalR;

namespace GlacierNET.Analysis.Hubs;

public class MonitoringHub : Hub
{
    private readonly ILogger<MonitoringHub> _logger;

    public MonitoringHub(ILogger<MonitoringHub> logger)
    {
        _logger = logger;
    }

    public override async Task OnConnectedAsync()
    {
        _logger.LogInformation("Client connected to MonitoringHub: {ConnectionId}", Context.ConnectionId);
        await Groups.AddToGroupAsync(Context.ConnectionId, "Monitoring");
        await base.OnConnectedAsync();
    }

    public override async Task OnDisconnectedAsync(Exception? exception)
    {
        _logger.LogInformation("Client disconnected from MonitoringHub: {ConnectionId}", Context.ConnectionId);
        await Groups.RemoveFromGroupAsync(Context.ConnectionId, "Monitoring");
        await base.OnDisconnectedAsync(exception);
    }

    public async Task SubscribeToGlacier(Guid glacierId)
    {
        await Groups.AddToGroupAsync(Context.ConnectionId, $"glacier-{glacierId}");
        _logger.LogDebug("Client {ConnectionId} subscribed to glacier {GlacierId}", Context.ConnectionId, glacierId);
    }

    public async Task UnsubscribeFromGlacier(Guid glacierId)
    {
        await Groups.RemoveFromGroupAsync(Context.ConnectionId, $"glacier-{glacierId}");
    }

    public async Task SubscribeToRegion(string region)
    {
        await Groups.AddToGroupAsync(Context.ConnectionId, $"region-{region}");
    }

    public async Task SendHeartbeat()
    {
        await Clients.Caller.SendAsync("HeartbeatResponse", new
        {
            serverTime = DateTime.UtcNow,
            connectionId = Context.ConnectionId
        });
    }

    public async Task RequestCurrentStatus()
    {
        await Clients.Caller.SendAsync("StatusUpdate", new
        {
            status = "connected",
            serverTime = DateTime.UtcNow,
            message = "Real-time monitoring active"
        });
    }
}
