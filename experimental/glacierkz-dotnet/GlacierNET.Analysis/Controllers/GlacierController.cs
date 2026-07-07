using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using GlacierNET.Analysis.Models;
using GlacierNET.Analysis.Services;

namespace GlacierNET.Analysis.Controllers;

[ApiController]
[Route("api/[controller]")]
public class GlacierController : ControllerBase
{
    private readonly GlacierService _glacierService;
    private readonly NotificationService _notificationService;
    private readonly ILogger<GlacierController> _logger;

    public GlacierController(
        GlacierService glacierService,
        NotificationService notificationService,
        ILogger<GlacierController> logger)
    {
        _glacierService = glacierService;
        _notificationService = notificationService;
        _logger = logger;
    }

    [HttpGet]
    [ResponseCache(Duration = 300)]
    public async Task<ActionResult<PagedResult<Glacier>>> GetAll([FromQuery] int page = 1, [FromQuery] int pageSize = 50)
    {
        var result = await _glacierService.GetAllGlaciersAsync(page, pageSize);
        return Ok(result);
    }

    [HttpGet("{id:guid}")]
    public async Task<ActionResult<Glacier>> GetById(Guid id)
    {
        var glacier = await _glacierService.GetGlacierByIdAsync(id);
        if (glacier == null) return NotFound($"Glacier {id} not found");
        return Ok(glacier);
    }

    [HttpPost]
    [Authorize(Roles = "Admin,Researcher")]
    public async Task<ActionResult<Glacier>> Create([FromBody] Glacier glacier)
    {
        if (!ModelState.IsValid) return BadRequest(ModelState);

        var created = await _glacierService.CreateGlacierAsync(glacier);
        _logger.LogInformation("Glacier created: {Name} in {Region}", created.Name, created.Region);
        await _notificationService.NotifyGlacierCreatedAsync(created);

        return CreatedAtAction(nameof(GetById), new { id = created.Id }, created);
    }

    [HttpPut("{id:guid}")]
    [Authorize(Roles = "Admin,Researcher")]
    public async Task<ActionResult<Glacier>> Update(Guid id, [FromBody] Glacier glacier)
    {
        var updated = await _glacierService.UpdateGlacierAsync(id, glacier);
        if (updated == null) return NotFound($"Glacier {id} not found");

        await _notificationService.NotifyGlacierUpdatedAsync(updated);
        return Ok(updated);
    }

    [HttpDelete("{id:guid}")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> Delete(Guid id)
    {
        var deleted = await _glacierService.DeleteGlacierAsync(id);
        if (!deleted) return NotFound($"Glacier {id} not found");

        await _notificationService.NotifyGlacierDeletedAsync(id);
        return NoContent();
    }

    [HttpGet("search")]
    public async Task<ActionResult<PagedResult<Glacier>>> Search(
        [FromQuery] string? name = null,
        [FromQuery] string? region = null,
        [FromQuery] GlacierStatus? status = null,
        [FromQuery] double? minArea = null,
        [FromQuery] double? maxArea = null)
    {
        var result = await _glacierService.SearchGlaciersAsync(name, region, status, minArea, maxArea);
        return Ok(result);
    }

    [HttpGet("region/{region}")]
    public async Task<ActionResult<List<Glacier>>> GetByRegion(string region)
    {
        var glaciers = await _glacierService.GetGlaciersByRegionAsync(region);
        return Ok(glaciers);
    }

    [HttpGet("bbox")]
    public async Task<ActionResult<List<Glacier>>> GetByBoundingBox(
        [FromQuery] double minLat, [FromQuery] double minLng,
        [FromQuery] double maxLat, [FromQuery] double maxLng)
    {
        if (minLat > maxLat || minLng > maxLng)
            return BadRequest("Invalid bounding box coordinates");

        var glaciers = await _glacierService.GetGlaciersByBoundingBoxAsync(minLat, minLng, maxLat, maxLng);
        return Ok(glaciers);
    }

    [HttpGet("statistics")]
    public async Task<ActionResult<GlacierStatistics>> GetStatistics()
    {
        var stats = await _glacierService.GetGlacierStatisticsAsync();
        return Ok(stats);
    }

    [HttpGet("export/csv")]
    public async Task<IActionResult> ExportCsv()
    {
        var csv = await _glacierService.ExportToCsvAsync();
        return File(System.Text.Encoding.UTF8.GetBytes(csv), "text/csv", "glaciers.csv");
    }
}
