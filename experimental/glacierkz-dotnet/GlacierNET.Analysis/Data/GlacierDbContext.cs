using Microsoft.EntityFrameworkCore;
using GlacierNET.Analysis.Models;

namespace GlacierNET.Analysis.Data;

public class GlacierDbContext : DbContext
{
    public GlacierDbContext(DbContextOptions<GlacierDbContext> options) : base(options) { }

    public DbSet<Glacier> Glaciers => Set<Glacier>();
    public DbSet<SatelliteImage> SatelliteImages => Set<SatelliteImage>();
    public DbSet<AnalysisResult> AnalysisResults => Set<AnalysisResult>();
    public DbSet<TrendData> TrendDataPoints => Set<TrendData>();
    public DbSet<ProcessingTask> ProcessingTasks => Set<ProcessingTask>();
    public DbSet<User> Users => Set<User>();
    public DbSet<Report> Reports => Set<Report>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        modelBuilder.Entity<Glacier>(entity =>
        {
            entity.HasIndex(e => e.Name);
            entity.HasIndex(e => e.Region);
            entity.HasIndex(e => e.Status);
            entity.HasIndex(e => e.AreaKm2);
            entity.HasIndex(e => e.CenterPoint);
            entity.HasMany(e => e.SatelliteImages)
                .WithOne(s => s.Glacier)
                .HasForeignKey(s => s.GlacierId)
                .OnDelete(DeleteBehavior.Cascade);
            entity.HasMany(e => e.AnalysisResults)
                .WithOne(a => a.Glacier)
                .HasForeignKey(a => a.GlacierId)
                .OnDelete(DeleteBehavior.Cascade);
            entity.HasMany(e => e.TrendDataPoints)
                .WithOne(t => t.Glacier)
                .HasForeignKey(t => t.GlacierId)
                .OnDelete(DeleteBehavior.Cascade);
            entity.Property(e => e.Geometry).HasColumnType("geometry(MultiPolygon,4326)");
            entity.Property(e => e.CenterPoint).HasColumnType("geometry(Point,4326)");
        });

        modelBuilder.Entity<SatelliteImage>(entity =>
        {
            entity.HasIndex(e => e.GlacierId);
            entity.HasIndex(e => e.CaptureDate);
            entity.HasIndex(e => e.Source);
            entity.HasIndex(e => new { e.GlacierId, e.CaptureDate });
        });

        modelBuilder.Entity<AnalysisResult>(entity =>
        {
            entity.HasIndex(e => e.GlacierId);
            entity.HasIndex(e => e.AnalysisType);
            entity.HasIndex(e => e.AnalysisDate);
            entity.HasIndex(e => new { e.GlacierId, e.AnalysisType, e.AnalysisDate });
        });

        modelBuilder.Entity<TrendData>(entity =>
        {
            entity.HasIndex(e => e.GlacierId);
            entity.HasIndex(e => e.AnalysisType);
            entity.HasIndex(e => e.MeasurementDate);
            entity.HasIndex(e => new { e.GlacierId, e.AnalysisType, e.MeasurementDate });
        });

        modelBuilder.Entity<ProcessingTask>(entity =>
        {
            entity.HasIndex(e => e.Status);
            entity.HasIndex(e => e.CreatedAt);
            entity.HasIndex(e => new { e.Status, e.Priority });
        });

        modelBuilder.Entity<User>(entity =>
        {
            entity.HasIndex(e => e.Username).IsUnique();
            entity.HasIndex(e => e.Email).IsUnique();
            entity.HasIndex(e => e.ApiKey);
        });

        modelBuilder.Entity<Report>(entity =>
        {
            entity.HasIndex(e => e.ReportType);
            entity.HasIndex(e => e.GeneratedAt);
            entity.HasIndex(e => e.GeneratedBy);
        });

        modelBuilder.Entity<Glacier>().HasData(
            new Glacier
            {
                Id = Guid.Parse("11111111-1111-1111-1111-111111111111"),
                Name = "Petrov Glacier",
                LocalName = "Петров мұздығы",
                Region = "Tian Shan",
                Country = "Kazakhstan",
                MountainRange = "Trans-Ili Alatau",
                ElevationMin = 3200,
                ElevationMax = 4200,
                ElevationMean = 3700,
                AreaKm2 = 4.8,
                LengthKm = 3.2,
                Orientation = 180,
                Status = GlacierStatus.Retreating,
                Description = "Well-studied glacier in the Trans-Ili Alatau range",
                CreatedAt = DateTime.UtcNow,
                UpdatedAt = DateTime.UtcNow,
                IsActive = true
            },
            new Glacier
            {
                Id = Guid.Parse("22222222-2222-2222-2222-222222222222"),
                Name = "Manas Glacier",
                Region = "Tian Shan",
                Country = "Kazakhstan",
                MountainRange = "Kungey Alatau",
                ElevationMin = 3500,
                ElevationMax = 4500,
                ElevationMean = 4000,
                AreaKm2 = 6.2,
                LengthKm = 4.1,
                Orientation = 210,
                Status = GlacierStatus.Active,
                Description = "Large glacier with significant debris cover",
                CreatedAt = DateTime.UtcNow,
                UpdatedAt = DateTime.UtcNow,
                IsActive = true
            },
            new Glacier
            {
                Id = Guid.Parse("33333333-3333-3333-3333-333333333333"),
                Name = "Bogdanovich Glacier",
                Region = "Altai",
                Country = "Kazakhstan",
                MountainRange = "Belukha",
                ElevationMin = 2800,
                ElevationMax = 3900,
                ElevationMean = 3350,
                AreaKm2 = 3.1,
                LengthKm = 2.8,
                Orientation = 150,
                Status = GlacierStatus.Stable,
                Description = "Easternmost glacier in the Belukha massif",
                CreatedAt = DateTime.UtcNow,
                UpdatedAt = DateTime.UtcNow,
                IsActive = true
            }
        );
    }

    public override Task<int> SaveChangesAsync(CancellationToken cancellationToken = default)
    {
        foreach (var entry in ChangeTracker.Entries<Glacier>().Where(e => e.State == EntityState.Modified))
        {
            entry.Entity.UpdatedAt = DateTime.UtcNow;
        }
        foreach (var entry in ChangeTracker.Entries<ProcessingTask>().Where(e => e.State == EntityState.Modified))
        {
            entry.Entity.UpdatedAt = DateTime.UtcNow;
        }
        return base.SaveChangesAsync(cancellationToken);
    }
}
