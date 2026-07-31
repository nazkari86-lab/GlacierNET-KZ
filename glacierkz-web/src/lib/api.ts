import { apiUrl } from "./utils";
import { authFetch } from "./auth";
import type {
  CryoGenesisDiscoveryList,
  DiscoveryPassport,
} from "./cryogenesis";

export interface ModelInfo {
  name: string;
  display_name: string;
  description: string;
  supports_tta: boolean;
  supports_crf: boolean;
  supports_uncertainty: boolean;
  channel_count?: number;
  feature_schema?: string[];
  decision_threshold?: number;
  inference_variant?: string;
  evidence_tier?: string;
  recommended?: boolean;
  year_range?: [number | null, number | null] | null;
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
  geotiff_path?: string;
  probability_path?: string;
  probability_geotiff_path?: string;
  entropy_path?: string;
  entropy_geotiff_path?: string;
  decision_threshold?: number;
  inference_variant?: string;
  feature_schema?: string[];
  uncertain_pixel_fraction?: number;
  warnings?: string[];
}

export interface YearMethodResult {
  name: string;
  area_km2: number;
  glacier_pixels: number;
  mask_url?: string | null;
  artifact_available: boolean;
}

export interface YearResult {
  year: number;
  sensor: string;
  source_flag: string;
  source_file: string;
  source_available: boolean;
  source_size_mb?: number | null;
  quality_score: number;
  confidence: string;
  include_in_strict_trend: boolean;
  caveat: string;
  primary_method: string;
  primary_area_km2: number;
  reported_methods: string[];
  artifact_methods: string[];
  methods: Record<string, YearMethodResult>;
  overlay_url?: string | null;
  provenance_url?: string | null;
  provenance_available: boolean;
  artifact_status: "ready" | "metadata_only";
}

export interface YearComparison {
  from: YearResult;
  to: YearResult;
  change_km2: number;
  change_percent?: number | null;
  comparable_in_strict_trend: boolean;
  warnings: string[];
  method: string;
}

export interface YearMapLayer {
  available?: true;
  year: number;
  method: string;
  image_url: string;
  bounds: [[number, number], [number, number]];
  source: string;
  scope: string;
  caveat: string;
}

export interface GlacierRecord {
  rgi_id: string;
  name: string;
  name_ru: string;
  named: boolean;
  priority?: number | null;
  wgms_reference: boolean;
  glims_id?: string | null;
  subregion?: string | null;
  centroid: { longitude: number; latitude: number };
  rgi_area_km2: number;
  elevation: { min_m: number; mean_m: number; max_m: number };
  slope_deg: number;
  aspect_deg: number;
  maximum_length_m: number;
  dem_source?: string | null;
  inventory_date?: string | null;
  geometry?: { type: string; coordinates: unknown };
}

export interface GlacierSeriesPoint {
  year: number;
  area_km2: number;
  coverage_of_rgi_percent?: number | null;
  method: string;
  mask_url: string;
}

export interface GlacierTimeSeries {
  glacier: GlacierRecord;
  method: string;
  points: GlacierSeriesPoint[];
  first_year?: number | null;
  last_year?: number | null;
  change_km2?: number | null;
  change_percent?: number | null;
  wgms_points: { year: number; area_km2: number; source: string }[];
  scope: string;
  caveat: string;
}

export interface MlBenchmark {
  protocol?: string | null;
  test_years: number[];
  hard_dice?: number | null;
  hard_iou?: number | null;
  precision?: number | null;
  recall?: number | null;
  area_bias_percent?: number | null;
  label_quality_tier?: string | null;
  generalisation_scope?: string | null;
}

export interface BenchmarkSource {
  id: string;
  title: string;
  role: string;
  citation_url: string;
  license: string;
  evidence_tier: string;
  state: "verified_local" | "local_unverified" | "metadata_only" | "missing";
  available: boolean;
  local_path?: string | null;
  size_bytes: number;
  integrity: string;
  digest?: string | null;
  notes?: string;
}

export interface BenchmarkTrack {
  id: string;
  title: string;
  status: string;
  category: "model_evaluation" | "reference_evidence" | "decision_support_evaluation";
  evidence_tier?: string;
  scope?: string;
  metrics: Record<string, unknown>;
  headline_metrics?: Record<string, unknown>;
  source_states?: Record<string, string>;
  blockers?: string[];
  claim_allowed?: string | null;
  claim_not_allowed?: string | null;
  artifacts: Array<{ path: string; exists: boolean; sha256?: string | null; size_bytes?: number }>;
}

export interface CentralAsiaBenchmarkReport {
  schema: string;
  benchmark_name: string;
  status: "ready" | "not_built";
  created_at?: string;
  policy?: Record<string, boolean>;
  sources: BenchmarkSource[];
  tracks: BenchmarkTrack[];
  summary: {
    sources_total: number;
    sources_local: number;
    sources_verified: number;
    sources_metadata_only: number;
    sources_missing: number;
    tracks_total: number;
    tracks_data_ready: number;
    tracks_blocked: number;
    model_evaluations_total: number;
    model_evaluations_measured: number;
    reference_evidence_total: number;
    reference_evidence_available: number;
    decision_support_evaluations_total: number;
    decision_support_evaluations_ready: number;
  };
  claims_not_unlocked?: string[];
  build_command?: string;
}

