using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace GlacierNET.Analysis.Models;

[Table("users")]
public class User
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; } = Guid.NewGuid();

    [Required]
    [MaxLength(100)]
    [Column("username")]
    public string Username { get; set; } = string.Empty;

    [Required]
    [MaxLength(200)]
    [Column("email")]
    public string Email { get; set; } = string.Empty;

    [Required]
    [MaxLength(200)]
    [Column("password_hash")]
    public string PasswordHash { get; set; } = string.Empty;

    [MaxLength(200)]
    [Column("salt")]
    public string Salt { get; set; } = string.Empty;

    [MaxLength(100)]
    [Column("full_name")]
    public string? FullName { get; set; }

    [MaxLength(200)]
    [Column("organization")]
    public string? Organization { get; set; }

    [Required]
    [Column("role")]
    public UserRole Role { get; set; } = UserRole.Researcher;

    [Column("is_active")]
    public bool IsActive { get; set; } = true;

    [Column("is_admin")]
    public bool IsAdmin { get; set; }

    [Column("last_login_at")]
    public DateTime? LastLoginAt { get; set; }

    [Column("created_at")]
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [Column("updated_at")]
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;

    [Column("login_count")]
    public int LoginCount { get; set; }

    [MaxLength(500)]
    [Column("preferences_json")]
    public string? PreferencesJson { get; set; }

    [MaxLength(2000)]
    [Column("api_key")]
    public string? ApiKey { get; set; }

    [Column("api_key_expires_at")]
    public DateTime? ApiKeyExpiresAt { get; set; }

    [NotMapped]
    public bool HasValidApiKey => !string.IsNullOrEmpty(ApiKey) &&
        (!ApiKeyExpiresAt.HasValue || ApiKeyExpiresAt.Value > DateTime.UtcNow);

    [NotMapped]
    public bool HasExpiredApiKey => ApiKeyExpiresAt.HasValue && ApiKeyExpiresAt.Value <= DateTime.UtcNow;
}
