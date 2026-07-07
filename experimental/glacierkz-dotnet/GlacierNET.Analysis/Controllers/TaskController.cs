using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using GlacierNET.Analysis.Models;
using GlacierNET.Analysis.Services;
using GlacierNET.Analysis.Data;

namespace GlacierNET.Analysis.Controllers;

[ApiController]
[Route("api/[controller]")]
public class TaskController : ControllerBase
{
    private readonly ProcessingTaskService _taskService;
    private readonly NotificationService _notificationService;
    private readonly ILogger<TaskController> _logger;

    public TaskController(
        ProcessingTaskService taskService,
        NotificationService notificationService,
        ILogger<TaskController> logger)
    {
        _taskService = taskService;
        _notificationService = notificationService;
        _logger = logger;
    }

    [HttpGet]
    public async Task<ActionResult<PagedResult<ProcessingTask>>> GetAll([FromQuery] int page = 1, [FromQuery] int pageSize = 20)
    {
        var result = await _taskService.GetAllTasksAsync(page, pageSize);
        return Ok(result);
    }

    [HttpGet("{id:guid}")]
    public async Task<ActionResult<ProcessingTask>> GetById(Guid id)
    {
        var task = await _taskService.GetTaskByIdAsync(id);
        if (task == null) return NotFound($"Task {id} not found");
        return Ok(task);
    }

    [HttpPost]
    [Authorize(Roles = "Admin,Researcher")]
    public async Task<ActionResult<ProcessingTask>> Create([FromBody] ProcessingTask task)
    {
        var created = await _taskService.CreateTaskAsync(task);
        _logger.LogInformation("Task created: {Name} by user {UserId}", created.Name, created.UserId);
        return CreatedAtAction(nameof(GetById), new { id = created.Id }, created);
    }

    [HttpPost("{id:guid}/start")]
    [Authorize(Roles = "Admin,Researcher")]
    public async Task<IActionResult> Start(Guid id)
    {
        var started = await _taskService.StartTaskAsync(id);
        if (started == null) return NotFound($"Task {id} not found");

        await _notificationService.NotifyTaskProgressAsync(started);
        return Ok(started);
    }

    [HttpPost("{id:guid}/pause")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> Pause(Guid id)
    {
        var paused = await _taskService.PauseTaskAsync(id);
        if (paused == null) return NotFound($"Task {id} not found");
        return Ok(paused);
    }

    [HttpPost("{id:guid}/resume")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> Resume(Guid id)
    {
        var resumed = await _taskService.ResumeTaskAsync(id);
        if (resumed == null) return NotFound($"Task {id} not found");
        return Ok(resumed);
    }

    [HttpPost("{id:guid}/cancel")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> Cancel(Guid id)
    {
        var cancelled = await _taskService.CancelTaskAsync(id);
        if (cancelled == null) return NotFound($"Task {id} not found");
        return Ok(cancelled);
    }

    [HttpGet("status/{status}")]
    public async Task<ActionResult<List<ProcessingTask>>> GetByStatus(TaskStatusType status)
    {
        var tasks = await _taskService.GetTasksByStatusAsync(status);
        return Ok(tasks);
    }

    [HttpGet("active")]
    public async Task<ActionResult<List<ProcessingTask>>> GetActive()
    {
        var tasks = await _taskService.GetActiveTasksAsync();
        return Ok(tasks);
    }

    [HttpGet("statistics")]
    public async Task<ActionResult<TaskStatistics>> GetStatistics()
    {
        var stats = await _taskService.GetTaskStatisticsAsync();
        return Ok(stats);
    }

    [HttpDelete("{id:guid}")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> Delete(Guid id)
    {
        var deleted = await _taskService.DeleteTaskAsync(id);
        if (!deleted) return NotFound($"Task {id} not found");
        return NoContent();
    }
}