export interface MlReadinessModel extends ModelInfo {
  available: boolean;
  trusted_artifact: boolean;
  benchmark: MlBenchmark;
}

export interface MlReadinessYear {
  year: number;
  sentinel2: boolean;
  terrain: boolean;
  sentinel1: boolean;
  compatible_models: string[];
  recommended_model?: string | null;
}

export interface MlTrainingDatasetSplit {
  patch_count: number;
  glacier_count: number;
  glaciers: string[];
  years: number[];
  glacier_pixel_fraction?: number | null;
  mean_training_weight?: number | null;
}

export interface MlSpatialEvaluation {
  status: string;
  created_at?: string;
  reason?: string;
  claim_scope?: string;
  annotation_status?: string;
  split_strategy?: string;
  patches?: Partial<Record<"train" | "val" | "test", number>>;
  glacier_counts?: Partial<Record<"train" | "val" | "test", number>>;
  epochs_requested?: number;
  epochs_completed?: number;
  baseline_test?: Partial<MlBenchmark> & { threshold?: number; area_bias_percent?: number };
  candidate_test?: Partial<MlBenchmark> & { threshold?: number; area_bias_percent?: number };
  candidate_minus_baseline_hard_iou?: number;
  promotion?: { status?: string; rule?: string };
  model_artifact_present?: boolean;
  claims_allowed?: string[];
  claims_not_allowed?: string[];
  limitations?: string[];
}

export interface MlTrainingDataset {
  status: "ready" | "blocked";
  dataset_id: string;
  schema?: string;
  created_at?: string;
  annotation_status?: string;
  dataset_role?: string;
  split_strategy?: string;
  channel_count?: number;
  patch_size?: number;
  feature_schema?: string[];
  eligible_tasks?: number;
  patch_count?: number;
  storage_bytes?: number;
  minimum_geometry_coverage?: number | null;
  excluded_tasks?: {
    total: number;
    by_confidence: Record<string, number>;
    handling?: string | null;
  };
  splits: Partial<Record<"train" | "val" | "test", MlTrainingDatasetSplit>>;
  membership: Record<string, "train" | "val" | "test">;
  review_queue: Array<{
    glacier_id: string;
    year: number;
    confidence: string;
    quality_score: number;
    review_priority: number;
    flags: string[];
    next_action: string;
  }>;
  spatial_evaluation?: MlSpatialEvaluation;
  weight_policy?: Record<string, string | number>;
  preview_url?: string | null;
  manifest_url: string;
  training_command?: string;
  integrity?: {
    required_arrays_present: boolean;
    declared_outputs_size_matched: boolean;
    full_sha256_validation: string;
  };
  limitations: string[];
  reason?: string;
}

export interface MlTrainingPipelineCheck {
  schema: string;
  status: "verified";
  created_at: string;
  dataset_id: string;
  dataset_manifest_sha256: string;
  purpose: string;
  architecture: string;
  batch: {
    features: number[];
    labels: number[];
    weights: number[];
    weight_min: number;
    weight_max: number;
    nonzero_weight_fraction: number;
  };
  metrics: Record<string, number>;
  runtime: {
    duration_seconds: number;
    tensorflow: string;
    python: string;
    devices: string[];
  };
  claims_allowed: string[];
  claims_not_allowed: string[];
  cache: { hit: boolean };
}

export interface MlReadiness {
  status: "ready" | "blocked";
  recommended_model?: string | null;
  years: MlReadinessYear[];
  models: MlReadinessModel[];
  training_dataset: MlTrainingDataset;
  generalisation_sentinel: {
    status: string;
    selected_config?: { ndsi_threshold: number; support_buffer_m: number; retain_inventory_connected_components: boolean } | null;
    n_external_glaciers?: number | null;
    baseline_hard_dice?: number | null;
    safeguard_hard_dice?: number | null;
    paired_dice_delta?: number | null;
    claim_tier: string;
  };
  workflow: string[];
  interpretation: string;
}

export interface MlEvidenceCase {
  schema: string;
  case_id: string;
  created_at: string;
  glacier: GlacierRecord;
  year: number;
  model: ModelInfo & {
    artifact_sha256?: string | null;
    benchmark_protocol?: string | null;
    test_years?: number[];
    label_quality_tier?: string | null;
  };
  inference: {
    variant: string;
    use_tta: boolean;
    decision_threshold: number;
    duration_seconds: number;
    window_shape: [number, number];
    context_m: number;
    feature_schema: string[];
  };
  source: {
    sentinel2_file: string;
    sentinel2_size_bytes: number;
    source_crop_sha256: string;
    terrain_file: string;
    sentinel1_file?: string | null;
  };
  metrics: {
    predicted_area_km2: number;
    rgi_rasterized_area_km2: number;
    area_delta_percent?: number | null;
    rgi_overlap_iou: number;
    mean_probability_in_selected_component: number;
    uncertain_fraction_in_review_zone: number;
    mean_boundary_entropy_nats?: number | null;
    review_priority_0_100: number;
    inventory_guided_area_km2: number;
    inventory_guided_area_delta_percent?: number | null;
    inventory_guided_rgi_overlap_iou: number;
    inventory_guided_spectral_fraction: number;
  };
  map: {
    bounds: [[number, number], [number, number]];
    rgi_geometry: { type: string; coordinates: unknown };
    model_geometry?: { type: string; coordinates: unknown } | null;
    inventory_guided_geometry?: { type: string; coordinates: unknown } | null;
  };
  inventory_guided_decoder: {
    schema: string;
    config: { ndsi_threshold: number; support_buffer_m: number; retain_inventory_connected_components: boolean };
    claim_tier: string;
    circular_validation_warning: string;
  };
  artifacts: Record<string, string | null>;
  review: { status: string; next_action: string; risk_twin_url: string };
  claims_allowed: string[];
  claims_not_allowed: string[];
  warnings: string[];
  cache: { hit: boolean; case_id: string };
}

