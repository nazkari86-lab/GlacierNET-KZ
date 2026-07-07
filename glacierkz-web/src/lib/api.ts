import { apiUrl } from "./utils";

export interface ModelInfo {
  name: string;
  display_name: string;
  description: string;
  supports_tta: boolean;
  supports_crf: boolean;
  supports_uncertainty: boolean;
}

export interface PredictResult {
  task_id: string;
  status: string;
  mask_path?: string;
  overlay_path?: string;
  area_km2?: number;
  error?: string;
  model_name?: string;
  image_path?: string;
}

export interface CompareSegment {
  model_name: string;
  mask_path: string;
  overlay_path: string;
  area_km2: number;
}

export interface CompareResult {
  task_id: string;
  segments: CompareSegment[];
}

export interface TrendResult {
  data: { year: number; area_km2: number }[];
  forecast: { year: number; area_km2: number; ci_lower?: number; ci_upper?: number }[];
  loss_rate_km2_per_year: number;
  total_loss_percent: number;
  r_squared: number;
  p_value?: number;
  significant?: boolean;
}

export interface HistoryItem {
  id: number;
  task_id: string;
  model_name: string;
  area_km2: number | null;
  year: number | null;
  created_at: string;
  thumbnail_path: string | null;
  mask_path: string | null;
  overlay_path: string | null;
  image_path: string | null;
  status: string;
}

