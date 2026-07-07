using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using GlacierNET.Analysis.Models;
using GlacierNET.Analysis.Services;

namespace GlacierNET.Analysis.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AnalysisController : ControllerBase
{
    private readonly AnalysisService _analysisService;
    private readonly NotificationService _notificationService;
    private readonly ILogger<AnalysisController> _logger;

    public AnalysisController(
        AnalysisService analysisService,
        NotificationService notificationService,
        ILogger<AnalysisController> logger)
    {
        _analysisService = analysisService;
        _notificationService = notificationService;
        _logger = logger;
    }

    [HttpGet]
    public async Task<ActionResult<PagedResult<AnalysisResult>>> GetAll([FromQuery] int page = 1, [FromQuery] int pageSize = 50)
    {
        var result = await _analysisService.GetAllResultsAsync(page, pageSize);
        return Ok(result);
    }

    [HttpGet("{id:guid}")]
    public async Task<ActionResult<AnalysisResult>> GetById(Guid id)
    {
        var result = await _analysisService.GetResultByIdAsync(id);
        if (result == null) return NotFound($"Analysis result {id} not found");
        return Ok(result);
    }

    [HttpPost]
    [Authorize(Roles = "Admin,Researcher")]
    public async Task<ActionResult<AnalysisResult>> Create([FromBody] AnalysisResult analysis)
    {
        if (!ModelState.IsValid) return BadRequest(ModelState);

        var created = await _analysisService.CreateResultAsync(analysis);
        _logger.LogInformation("Analysis created: {Type} for glacier {GlacierId}",
            created.AnalysisType, created.GlacierId);
        await _notificationService.NotifyAnalysisCompletedAsync(created);

        return CreatedAtAction(nameof(GetById), new { id = created.Id }, created);
    }

    [HttpGet("glacier/{glacierId:guid}")]
    public async Task<ActionResult<List<AnalysisResult>>> GetByGlacier(Guid glacierId, [FromQuery] int? limit = null)
    {
        var results = await _analysisService.GetResultsByGlacierAsync(glacierId, limit);
        return Ok(results);
    }

    [HttpGet("glacier/{glacierId:guid}/type/{analysisType}")]
    public async Task<ActionResult<List<AnalysisResult>>> GetByGlacierAndType(Guid glacierId, AnalysisType analysisType)
    {
        var results = await _analysisService.GetResultsByGlacierAndTypeAsync(glacierId, analysisType);
        return Ok(results);
    }

    [HttpGet("anomalies")]
    public async Task<ActionResult<List<AnalysisResult>>> GetAnomalies([FromQuery] int limit = 100)
    {
        var anomalies = await _analysisService.GetAnomaliesAsync(limit);
        return Ok(anomalies);
    }

    [HttpGet("summary/{glacierId:guid}")]
    public async Task<ActionResult<AnalysisSummary>> GetSummary(Guid glacierId)
    {
        var summary = await _analysisService.GetAnalysisSummaryAsync(glacierId);
        if (summary == null) return NotFound($"No analysis data for glacier {glacierId}");
        return Ok(summary);
    }

    [HttpGet("compare")]
    public async Task<ActionResult<AnalysisComparison>> Compare(
        [FromQuery] Guid glacierId1,
        [FromQuery] Guid glacierId2,
        [FromQuery] AnalysisType type)
    {
        var comparison = await _analysisService.CompareGlaciersAsync(glacierId1, glacierId2, type);
        return Ok(comparison);
    }

    [HttpGet("mass-balance-trend/{glacierId:guid}")]
    public async Task<ActionResult<MassBalanceTrend>> GetMassBalanceTrend(Guid glacierId, [FromQuery] int years = 10)
    {
        var trend = await _analysisService.GetMassBalanceTrendAsync(glacierId, years);
        if (trend == null) return NotFound($"No mass balance data for glacier {glacierId}");
        return Ok(trend);
    }

    [HttpGet("recent")]
    public async Task<ActionResult<List<AnalysisResult>>> GetRecent([FromQuery] int limit = 20)
    {
        var results = await _analysisService.GetRecentResultsAsync(limit);
        return Ok(results);
    }

    [HttpDelete("{id:guid}")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> Delete(Guid id)
    {
        var deleted = await _analysisService.DeleteResultAsync(id);
        if (!deleted) return NotFound($"Analysis result {id} not found");
        return NoContent();
    }
}