export async function fetchGlaciers(
  search = "",
  namedOnly = true,
  limit = 1000,
  includeGeometry = false
): Promise<{ glaciers: GlacierRecord[]; total: number }> {
  const params = new URLSearchParams({
    search,
    named_only: String(namedOnly),
    limit: String(limit),
    include_geometry: String(includeGeometry),
  });
  const res = checkResponse(await fetch(apiUrl(`/api/glaciers?${params}`)));
  return res.json();
}

export async function fetchGlacier(
  rgiId: string,
): Promise<GlacierRecord> {
  const res = checkResponse(
    await fetch(
      apiUrl(`/api/glaciers/${encodeURIComponent(rgiId)}?include_geometry=true`),
    ),
  );
  return res.json();
}

export async function fetchCryoGenesisDiscoveries(): Promise<CryoGenesisDiscoveryList> {
  const res = checkResponse(
    await fetch(apiUrl("/api/cryogenesis/discoveries"), {
      cache: "no-store",
    }),
  );
  return res.json();
}

export async function fetchCryoGenesisPassport(
  rgiId: string,
): Promise<DiscoveryPassport> {
  const res = checkResponse(
    await fetch(
      apiUrl(
        `/api/cryogenesis/glaciers/${encodeURIComponent(rgiId)}/passport`,
      ),
      { cache: "no-store" },
    ),
  );
  return res.json();
}

export async function fetchGlacierSeries(
  rgiId: string,
  method = "ndsi"
): Promise<GlacierTimeSeries> {
  const res = checkResponse(
    await fetch(apiUrl(`/api/glaciers/${encodeURIComponent(rgiId)}/timeseries?method=${method}`))
  );
  return res.json();
}

export async function fetchMlReadiness(): Promise<MlReadiness> {
  const res = checkResponse(await fetch(apiUrl("/api/ml/readiness"), { cache: "no-store" }));
  return res.json();
}

export async function fetchMlTrainingDataset(): Promise<MlTrainingDataset> {
  const res = checkResponse(await fetch(apiUrl("/api/ml/training-dataset"), { cache: "no-store" }));
  return res.json();
}

export async function verifyMlTrainingDataset(refresh = false): Promise<MlTrainingPipelineCheck> {
  const response = await fetch(apiUrl("/api/ml/training-dataset/verify"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!response.ok) {
    let detail = `API ${response.status}: ${response.statusText}`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Preserve the status fallback when the response is not JSON.
    }
    throw new Error(detail);
  }
  return response.json();
}

export async function analyzeMlGlacier(
  rgiId: string,
  request: {
    year: number;
    model_name: string;
    use_tta: boolean;
    context_m?: number;
    refresh?: boolean;
  }
): Promise<MlEvidenceCase> {
  const response = await fetch(apiUrl(`/api/ml/glaciers/${encodeURIComponent(rgiId)}/analyze`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    let detail = `API ${response.status}: ${response.statusText}`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Preserve the status fallback when the response is not JSON.
    }
    throw new Error(detail);
  }
  return response.json();
}

export async function fetchMlCase(caseId: string): Promise<MlEvidenceCase> {
  const res = checkResponse(await fetch(apiUrl(`/api/ml/cases/${encodeURIComponent(caseId)}`)));
  return res.json();
}

export async function fetchYears(strictOnly = false): Promise<YearResult[]> {
  const res = checkResponse(await fetch(apiUrl(`/api/years?strict_only=${strictOnly}`)));
  const body = await res.json();
  return body.years;
}

export async function compareLocalYears(fromYear: number, toYear: number): Promise<YearComparison> {
  const params = new URLSearchParams({
    from_year: String(fromYear),
    to_year: String(toYear),
  });
  const res = checkResponse(await fetch(apiUrl(`/api/years/compare?${params}`)));
  return res.json();
}

export async function fetchYearMapLayer(year: number): Promise<YearMapLayer> {
  const res = checkResponse(await fetch(apiUrl(`/api/years/${year}/map-layer`)));
  const body = await res.json() as YearMapLayer | {
    available: false;
    year: number;
    reason: string;
  };
  if (body.available === false) {
    throw new Error(body.reason);
  }
  return body;
}

export interface CompareSegment {
  model_name: string;
  mask_path: string;
  overlay_path: string;
  area_km2: number | null;
}

