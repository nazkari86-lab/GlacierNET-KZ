using System.Net.Http.Json;
using System.Text.Json;
using GlacierNET.Analysis.Models;

namespace GlacierNET.Blazor.Services;

public class ApiClient
{
    private readonly HttpClient _httpClient;
    private readonly JsonSerializerOptions _jsonOptions;

    public ApiClient(HttpClient httpClient)
    {
        _httpClient = httpClient;
        _jsonOptions = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase
        };
    }

    public async Task<T?> GetAsync<T>(string endpoint, CancellationToken cancellationToken = default)
    {
        var response = await _httpClient.GetAsync(endpoint, cancellationToken);
        if (response.IsSuccessStatusCode)
        {
            return await response.Content.ReadFromJsonAsync<T>(_jsonOptions, cancellationToken);
        }
        return default;
    }

    public async Task<PagedResult<T>?> GetPagedAsync<T>(string endpoint, int page = 1, int pageSize = 50, CancellationToken cancellationToken = default)
    {
        var separator = endpoint.Contains('?') ? "&" : "?";
        var url = $"{endpoint}{separator}page={page}&pageSize={pageSize}";
        return await GetAsync<PagedResult<T>>(url, cancellationToken);
    }

    public async Task<T?> PostAsync<T>(string endpoint, object data, CancellationToken cancellationToken = default)
    {
        var response = await _httpClient.PostAsJsonAsync(endpoint, data, _jsonOptions, cancellationToken);
        if (response.IsSuccessStatusCode)
        {
            return await response.Content.ReadFromJsonAsync<T>(_jsonOptions, cancellationToken);
        }
        return default;
    }

    public async Task<bool> PostAsync(string endpoint, object? data = null, CancellationToken cancellationToken = default)
    {
        var response = data != null
            ? await _httpClient.PostAsJsonAsync(endpoint, data, _jsonOptions, cancellationToken)
            : await _httpClient.PostAsync(endpoint, null, cancellationToken);
        return response.IsSuccessStatusCode;
    }

    public async Task<T?> PutAsync<T>(string endpoint, object data, CancellationToken cancellationToken = default)
    {
        var response = await _httpClient.PutAsJsonAsync(endpoint, data, _jsonOptions, cancellationToken);
        if (response.IsSuccessStatusCode)
        {
            return await response.Content.ReadFromJsonAsync<T>(_jsonOptions, cancellationToken);
        }
        return default;
    }

    public async Task<bool> PutAsync(string endpoint, object data, CancellationToken cancellationToken = default)
    {
        var response = await _httpClient.PutAsJsonAsync(endpoint, data, _jsonOptions, cancellationToken);
        return response.IsSuccessStatusCode;
    }

    public async Task<bool> DeleteAsync(string endpoint, CancellationToken cancellationToken = default)
    {
        var response = await _httpClient.DeleteAsync(endpoint, cancellationToken);
        return response.IsSuccessStatusCode;
    }

    public async Task<List<Glacier>> SearchGlaciersAsync(string? name = null, string? region = null, CancellationToken cancellationToken = default)
    {
        var queryParams = new List<string>();
        if (!string.IsNullOrEmpty(name)) queryParams.Add($"name={Uri.EscapeDataString(name)}");
        if (!string.IsNullOrEmpty(region)) queryParams.Add($"region={Uri.EscapeDataString(region)}");

        var query = queryParams.Any() ? $"?{string.Join("&", queryParams)}" : string.Empty;
        return await GetAsync<List<Glacier>>($"/api/glacier/search{query}", cancellationToken) ?? new();
    }

    public async Task<GlacierStatistics?> GetGlacierStatisticsAsync(CancellationToken cancellationToken = default)
    {
        return await GetAsync<GlacierStatistics>("/api/glacier/statistics", cancellationToken);
    }

    public async Task<List<AnalysisResult>> GetAnomaliesAsync(int limit = 100, CancellationToken cancellationToken = default)
    {
        return await GetAsync<List<AnalysisResult>>($"/api/analysis/anomalies?limit={limit}", cancellationToken) ?? new();
    }

    public async Task<AnalysisSummary?> GetAnalysisSummaryAsync(Guid glacierId, CancellationToken cancellationToken = default)
    {
        return await GetAsync<AnalysisSummary>($"/api/analysis/summary/{glacierId}", cancellationToken);
    }

    public async Task<AdminDashboard?> GetAdminDashboardAsync(CancellationToken cancellationToken = default)
    {
        return await GetAsync<AdminDashboard>("/api/admin/dashboard", cancellationToken);
    }

    public async Task<SystemHealth?> GetSystemHealthAsync(CancellationToken cancellationToken = default)
    {
        return await GetAsync<SystemHealth>("/api/admin/system-health", cancellationToken);
    }

    public async Task<List<Report>> GetRecentReportsAsync(int limit = 10, CancellationToken cancellationToken = default)
    {
        return await GetAsync<List<Report>>($"/api/report/recent?limit={limit}", cancellationToken) ?? new();
    }

    public async Task<string> GetReportHtmlAsync(Guid reportId, CancellationToken cancellationToken = default)
    {
        var response = await _httpClient.GetAsync($"/api/report/{reportId}/html", cancellationToken);
        if (response.IsSuccessStatusCode)
        {
            return await response.Content.ReadAsStringAsync(cancellationToken);
        }
        return string.Empty;
    }
}
