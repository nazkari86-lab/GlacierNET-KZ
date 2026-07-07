using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using GlacierNET.Analysis.Models;
using GlacierNET.Analysis.Services;

namespace GlacierNET.Analysis.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ReportController : ControllerBase
{
    private readonly ReportService _reportService;
    private readonly NotificationService _notificationService;
    private readonly ILogger<ReportController> _logger;

    public ReportController(
        ReportService reportService,
        NotificationService notificationService,
        ILogger<ReportController> logger)
    {
        _reportService = reportService;
        _notificationService = notificationService;
        _logger = logger;
    }

    [HttpGet]
    public async Task<ActionResult<PagedResult<Report>>> GetAll([FromQuery] int page = 1, [FromQuery] int pageSize = 20)
    {
        var result = await _reportService.GetAllReportsAsync(page, pageSize);
        return Ok(result);
    }

    [HttpGet("{id:guid}")]
    public async Task<ActionResult<Report>> GetById(Guid id)
    {
        var report = await _reportService.GetReportByIdAsync(id);
        if (report == null) return NotFound($"Report {id} not found");
        return Ok(report);
    }

    [HttpGet("{id:guid}/html")]
    public async Task<IActionResult> GetHtml(Guid id)
    {
        var html = await _reportService.GenerateHtmlReportAsync(id);
        if (string.IsNullOrEmpty(html)) return NotFound($"Report {id} not found");
        return Content(html, "text/html");
    }

    [HttpPost("generate")]
    [Authorize(Roles = "Admin,Researcher")]
    public async Task<ActionResult<Report>> GenerateReport([FromBody] ReportGenerationRequest request)
    {
        var report = await _reportService.GenerateReportAsync(request);
        _logger.LogInformation("Report generated: {Title}", report.Title);
        await _notificationService.BroadcastStatusUpdateAsync(new
        {
            type = "report_generated",
            reportId = report.Id,
            title = report.Title,
            format = report.Format.ToString()
        });
        return CreatedAtAction(nameof(GetById), new { id = report.Id }, report);
    }

    [HttpGet("annual/{year:int}")]
    public async Task<ActionResult<List<Report>>> GetAnnualReports(int year)
    {
        var reports = await _reportService.GetAnnualReportsAsync(year);
        return Ok(reports);
    }

    [HttpGet("type/{reportType}")]
    public async Task<ActionResult<List<Report>>> GetByType(ReportType reportType)
    {
        var reports = await _reportService.GetReportsByTypeAsync(reportType);
        return Ok(reports);
    }

    [HttpGet("recent")]
    public async Task<ActionResult<List<Report>>> GetRecent([FromQuery] int limit = 10)
    {
        var reports = await _reportService.GetRecentReportsAsync(limit);
        return Ok(reports);
    }

    [HttpDelete("{id:guid}")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> Delete(Guid id)
    {
        var deleted = await _reportService.DeleteReportAsync(id);
        if (!deleted) return NotFound($"Report {id} not found");
        return NoContent();
    }
}