export interface CompareResult {
  task_id: string;
  segments: CompareSegment[];
  failures?: { model_name: string; error: string }[];
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

export interface TrendEvidencePoint {
  year: number;
  area_km2: number;
  sensor: string;
  quality_score: number;
  confidence: string;
  included_in_exploratory_trend: boolean;
  caveat: string;
}

export interface TrendEvidence {
  title: string;
  status: "exploratory_not_adjudicated";
  primary_table: string;
  points: TrendEvidencePoint[];
  exploratory_points: TrendEvidencePoint[];
  exploratory_linear_trend: {
    n_observations: number;
    first_year: number;
    last_year: number;
    slope_km2_per_year: number;
    slope_interval_95_approx: [number, number];
    r_squared: number;
    net_change_km2: number;
    net_change_percent: number | null;
  } | null;
  flagged_temporal_anomalies: { year: number; status: string; relative_change_percent: number; reason: string }[];
  limitations: string[];
}

export async function fetchTrendEvidence(): Promise<TrendEvidence> {
  const res = checkResponse(await fetch(apiUrl("/api/analysis/evidence/trend")));
  return res.json();
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
  useCrf: boolean,
  year?: number,
): Promise<CompareResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("model_names", modelNames.join(","));
  form.append("use_tta", String(useTta));
  form.append("use_crf", String(useCrf));
  if (year !== undefined) form.append("year", String(year));
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
  const res = await fetch(apiUrl("/api/analysis/models/fetch"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, api_key: apiKey }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `API ${res.status}: ${res.statusText}`);
  }
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
  bands?: number;
  source_path?: string;
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

