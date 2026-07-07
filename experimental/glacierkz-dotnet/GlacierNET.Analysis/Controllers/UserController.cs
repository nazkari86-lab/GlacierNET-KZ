using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Microsoft.IdentityModel.Tokens;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using GlacierNET.Analysis.Data;
using GlacierNET.Analysis.DTOs;
using GlacierNET.Analysis.Models;
using Microsoft.EntityFrameworkCore;

namespace GlacierNET.Analysis.Controllers;

[ApiController]
[Route("api/[controller]")]
public class UserController : ControllerBase
{
    private readonly GlacierDbContext _context;
    private readonly IConfiguration _configuration;
    private readonly ILogger<UserController> _logger;

    public UserController(
        GlacierDbContext context,
        IConfiguration configuration,
        ILogger<UserController> logger)
    {
        _context = context;
        _configuration = configuration;
        _logger = logger;
    }

    [HttpPost("login")]
    public async Task<ActionResult<LoginResponse>> Login([FromBody] LoginRequest request)
    {
        var user = await _context.Users.FirstOrDefaultAsync(u => u.Email == request.Email && u.IsActive);
        if (user == null) return Unauthorized("Invalid credentials");

        if (!BCrypt.Net.BCrypt.Verify(request.Password, user.PasswordHash))
            return Unauthorized("Invalid credentials");

        user.LastLoginAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();

        var token = GenerateJwtToken(user);

        return Ok(new LoginResponse
        {
            Token = token,
            ExpiresAt = DateTime.UtcNow.AddHours(8),
            User = new UserInfo
            {
                Id = user.Id,
                Username = user.Username,
                Email = user.Email,
                Role = user.Role.ToString(),
                Organization = user.Organization
            }
        });
    }

    [HttpPost("register")]
    public async Task<ActionResult<UserProfileDto>> Register([FromBody] RegisterRequest request)
    {
        if (await _context.Users.AnyAsync(u => u.Email == request.Email))
            return BadRequest("Email already registered");

        var user = new User
        {
            Username = request.Username,
            Email = request.Email,
            PasswordHash = BCrypt.Net.BCrypt.HashPassword(request.Password),
            Salt = string.Empty,
            Role = request.Role ?? UserRole.Viewer,
            Organization = request.Organization,
            IsActive = true
        };

        _context.Users.Add(user);
        await _context.SaveChangesAsync();

        _logger.LogInformation("New user registered: {Username}", user.Username);
        return CreatedAtAction(nameof(GetProfile), new { id = user.Id }, ToProfileDto(user));
    }

    [HttpGet("profile")]
    [Authorize]
    public async Task<ActionResult<UserProfileDto>> GetProfile()
    {
        var userId = GetUserIdFromClaims();
        var user = await _context.Users.FindAsync(userId);
        if (user == null) return NotFound("User not found");
        return Ok(ToProfileDto(user));
    }

    [HttpGet]
    [Authorize(Roles = "Admin")]
    public async Task<ActionResult<List<UserListDto>>> GetAll()
    {
        var users = await _context.Users
            .Where(u => u.IsActive)
            .OrderBy(u => u.Username)
            .ToListAsync();
        return Ok(users.Select(ToListDto).ToList());
    }

    [HttpPut("{id:guid}")]
    [Authorize]
    public async Task<IActionResult> UpdateProfile(Guid id, [FromBody] UserUpdateRequest request)
    {
        var userId = GetUserIdFromClaims();
        if (userId != id && !User.IsInRole("Admin"))
            return Forbid();

        var user = await _context.Users.FindAsync(id);
        if (user == null) return NotFound("User not found");

        if (!string.IsNullOrEmpty(request.Username)) user.Username = request.Username;
        if (!string.IsNullOrEmpty(request.Email)) user.Email = request.Email;
        if (!string.IsNullOrEmpty(request.Organization)) user.Organization = request.Organization;

        await _context.SaveChangesAsync();
        return Ok(ToProfileDto(user));
    }

    [HttpPost("{id:guid}/deactivate")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> Deactivate(Guid id)
    {
        var user = await _context.Users.FindAsync(id);
        if (user == null) return NotFound("User not found");

        user.IsActive = false;
        await _context.SaveChangesAsync();
        return NoContent();
    }

    private Guid GetUserIdFromClaims()
    {
        var claim = User.FindFirst(ClaimTypes.NameIdentifier);
        if (claim == null || !Guid.TryParse(claim.Value, out var userId))
            throw new UnauthorizedAccessException("Invalid user ID in token");
        return userId;
    }

    private string GenerateJwtToken(User user)
    {
        var jwtSettings = _configuration.GetSection("JwtSettings");
        var secretKey = jwtSettings["SecretKey"]
            ?? _configuration["JWT_SECRET"]
            ?? Environment.GetEnvironmentVariable("JWT_SECRET");
        if (string.IsNullOrWhiteSpace(secretKey) || secretKey.Length < 32)
        {
            throw new InvalidOperationException(
                "JWT secret not configured. Set JwtSettings:SecretKey or JWT_SECRET (minimum 32 characters).");
        }
        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secretKey));
        var credentials = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

        var claims = new[]
        {
            new Claim(ClaimTypes.NameIdentifier, user.Id.ToString()),
            new Claim(ClaimTypes.Name, user.Username),
            new Claim(ClaimTypes.Email, user.Email),
            new Claim(ClaimTypes.Role, user.Role.ToString()),
            new Claim("Organization", user.Organization ?? string.Empty)
        };

        var token = new JwtSecurityToken(
            issuer: jwtSettings["Issuer"],
            audience: jwtSettings["Audience"],
            claims: claims,
            expires: DateTime.UtcNow.AddHours(8),
            signingCredentials: credentials);

        return new JwtSecurityTokenHandler().WriteToken(token);
    }

    private static UserProfileDto ToProfileDto(User user) => new()
    {
        Id = user.Id,
        Username = user.Username,
        Email = user.Email,
        FullName = user.FullName,
        Organization = user.Organization,
        Role = user.Role,
        IsActive = user.IsActive,
        LastLoginAt = user.LastLoginAt,
        CreatedAt = user.CreatedAt,
        LoginCount = user.LoginCount
    };

    private static UserListDto ToListDto(User user) => new()
    {
        Id = user.Id,
        Username = user.Username,
        Email = user.Email,
        Organization = user.Organization,
        Role = user.Role,
        IsActive = user.IsActive,
        LastLoginAt = user.LastLoginAt,
        CreatedAt = user.CreatedAt
    };
}

public class LoginRequest
{
    public string Email { get; set; } = string.Empty;
    public string Password { get; set; } = string.Empty;
}

public class LoginResponse
{
    public string Token { get; set; } = string.Empty;
    public DateTime ExpiresAt { get; set; }
    public UserInfo User { get; set; } = new();
}

public class UserInfo
{
    public Guid Id { get; set; }
    public string Username { get; set; } = string.Empty;
    public string Email { get; set; } = string.Empty;
    public string Role { get; set; } = string.Empty;
    public string? Organization { get; set; }
}

public class RegisterRequest
{
    public string Username { get; set; } = string.Empty;
    public string Email { get; set; } = string.Empty;
    public string Password { get; set; } = string.Empty;
    public UserRole? Role { get; set; }
    public string? Organization { get; set; }
}

public class UserUpdateRequest
{
    public string? Username { get; set; }
    public string? Email { get; set; }
    public string? Organization { get; set; }
}
