using Microsoft.EntityFrameworkCore;
using GlacierNET.Analysis.Data;
using GlacierNET.Analysis.Services;
using GlacierNET.Analysis.Hubs;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddRazorPages();
builder.Services.AddServerSideBlazor()
    .AddHubOptions(options =>
    {
        options.MaximumReceiveMessageSize = 1024 * 1024;
        options.ClientTimeoutInterval = TimeSpan.FromSeconds(60);
        options.KeepAliveInterval = TimeSpan.FromSeconds(15);
    });

builder.Services.AddHttpClient("GlacierApi", client =>
{
    client.BaseAddress = new Uri(builder.Configuration["ApiSettings:BaseUrl"] ?? "https://localhost:5001");
    client.Timeout = TimeSpan.FromSeconds(30);
});

builder.Services.AddDbContext<GlacierDbContext>(options =>
    options.UseNpgsql(
        builder.Configuration.GetConnectionString("DefaultConnection"),
        npgsql => npgsql.MigrationsAssembly("GlacierNET.Analysis")));

builder.Services.AddSignalR();

builder.Services.AddScoped<GlacierService>();
builder.Services.AddScoped<AnalysisService>();
builder.Services.AddScoped<TrendService>();
builder.Services.AddScoped<ReportService>();
builder.Services.AddScoped<ExportService>();
builder.Services.AddScoped<CacheService>();
builder.Services.AddScoped<NotificationService>();
builder.Services.AddScoped<ProcessingTaskService>();
builder.Services.AddScoped(sp =>
{
    var httpClient = sp.GetRequiredService<IHttpClientFactory>().CreateClient("GlacierApi");
    return new ApiClient(httpClient);
});

builder.Services.AddResponseCompression();

var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseStaticFiles();
app.UseRouting();
app.UseResponseCompression();

app.MapBlazorHub();
app.MapHub<MonitoringHub>("/hubs/monitoring");
app.MapHub<TaskProgressHub>("/hubs/tasks");
app.MapFallbackToPage("/_Host");

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<GlacierDbContext>();
    if (await db.Database.CanConnectAsync())
    {
        await db.Database.MigrateAsync();
    }
}

app.Run();