function checkResponse(res: Response): Response {
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`);
  }
  return res;
}

export async function fetchModels(): Promise<ModelInfo[]> {
  const res = checkResponse(await fetch(apiUrl("/api/models")));
  return res.json();
}

export async function predict(
  file: File,
  modelName: string,
  useTta: boolean,
  useCrf: boolean,
  ndsiThreshold?: number,
  year?: number
): Promise<PredictResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("model_name", modelName);
  form.append("use_tta", String(useTta));
  form.append("use_crf", String(useCrf));
  if (ndsiThreshold !== undefined) {
    form.append("ndsi_threshold", String(ndsiThreshold));
  }
  if (year !== undefined) {
    form.append("year", String(year));
  }
  const res = checkResponse(await fetch(apiUrl("/api/predict"), { method: "POST", body: form }));
  return res.json();
}

export async function compareModels(
  file: File,
  modelNames: string[],
  useTta: boolean,
  useCrf: boolean
): Promise<CompareResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("model_names", modelNames.join(","));
  form.append("use_tta", String(useTta));
  form.append("use_crf", String(useCrf));
  const res = checkResponse(await fetch(apiUrl("/api/compare"), { method: "POST", body: form }));
  return res.json();
}

export async function fetchTrend(
  fileIds: string[],
  years: number[],
  forecastUntil = 2050
): Promise<TrendResult> {
  const res = checkResponse(await fetch(apiUrl("/api/trend"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_ids: fileIds, years, forecast_until: forecastUntil }),
  }));
  return res.json();
}

export async function fetchHistory(limit = 50, offset = 0): Promise<HistoryItem[]> {
  const res = checkResponse(await fetch(apiUrl(`/api/history?limit=${limit}&offset=${offset}`)));
  return res.json();
}

export function getStaticUrl(path: string): string {
  return path;
}

// --- LLM Analysis ---
export interface LLMModelInfo {
  id: string;
  name: string;
  free: boolean;
}

export interface LLMProviderInfo {
  provider: string;
  label: string;
  models: LLMModelInfo[];
  needs_key: boolean;
}

export interface LLMAnalyzeRequest {
  prompt: string;
  provider?: string;
  model?: string;
  mode?: "describe" | "trend" | "compare";
  context?: string;
  api_key?: string;
}

export interface LLMAnalyzeResponse {
  content: string;
  provider: string;
  model: string;
  fallback_used: boolean;
}

export async function fetchAnalysisModels(): Promise<LLMProviderInfo[]> {
  const res = checkResponse(await fetch(apiUrl("/api/analysis/models")));
  return res.json();
}

export async function fetchProviderModels(provider: string, apiKey: string): Promise<LLMModelInfo[]> {
  const res = checkResponse(
    await fetch(apiUrl("/api/analysis/models/fetch"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider, api_key: apiKey }),
    })
  );
  return res.json();
}

export async function analyzeWithLLM(body: LLMAnalyzeRequest): Promise<LLMAnalyzeResponse> {
  const res = checkResponse(await fetch(apiUrl("/api/analysis/analyze"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }));
  return res.json();
}

// --- MCP Tools ---
export interface MCPTool {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

export interface MCPToolCallResult {
  status: string;
  data: unknown;
  error: string | null;
}

export async function fetchMCPTools(): Promise<MCPTool[]> {
  const res = checkResponse(await fetch(apiUrl("/mcp/tools")));
  const data = await res.json();
  return data.tools;
}

export async function callMCPTool(toolName: string, args: Record<string, unknown> = {}): Promise<MCPToolCallResult> {
  const res = checkResponse(await fetch(apiUrl("/mcp/tools/call"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tool_name: toolName, arguments: args }),
  }));
  return res.json();
}

// --- Datasets ---
export interface DatasetInfo {
  id: string;
  name: string;
  size_mb: number;
  num_samples: number;
  glacier_name: string;
  date_range: string;
  status: string;
}

export interface DatasetListResponse {
  datasets: DatasetInfo[];
  total: number;
  offset: number;
  limit: number;
}

export async function fetchDatasets(search?: string): Promise<DatasetListResponse> {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  const qs = params.toString();
  const res = checkResponse(await fetch(apiUrl(qs ? `/api/datasets/?${qs}` : "/api/datasets/")));
  return res.json();
}

export async function uploadDataset(file: File, name?: string): Promise<DatasetInfo> {
  const form = new FormData();
  form.append("file", file);
  const params = name ? `?name=${encodeURIComponent(name)}` : "";
  const res = checkResponse(await fetch(apiUrl(`/api/datasets/upload${params}`), { method: "POST", body: form }));
  return res.json();
}

// --- Dashboard ---
export interface DashboardStats {
  total_segments: number;
  total_area_km2: number;
  models_registered: number;
  active_tasks: number;
  segments_over_time: { label: string; values: number[] }[];
  model_usage: { label: string; value: number; color: string }[];
  recent_tasks: {
    id: string;
    model: string;
    area_km2: number;
    date: string;
    status: string;
  }[];
}

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const res = checkResponse(await fetch(apiUrl("/api/dashboard/stats")));
  return res.json();
}

export interface DataCoverage {
  raw_sentinel2: number[];
  raw_landsat: number[];
  predictions: number[];
  missing_sentinel2: number[];
  missing_landsat: number[];
  missing_predictions: number[];
  glacier_area_rf_series: { year: number; area_km2: number; sensor: string }[];
  areas_row_count: number;
  updated_from: string;
}

export async function fetchDataCoverage(): Promise<DataCoverage> {
  const res = checkResponse(await fetch(apiUrl("/api/data/coverage")));
  return res.json();
}

export interface GrantTimeSeriesRow {
  year: string;
  area_km2: string;
  primary_method: string;
  sensor: string;
  source_flag: string;
  quality_score: string;
  confidence: string;
  include_in_strict_trend: string;
  source_file: string;
  caveat: string;
  created_at: string;
}

export interface YearQualityRow {
  year: string;
  sensor: string;
  source_file: string;
  source_flag: string;
  methods_available: string;
  has_rf: string;
  has_unet: string;
  has_ndsi: string;
  quality_score: string;
  confidence: string;
  include_in_strict_trend: string;
  caveat: string;
}

export interface GrantReadinessSummary {
  created_at?: string;
  quality_table?: string;
  grant_timeseries_table?: string;
  strict_trend?: {
    ok: boolean;
    n_years?: number;
    years?: number[];
    slope_km2_per_year?: number;
    r_squared?: number;
    p_value?: number;
    significant?: boolean;
    change_km2?: number;
    change_percent?: number;
    forecast_2050_km2?: number;
    forecast_2050_ci95_lower?: number;
    forecast_2050_ci95_upper?: number;
  };
  grant_readiness_notes?: string[];
}

export interface GrantReadiness {
  summary: GrantReadinessSummary;
  timeseries: GrantTimeSeriesRow[];
  year_quality: YearQualityRow[];
  updated_from: string;
}

export async function fetchGrantReadiness(): Promise<GrantReadiness> {
  const res = checkResponse(await fetch(apiUrl("/api/data/grant-readiness")));
  return res.json();
}

// --- Pipeline ---
export interface PipelineStageInfo {
  id: string;
  name: string;
  status: string;
  progress: number;
}

export interface PipelineRun {
  id: string;
  name: string;
  status: string;
  stages: PipelineStageInfo[];
  createdAt: string;
  triggeredBy: string;
  branch: string;
  commit?: string;
}

export async function fetchPipelineRuns(search?: string, status?: string): Promise<PipelineRun[]> {
  const params = new URLSearchParams();
  if (search) params.set("q", search);
  if (status && status !== "all") params.set("status", status);
  const qs = params.toString();
  const res = checkResponse(await fetch(apiUrl(`/api/pipeline/runs${qs ? `?${qs}` : ""}`)));
  const data = await res.json();
  return data.runs || [];
}

export async function cancelPipelineRun(runId: string): Promise<void> {
  checkResponse(await fetch(apiUrl(`/api/pipeline/runs/${runId}/cancel`), { method: "POST" }));
}

export async function rerunPipelineRun(runId: string): Promise<void> {
  checkResponse(await fetch(apiUrl(`/api/pipeline/runs/${runId}/rerun`), { method: "POST" }));
}

// --- Training ---
export interface TrainConfig {
  dataset_id: string;
  model_name: string;
  epochs: number;
  batch_size: number;
  learning_rate: number;
  optimizer: string;
}

export interface TrainStatus {
  task_id: string;
  status: string;
  epoch: number;
  total_epochs: number;
  metrics: Record<string, number>;
  best_metric: number;
}

export interface TrainingLogLine {
  time: string;
  text: string;
  type: "info" | "success" | "warning" | "error";
}

export async function startTraining(config: TrainConfig): Promise<TrainStatus> {
  const res = checkResponse(await fetch(apiUrl("/api/training/start"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  }));
  return res.json();
}

export async function getTrainingStatus(taskId: string): Promise<TrainStatus> {
  const res = checkResponse(await fetch(apiUrl(`/api/training/status/${taskId}`)));
  return res.json();
}

export async function getTrainingLogs(taskId: string): Promise<TrainingLogLine[]> {
  const res = checkResponse(await fetch(apiUrl(`/api/training/logs/${taskId}`)));
  const data = await res.json();
  return data.logs || [];
}

export async function pauseTrainingRun(taskId: string): Promise<TrainStatus> {
  const res = checkResponse(await fetch(apiUrl(`/api/training/pause/${taskId}`), { method: "POST" }));
  return res.json();
}

export async function stopTrainingRun(taskId: string): Promise<TrainStatus> {
  const res = checkResponse(await fetch(apiUrl(`/api/training/stop/${taskId}`), { method: "POST" }));
  return res.json();
}

// --- Admin ---
export interface AdminStats {
  totalUsers: number;
  activeUsers: number;
  totalDatasets: number;
  totalPredictions: number;
  storageUsed: number;
  storageTotal: number;
  cpuUsage: number;
  memoryUsage: number;
  uptime: number;
  errorRate: number;
  requestsPerMinute: number;
  avgResponseTime: number;
}

export interface AdminAlert {
  id: string;
  level: "info" | "warning" | "error";
  message: string;
  timestamp: string;
}

export interface AdminUser {
  id: string;
  name: string;
  email: string;
  role: "admin" | "operator" | "viewer";
  status: "active" | "inactive" | "suspended";
  lastLogin: string;
  datasetsCount: number;
  predictionsCount: number;
  createdAt: string;
}

export interface AdminSystemInfo {
  hostname: string;
  os: string;
  kernel: string;
  uptime: number;
  cpu: { model: string; cores: number; usage: number };
  memory: { total: number; used: number; free: number };
  disk: { total: number; used: number; mount: string };
  network: { rxBytes: number; txBytes: number; connections: number };
}

export interface AdminServiceHealth {
  name: string;
  status: "healthy" | "degraded" | "down";
  latency: number;
  lastChecked: string;
  url?: string;
}

export interface AuditEntry {
  id: string;
  userId: string;
  userName: string;
  action: string;
  resource: string;
  resourceId?: string;
  details?: string;
  ipAddress: string;
  userAgent: string;
  timestamp: string;
  level: "info" | "warning" | "error";
}

export async function fetchAdminStats(): Promise<AdminStats> {
  const res = checkResponse(await fetch(apiUrl("/api/admin/stats")));
  return res.json();
}

export async function fetchAdminAlerts(): Promise<AdminAlert[]> {
  const res = checkResponse(await fetch(apiUrl("/api/admin/alerts")));
  const data = await res.json();
  return data.alerts || [];
}

export async function fetchAdminRequestMetrics(): Promise<{ timestamp: number; value: number }[]> {
  const res = checkResponse(await fetch(apiUrl("/api/admin/metrics/requests")));
  const data = await res.json();
  return (data.points || []).map((p: { timestamp: number; value: number }) => ({
    timestamp: p.timestamp * 1000,
    value: p.value,
  }));
}

export async function fetchAdminSystemInfo(): Promise<AdminSystemInfo> {
  const res = checkResponse(await fetch(apiUrl("/api/admin/system/info")));
  return res.json();
}

export async function fetchAdminServices(): Promise<AdminServiceHealth[]> {
  const res = checkResponse(await fetch(apiUrl("/api/admin/system/services")));
  const data = await res.json();
  return data.services || [];
}

export async function fetchAdminUsers(params?: {
  q?: string;
  role?: string;
  status?: string;
}): Promise<AdminUser[]> {
  const search = new URLSearchParams();
  if (params?.q) search.set("q", params.q);
  if (params?.role && params.role !== "all") search.set("role", params.role);
  if (params?.status && params.status !== "all") search.set("status", params.status);
  const qs = search.toString();
  const res = checkResponse(await fetch(apiUrl(`/api/admin/users${qs ? `?${qs}` : ""}`)));
  const data = await res.json();
  return data.users || [];
}

export async function updateAdminUserRole(userId: string, role: string): Promise<void> {
  checkResponse(
    await fetch(apiUrl(`/api/admin/users/${userId}/role`), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role }),
    })
  );
}

export async function suspendAdminUser(userId: string): Promise<void> {
  checkResponse(await fetch(apiUrl(`/api/admin/users/${userId}/suspend`), { method: "POST" }));
}

export async function deleteAdminUser(userId: string): Promise<void> {
  checkResponse(await fetch(apiUrl(`/api/admin/users/${userId}`), { method: "DELETE" }));
}

export async function fetchAdminAudit(params?: {
  page?: number;
  limit?: number;
  q?: string;
  level?: string;
  from?: string;
  to?: string;
}): Promise<{ entries: AuditEntry[]; totalPages: number }> {
  const search = new URLSearchParams();
  if (params?.page) search.set("page", String(params.page));
  if (params?.limit) search.set("limit", String(params.limit));
  if (params?.q) search.set("q", params.q);
  if (params?.level && params.level !== "all") search.set("level", params.level);
  if (params?.from) search.set("from", params.from);
  if (params?.to) search.set("to", params.to);
  const qs = search.toString();
  const res = checkResponse(await fetch(apiUrl(`/api/admin/audit${qs ? `?${qs}` : ""}`)));
  const data = await res.json();
  return { entries: data.entries || [], totalPages: data.totalPages || 1 };
}

export async function exportAdminAuditCsv(params?: {
  q?: string;
  level?: string;
  from?: string;
  to?: string;
}): Promise<Blob> {
  const search = new URLSearchParams({ format: "csv" });
  if (params?.q) search.set("q", params.q);
  if (params?.level && params.level !== "all") search.set("level", params.level);
  if (params?.from) search.set("from", params.from);
  if (params?.to) search.set("to", params.to);
  const res = checkResponse(await fetch(apiUrl(`/api/admin/audit?${search}`)));
  return res.blob();
}
