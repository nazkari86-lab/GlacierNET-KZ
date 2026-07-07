using System.Text;
using System.Text.Json.Serialization;
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi.Models;
using GlacierNET.Analysis.Data;
using GlacierNET.Analysis.Grpc;
using GlacierNET.Analysis.Hubs;
using GlacierNET.Analysis.Services;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers().AddJsonOptions(options =>
{
    options.JsonSerializerOptions.ReferenceHandler = ReferenceHandler.IgnoreCycles;
    options.JsonSerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull;
});

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo
    {
        Title = "GlacierNET-KZ Analysis API",
        Version = "v1",
        Description = "Analytics platform for glacier monitoring in Kazakhstan",
        Contact = new OpenApiContact { Name = "GlacierNET Team", Email = "team@glacierkz.kz" }
    });
    c.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
    {
        Name = "Authorization",
        Type = SecuritySchemeType.Http,
        Scheme = "bearer",
        BearerFormat = "JWT",
        In = ParameterLocation.Header,
        Description = "JWT token for authentication"
    });
    c.AddSecurityRequirement(new OpenApiSecurityRequirement
    {
        {
            new OpenApiSecurityScheme
            {
                Reference = new OpenApiReference { Type = ReferenceType.SecurityScheme, Id = "Bearer" }
            },
            Array.Empty<string>()
        }
    });
});

var connectionString = builder.Configuration.GetConnectionString("DefaultConnection");
builder.Services.AddDbContext<GlacierDbContext>(options =>
    options.UseNpgsql(connectionString, npgsql =>
    {
        npgsql.UseNetTopologySuite();
        npgsql.MigrationsAssembly("GlacierNET.Analysis");
    }));

builder.Services.AddStackExchangeRedisCache(options =>
{
    options.Configuration = builder.Configuration.GetConnectionString("Redis");
    options.InstanceName = "GlacierNET_";
});

builder.Services.AddSignalR(options =>
{
    options.EnableDetailedErrors = true;
    options.KeepAliveInterval = TimeSpan.FromSeconds(15);
    options.ClientTimeoutInterval = TimeSpan.FromSeconds(30);
    options.MaximumReceiveMessageSize = 1024 * 1024;
}).AddJsonProtocol(options =>
{
    options.PayloadSerializerOptions.PropertyNamingPolicy = System.Text.Json.JsonNamingPolicy.CamelCase;
});

var jwtSecretKey = builder.Configuration["JwtSettings:SecretKey"]
    ?? builder.Configuration["JWT_SECRET"]
    ?? Environment.GetEnvironmentVariable("JWT_SECRET");
if (string.IsNullOrWhiteSpace(jwtSecretKey) || jwtSecretKey.Length < 32)
{
    throw new InvalidOperationException(
        "JWT secret not configured. Set JwtSettings:SecretKey or JWT_SECRET (minimum 32 characters).");
}
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = builder.Configuration["JwtSettings:Issuer"],
            ValidAudience = builder.Configuration["JwtSettings:Audience"],
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtSecretKey)),
            ClockSkew = TimeSpan.FromMinutes(1)
        };
    });
builder.Services.AddAuthorization();

builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowConfiguredOrigins", policy =>
    {
        var origins = builder.Configuration.GetSection("Cors:AllowedOrigins").Get<string[]>() ?? [];
        policy.WithOrigins(origins)
            .AllowAnyHeader()
            .AllowAnyMethod()
            .AllowCredentials();
    });
});

builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
    options.AddFixedWindowLimiter("fixed", limiterOptions =>
    {
        limiterOptions.PermitLimit = 100;
        limiterOptions.Window = TimeSpan.FromMinutes(1);
        limiterOptions.QueueProcessingOrder = QueueProcessingOrder.OldestFirst;
        limiterOptions.QueueLimit = 10;
    });
    options.AddTokenBucketLimiter("token", limiterOptions =>
    {
        limiterOptions.TokenLimit = 50;
        limiterOptions.ReplenishmentPeriod = TimeSpan.FromSeconds(10);
        limiterOptions.TokensPerPeriod = 10;
        limiterOptions.AutoReplenishment = true;
    });
});

builder.Services.AddScoped<GlacierService>();
builder.Services.AddScoped<AnalysisService>();
builder.Services.AddScoped<TrendService>();
builder.Services.AddScoped<ExportService>();
builder.Services.AddScoped<CacheService>();
builder.Services.AddScoped<ReportService>();
builder.Services.AddScoped<NotificationService>();
builder.Services.AddScoped<ProcessingTaskService>();

builder.Services.AddGrpcClient<GlacierAnalysis.GlacierAnalysisClient>(options =>
{
    options.Address = new Uri(builder.Configuration["GrpcServices:PythonMlService"]!);
}).ConfigureChannel(options =>
{
    options.Credentials = Grpc.Core.ChannelCredentials.Insecure;
});

builder.Services.AddHealthChecks()
    .AddDbContextCheck<GlacierDbContext>()
    .AddRedis(builder.Configuration.GetConnectionString("Redis")!);

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI(c => c.SwaggerEndpoint("/swagger/v1/swagger.json", "GlacierNET-KZ API v1"));
}

app.UseHttpsRedirection();
app.UseCors("AllowConfiguredOrigins");
app.UseRateLimiter();
app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();
app.MapHub<MonitoringHub>("/hubs/monitoring");
app.MapHub<TaskProgressHub>("/hubs/tasks");
app.MapHealthChecks("/health");

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<GlacierDbContext>();
    await db.Database.EnsureCreatedAsync();
    await SeedData.InitializeAsync(scope.ServiceProvider);
}

await app.RunAsync();