export interface DecisionTimeSeriesRow {
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

export interface DecisionReadinessSummary {
  created_at?: string;
  quality_table?: string;
  decision_timeseries_table?: string;
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
  decision_readiness_notes?: string[];
}

export interface DecisionReadiness {
  summary: DecisionReadinessSummary;
  timeseries: DecisionTimeSeriesRow[];
  year_quality: YearQualityRow[];
  updated_from: string;
}

export async function fetchDecisionReadiness(): Promise<DecisionReadiness> {
  const res = checkResponse(await fetch(apiUrl("/api/data/decision-readiness")));
  return res.json();
}

// --- Active Cryosphere Risk Twin (research screening, never an official warning) ---
export interface RiskTwinReadiness {
  status: string;
  available: string[];
  blocked: string[];
  safety_statement: string;
}

export interface RiskTwinObservationInput {
  observation_id: string;
  variable: string;
  value: number;
  uncertainty_std: number;
  timestamp: string;
  sensor: string;
  quality_flags?: string[];
  spatial_support?: string;
}

export interface RiskTwinActionInput {
  action_id: string;
  label: string;
  target_variables: string[];
  expected_observation_variance: Record<string, number>;
  cost?: number;
  latency_hours?: number;
  available?: boolean;
}

export interface RiskTwinRequest {
  basin_id: string;
  observations: RiskTwinObservationInput[];
  actions?: RiskTwinActionInput[];
  required_variables?: string[];
  priority_inputs?: {
    current_anomaly: number;
    resilience_vulnerability?: number;
    potential_consequence: number;
    staleness?: number;
  };
}

export interface RiskTwinResult {
  maturity: string;
  state: {
    basin_id: string;
    state: Record<string, { mean: number; std: number; ci95: [number, number]; observation_count: number; updated_at: string }>;
    data_gaps: string[];
    provenance: Array<Record<string, unknown>>;
  };
  observation_ranking: Array<{
    action_id: string;
    label: string;
    available: boolean;
    model_based_uncertainty_reduction_fraction?: number;
    [key: string]: unknown;
  }>;
  decision_support: { abstain: boolean; reasons?: string[]; [key: string]: unknown };
  priorities: { status?: string; hazard_priority?: { score?: number; status?: string } | null; observation_priority?: { score?: number; status?: string } | null; [key: string]: unknown };
  cascade_graph: { nodes: Array<Record<string, unknown>>; edges: Array<Record<string, unknown>> };
  claims_not_allowed: string[];
  [key: string]: unknown;
}

export async function fetchRiskTwinReadiness(): Promise<RiskTwinReadiness> {
  const res = checkResponse(await fetch(apiUrl("/api/risk-twin/readiness")));
  return res.json();
}

export type OsintLinkScope = "near_glacier" | "regional_trigger_context" | "broad_context" | "unresolved";

export interface OsintEvent {
  id: string;
  external_id: string;
  source_id: string;
  source_name: string;
  source_tier: string;
  title: string;
  summary: string;
  url: string;
  published_at: string;
  event_type: string;
  matched_topics: string[];
  latitude: number | null;
  longitude: number | null;
  location_name: string;
  geolocation_method: string;
  geolocation_uncertainty_km: number | null;
  magnitude: number | null;
  severity_label: string | null;
  linked_glacier: {
    rgi_id: string;
    name: string;
    name_ru: string;
    centroid: { longitude: number; latitude: number };
  } | null;
  distance_to_glacier_km: number | null;
  link_scope: OsintLinkScope;
  link_rationale: string;
  evidence_confidence_0_1: number;
  observation_priority_0_100: number;
  recommended_action: string;
  hazard_probability: null;
  claim_status: "reported_signal_not_validated_hazard";
  content_sha256: string;
}

export interface OsintRadar {
  schema: string;
  generated_at: string;
  region: {
    name: string;
    bounds: { minlatitude: number; maxlatitude: number; minlongitude: number; maxlongitude: number };
  };
  events: OsintEvent[];
  source_health: Array<{ source_id: string; status: string; items: number; error: string | null }>;
  summary: {
    events_total: number;
    near_glacier: number;
    regional_trigger_context: number;
    official_or_authoritative: number;
    unresolved: number;
  };
  method: Record<string, string>;
  claims_allowed: string[];
  claims_not_allowed: string[];
  warnings: string[];
  cache: { status: string; ttl_seconds: number };
  returned: number;
  matched: number;
}

export interface OsintSourceCatalog {
  schema: string;
  sources: Array<{
    id: string;
    name: string;
    tier: string;
    mode: string;
    url: string;
    license_note: string;
    role: string;
    configured: boolean;
  }>;
  content_policy: string;
}

export interface OsintReadiness {
  schema: string;
  status: string;
  available: string[];
  blocked: string[];
  unlock_requires: string[];
  safety_statement: string;
}

export async function fetchOsintEvents(options: {
  rgiId?: string;
  eventType?: string;
  sourceTier?: string;
  scope?: "all" | OsintLinkScope;
  limit?: number;
  refresh?: boolean;
} = {}): Promise<OsintRadar> {
  const params = new URLSearchParams();
  if (options.rgiId) params.set("rgi_id", options.rgiId);
  if (options.eventType) params.set("event_type", options.eventType);
  if (options.sourceTier) params.set("source_tier", options.sourceTier);
  if (options.scope && options.scope !== "all") params.set("scope", options.scope);
  params.set("limit", String(options.limit ?? 100));
  if (options.refresh) params.set("refresh", "true");
  const res = checkResponse(await fetch(apiUrl(`/api/osint/events?${params.toString()}`)));
  return res.json();
}

export async function fetchOsintSources(): Promise<OsintSourceCatalog> {
  const res = checkResponse(await fetch(apiUrl("/api/osint/sources")));
  return res.json();
}

export async function fetchOsintReadiness(): Promise<OsintReadiness> {
  const res = checkResponse(await fetch(apiUrl("/api/osint/readiness")));
  return res.json();
}

export async function evaluateRiskTwin(payload: RiskTwinRequest): Promise<RiskTwinResult> {
  const res = checkResponse(await fetch(apiUrl("/api/risk-twin/evaluate"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }));
  return res.json();
}

export interface GeoJsonFeatureCollection {
  type: "FeatureCollection";
  features: Array<{ type: "Feature"; properties: Record<string, unknown>; geometry: { type: string; coordinates: unknown } }>;
}

export interface RiskTwinSpatialContext {
  schema: string;
  query: { year: number; buffer_km: number; lake_inventory_year: number; previous_lake_inventory_year: number | null };
  layers: {
    hma_gli_2015_2018: GeoJsonFeatureCollection;
    tien_shan_lakes: GeoJsonFeatureCollection;
    historical_glof_events: GeoJsonFeatureCollection;
    hydrorivers: GeoJsonFeatureCollection;
    hydrobasins_level06: GeoJsonFeatureCollection;
  };
  lake_timeseries: Array<{ year: number; lake_count: number; total_area_m2: number }>;
  screening_candidates: Array<{
    lake_id: string | null;
    inventory_year: number;
    previous_inventory_year: number | null;
    latitude: number;
    longitude: number;
    area_current_m2: number;
    area_previous_m2: number | null;
    area_change_percent: number | null;
    geometric_match_distance_m: number | null;
    distance_to_rgi_boundary_m: number;
    elevation_m: number | null;
    observation_priority_0_100: number;
    flags: string[];
    interpretation: string;
  }>;
  impact_assets: {
    available: boolean;
    planning_radius_km: number;
  features: GeoJsonFeatureCollection;
  summary: Record<string, number>;
  nearby_asset_count?: number;
  returned_feature_count?: number;
  map_feature_limit?: number;
    reason?: string;
    source?: string;
    interpretation: string;
  };
  downstream_route: {
    available: boolean;
    status: string;
    start_reach_id?: number;
    start_distance_to_rgi_boundary_m?: number;
    connector_quality?: "near" | "screening_only";
    route_length_km?: number;
    route_segment_count?: number;
    next_downstream_id_after_subset?: number | null;
    max_route_km?: number;
    corridor_width_m?: number;
    features: GeoJsonFeatureCollection;
    corridor: { type: "Feature"; properties: Record<string, unknown>; geometry: GeoJSON.GeoJsonObject } | null;
    planning_assets: GeoJsonFeatureCollection;
    planning_asset_summary?: Record<string, number>;
    planning_asset_count?: number;
    returned_planning_asset_count?: number;
    interpretation?: string;
  };
  terrain: { available: boolean; path: string; bands?: Record<string, number | null>; scope?: string; reason?: string };
  sentinel1: { available: boolean; path: string; bands?: Record<string, number | null>; scope?: string; reason?: string };
  jrc_surface_water: { available: boolean; path: string; bands?: Record<string, number | null>; scope?: string; reason?: string };
  climate_context: {
    available: boolean;
    path: string;
    dataset?: string;
    variables?: string[];
    years?: string[];
    bbox_wgs84?: number[];
    scope?: string;
    interpretation?: string;
    reason?: string;
  };
  population_planning_context: {
    available: boolean;
    path: string;
    reference_year?: number;
    planning_radius_km: number;
    modelled_population_grid_sum?: number;
    non_empty_grid_cells?: number;
    scope?: string;
    reason?: string;
  };
  benchmark_physical_context?: {
    available: boolean;
    oggm?: {
      inventory_based_volume_km3?: number | null;
      volume_area_scaling_km3?: number | null;
      dem_mean_elevation_m?: number | null;
      main_flowline_length_m?: number | null;
      calibration_reference_mass_balance_kg_m2_year?: number | null;
      calibration_reference_error_kg_m2_year?: number | null;
      calibration_reference_period?: string | null;
      evidence_type: string;
    } | null;
    itslive_point_sample?: {
      observations_valid: number;
      velocity_m_per_year_median?: number | null;
      velocity_m_per_year_p90?: number | null;
      velocity_m_per_year_max?: number | null;
      sampling_geometry: string;
      evidence_type: string;
    } | null;
    itslive_cloud_coverage: Array<{ cube_id: string; bbox: number[]; zarr_url: string }>;
    claim_allowed: Array<string | null>;
    claim_not_allowed: string[];
  };
  interpretation: { allowed: string[]; not_allowed: string[]; event_note: string };
  sources: string[];
}

export interface RegionalObservationScan {
  schema: string;
  status: string;
  buffer_km: number;
  inventory_year: number;
  previous_inventory_year: number | null;
  returned: number;
  summary: { scanned_lakes: number; candidates_with_nearby_rgi: number; unmatched_previous: number; large_change_screening: number };
  candidates: Array<{
    lake_id: string | null;
    inventory_year: number;
    latitude: number;
    longitude: number;
    area_current_m2: number;
    previous_inventory_year: number | null;
    area_previous_m2: number | null;
    area_change_percent: number | null;
    geometric_match_distance_m: number | null;
    distance_to_rgi_boundary_m: number;
    observation_priority_0_100: number;
    flags: string[];
    glacier: { rgi_id: string; name: string; name_ru: string; centroid: { latitude: number; longitude: number }; rgi_area_km2: number };
    historical_event_count_in_glacier_context: number;
    interpretation: string;
  }>;
  limitations: string[];
}

/**
 * A candidate can have no upstream lake identifier, so an RGI ID alone is
 * not a stable UI key. Keep the inventory and exact coordinates in the key
 * to prevent one real observation from overwriting another in a list or map.
 */
export function regionalObservationCandidateKey(candidate: RegionalObservationScan["candidates"][number]): string {
  return [
    candidate.glacier.rgi_id,
    candidate.inventory_year,
    candidate.lake_id ?? "without-id",
    candidate.latitude.toFixed(6),
    candidate.longitude.toFixed(6),
  ].join(":");
}

/**
 * Keep an already-open browser usable across a rolling local API restart.
 * v2 used a 2023/2020-specific shape; v3 makes the inventory year explicit.
 * This adapter is deliberately narrow and is removed only after every deployed
 * API is known to serve v3. It never synthesizes measurements or matches.
 */
function normalizeRiskTwinContext(payload: unknown): RiskTwinSpatialContext {
  const raw = payload as Record<string, unknown>;
  const rawLayers = (raw.layers ?? {}) as Record<string, unknown>;
  const emptyLayer: GeoJsonFeatureCollection = { type: "FeatureCollection", features: [] };
  const rawQuery = (raw.query ?? {}) as Record<string, unknown>;
  const inventoryYear = Number(rawQuery.lake_inventory_year ?? 2023);
  const previousYearValue = rawQuery.previous_lake_inventory_year;
  const previousYear = typeof previousYearValue === "number" ? previousYearValue : inventoryYear === 2023 ? 2020 : null;
  const rawCandidates = Array.isArray(raw.screening_candidates) ? raw.screening_candidates as Array<Record<string, unknown>> : [];
  const rawRoute = (raw.downstream_route ?? {}) as Record<string, unknown>;
  return {
    ...raw,
    query: {
      year: Number(rawQuery.year ?? 2024),
      buffer_km: Number(rawQuery.buffer_km ?? 10),
      lake_inventory_year: inventoryYear,
      previous_lake_inventory_year: previousYear,
    },
    layers: {
      hma_gli_2015_2018: (rawLayers.hma_gli_2015_2018 ?? emptyLayer) as GeoJsonFeatureCollection,
      tien_shan_lakes: (rawLayers.tien_shan_lakes ?? rawLayers.tien_shan_lakes_2023 ?? emptyLayer) as GeoJsonFeatureCollection,
      historical_glof_events: (rawLayers.historical_glof_events ?? emptyLayer) as GeoJsonFeatureCollection,
      hydrorivers: (rawLayers.hydrorivers ?? emptyLayer) as GeoJsonFeatureCollection,
      hydrobasins_level06: (rawLayers.hydrobasins_level06 ?? emptyLayer) as GeoJsonFeatureCollection,
    },
    downstream_route: {
      ...rawRoute,
      available: rawRoute.available === true,
      status: String(rawRoute.status ?? "not_available"),
      features: (rawRoute.features ?? emptyLayer) as GeoJsonFeatureCollection,
      corridor: (rawRoute.corridor ?? null) as RiskTwinSpatialContext["downstream_route"]["corridor"],
      planning_assets: (rawRoute.planning_assets ?? emptyLayer) as GeoJsonFeatureCollection,
    },
    screening_candidates: rawCandidates.map((candidate) => ({
      ...candidate,
      lake_id: candidate.lake_id ?? candidate.lake_id_2023 ?? null,
      inventory_year: Number(candidate.inventory_year ?? inventoryYear),
      previous_inventory_year: candidate.previous_inventory_year ?? previousYear,
      area_current_m2: Number(candidate.area_current_m2 ?? candidate.area_2023_m2 ?? 0),
      area_previous_m2: candidate.area_previous_m2 ?? candidate.area_2020_m2 ?? null,
      area_change_percent: candidate.area_change_percent ?? candidate.area_change_2020_2023_percent ?? null,
    })),
  } as RiskTwinSpatialContext;
}

export async function fetchRiskTwinContext(
  rgiId: string,
  year = 2024,
  bufferKm = 10,
  lakeInventoryYear = 2023,
): Promise<RiskTwinSpatialContext> {
  const params = new URLSearchParams({ year: String(year), buffer_km: String(bufferKm), lake_inventory_year: String(lakeInventoryYear) });
  const res = checkResponse(await fetch(apiUrl(`/api/risk-twin/context/${encodeURIComponent(rgiId)}?${params}`)));
  return normalizeRiskTwinContext(await res.json());
}

export async function fetchRegionalObservationScan(limit = 100, bufferKm = 10, inventoryYear = 2023): Promise<RegionalObservationScan> {
  const params = new URLSearchParams({ limit: String(limit), buffer_km: String(bufferKm), inventory_year: String(inventoryYear) });
  const res = checkResponse(await fetch(apiUrl(`/api/risk-twin/regional-scan?${params}`)));
  return res.json();
}

export interface JuryEvidence {
  claim_policy: string;
  release_checks: { local_package_complete: boolean; required_artifact_count: number };
  claim_status_counts: Record<string, number>;
  supported_now: { title: string; value: Record<string, number | string | null>; scope: string }[];
  honest_negative_result: { title: string; hard_dice: { estimate: number; ci_lower: number; ci_upper: number }; area_error_percent: { estimate: number; ci_lower: number; ci_upper: number }; meaning: string };
  strict_trend: { n_years: number; slope_km2_per_year: number; p_value: number; significant: boolean; meaning: string };
  blocked_until_external_work: { id: string; claim: string; scope: string; evidence: string[] }[];
  automation_readiness: {
    available: boolean;
    machine_assisted_label_pack: { status: string; tasks: number; glaciers: number; years: number[]; purpose: string };
    claims: { id: string; claim: string; automated_input_ready: boolean; status: string }[];
  };
  scientific_evidence: ScientificEvidence;
  sources: string[];
}

export type ClaimEvidenceStatus = "supported_silver" | "supported_provisional" | "refuted_for_current_model" | "blocked_external_evidence";

export interface EvidenceArtifact {
  path: string;
  exists: boolean;
  sha256: string | null;
}

export interface ScientificEvidence {
  schema: "glaciernet-kz.scientific-evidence.v1";
  claim_policy: string;
  claim_registry: Array<{ id: string; status: ClaimEvidenceStatus; claim: string; scope: string; artifacts: EvidenceArtifact[] }>;
  temporal_holdout: {
    evaluation_protocol: string;
    generalisation_scope: string;
    label_quality_tier: string;
    label_provenance: string;
    splits: { train_years: number[]; validation_years: number[]; test_years: number[] };
    hard_metrics: Record<string, number | string>;
    threshold_calibration: { selection_split: string; objective: string; selected_threshold: number };
    glacier_level_ci_status: string;
    boundary_metrics_status: string;
    claims_allowed: string[];
    claims_not_allowed: string[];
    artifacts: EvidenceArtifact[];
  };
  paired_glacier_diagnostic: {
    label_quality_tier: string;
    evaluation_status: string;
    cohort_selection: { n_glaciers: number; [key: string]: number };
    metrics: Record<string, { estimate: number; ci_lower: number; ci_upper: number; confidence: number; n_glaciers: number; [key: string]: number }>;
    paired_tests: Record<string, unknown>;
    claims_not_allowed: string[];
    artifacts: EvidenceArtifact[];
  };
  external_generalisation: { status: ClaimEvidenceStatus | "external_evidence_available"; test_region: string; label_quality_tier_required: string; blocked_reason?: string | null; artifact: EvidenceArtifact };
  external_safeguard: {
    status: string;
    method: string;
    selected_config: { ndsi_threshold: number; support_buffer_m: number; retain_inventory_connected_components: boolean };
    n_calibration_glaciers: number;
    n_external_glaciers: number;
    parameters_frozen_before_external_replay: boolean;
    baseline: Record<string, { estimate: number; ci_lower: number; ci_upper: number }>;
    safeguard: Record<string, { estimate: number; ci_lower: number; ci_upper: number }>;
    paired_delta: Record<string, { estimate: number; ci_lower: number; ci_upper: number }>;
    circularity_guard: string;
    claims_not_allowed: string[];
    artifacts: EvidenceArtifact[];
  };
}

export async function fetchJuryEvidence(): Promise<JuryEvidence> {
  const res = checkResponse(await fetch(apiUrl("/api/jury/evidence")));
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

// --- Cryosphere Operations ---
export interface OperationsAsset {
  id: string;
  basin_id: string;
  asset_type: string;
  name: string;
  latitude: number;
  longitude: number;
  status: string;
  evidence_tier: string;
  model_version?: string | null;
  data_version?: string | null;
  allowed_use: string;
  forbidden_use: string;
}

export interface ChangeCandidate {
  id: string;
  asset_id: string;
  change_type: string;
  magnitude: number;
  uncertainty: number;
  data_quality_gap: number;
  model_disagreement: number;
  expected_information_gain: number;
  domain_shift_status: string;
  priority_score: number;
  next_action: string;
  rationale: string;
  status: string;
  evidence_tier: string;
  detected_at: string;
}

export interface InspectionTask {
  id: string;
  asset_id: string;
  candidate_id?: string | null;
  action_type: string;
  priority_score: number;
  rationale: string;
  status: string;
  assigned_to?: string | null;
  due_at?: string | null;
  offline_package_status: string;
}

export interface EvidenceCase {
  id: string;
  asset_id: string;
  title: string;
  status: string;
  summary: string;
  limitations: string;
  allowed_use: string;
  forbidden_use: string;
  reviewer?: string | null;
  updated_at: string;
}

export interface OperationsObservation {
  id: string;
  asset_id: string;
  observation_type: string;
  observed_at: string;
  source: string;
  values_json: string;
  quality_status: string;
  uncertainty: number;
  artifact_sha256?: string | null;
  created_by: string;
  created_at: string;
}

export interface OperationsFieldReport {
  id: string;
  task_id: string;
  asset_id: string;
  observer: string;
  observed_at: string;
  notes: string;
  signature: string;
  sync_status: string;
  created_at: string;
}

export interface OperationsDecision {
  id: string;
  evidence_case_id: string;
  decision: string;
  rationale: string;
  decided_by: string;
  decided_at: string;
  outcome?: string | null;
  status: string;
}

export interface OperationsAuditEvent {
  sequence: number;
  entity_type: string;
  entity_id: string;
  action: string;
  actor: string;
  payload_sha256: string;
  previous_event_sha256?: string | null;
  event_sha256: string;
  created_at: string;
}

export interface OperationsOverview {
  counts: Record<string, number>;
  observation_queue: ChangeCandidate[];
  inspection_tasks: InspectionTask[];
  assets: OperationsAsset[];
  observations: OperationsObservation[];
  field_reports: OperationsFieldReport[];
  evidence_cases: EvidenceCase[];
  decisions: OperationsDecision[];
  audit_events: OperationsAuditEvent[];
  audit_chain: {
    valid: boolean;
    events: number;
    head_sha256?: string | null;
  };
  safety_statement: string;
  demo_only?: boolean;
  persistence?: string;
}

export interface FieldReportInput {
  task_id: string;
  asset_id: string;
  observer: string;
  observed_at: string;
  latitude: number;
  longitude: number;
  measurements: Record<string, unknown>;
  checklist: Record<string, boolean | string | null>;
  notes: string;
  attachment_manifest: Array<Record<string, unknown>>;
  signature: string;
  sync_status: "offline_draft" | "synced";
}

export interface InspectionTaskInput {
  asset_id: string;
  candidate_id?: string | null;
  action_type: string;
  priority_score: number;
  rationale: string;
  assigned_to?: string | null;
  due_at?: string | null;
}

export interface RiskTwinHandoffInput {
  rgi_id: string;
  glacier_name: string;
  lake_id?: string | null;
  inventory_year: number;
  previous_inventory_year?: number | null;
  latitude: number;
  longitude: number;
  area_current_m2: number;
  area_previous_m2?: number | null;
  area_change_percent?: number | null;
  geometric_match_distance_m?: number | null;
  distance_to_rgi_boundary_m: number;
  observation_priority_0_100: number;
  flags: string[];
  action_summary: string;
}

export interface RiskTwinHandoffResult {
  status: "created" | "existing";
  case_key: string;
  asset: OperationsAsset;
  evidence_case: EvidenceCase;
  inspection_task: InspectionTask | null;
  operations_url: string;
  safety_statement: string;
}

export async function fetchOperationsOverview(): Promise<OperationsOverview> {
  const res = checkResponse(await fetch(apiUrl("/api/operations/overview")));
  return res.json();
}

export async function fetchOperationsDemo(): Promise<OperationsOverview> {
  const res = checkResponse(await fetch(apiUrl("/api/operations/demo")));
  return res.json();
}

export async function createFieldReport(
  input: FieldReportInput
): Promise<Record<string, unknown>> {
  const res = checkResponse(
    await authFetch(apiUrl("/api/operations/field-reports"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    })
  );
  return res.json();
}

export async function createInspectionTask(input: InspectionTaskInput): Promise<InspectionTask> {
  const res = checkResponse(
    await authFetch(apiUrl("/api/operations/inspection-tasks"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    })
  );
  return res.json();
}

export async function createRiskTwinHandoff(input: RiskTwinHandoffInput): Promise<RiskTwinHandoffResult> {
  const res = checkResponse(
    await authFetch(apiUrl("/api/operations/risk-twin-handoffs"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  );
  return res.json();
}

export async function fetchCentralAsiaBenchmark(): Promise<CentralAsiaBenchmarkReport> {
  const res = checkResponse(await fetch(apiUrl("/api/benchmark")));
  return res.json();
}
