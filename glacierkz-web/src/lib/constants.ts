export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

/** WebSocket base (ws/wss) — uses current host when API URL is relative (unified gateway). */
export function getWebSocketOrigin(): string {
  if (typeof window !== "undefined") {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const explicit = process.env.NEXT_PUBLIC_WS_URL;
    if (explicit) return explicit.replace(/\/$/, "");
    if (!API_BASE_URL) return `${proto}//${window.location.host}`;
  }
  const http = API_BASE_URL || "http://localhost:8000";
  return http.replace(/^http/, "ws");
}

export const API_ENDPOINTS = {
  MODELS: "/api/models",
  PREDICT: "/api/predict",
  COMPARE: "/api/compare",
  TREND: "/api/trend",
  HISTORY: "/api/history",
  ANALYSIS_MODELS: "/api/analysis/models",
  ANALYZE: "/api/analysis/analyze",
  ADMIN_USERS: "/api/admin/users",
  ADMIN_AUDIT: "/api/admin/audit",
  ADMIN_SYSTEM: "/api/admin/system",
  PIPELINE: "/api/pipeline",
  PIPELINE_RUN: "/api/pipeline/run",
  DATASETS: "/api/datasets",
  DATASET_UPLOAD: "/api/datasets/upload",
  FILES: "/api/files",
  HEALTH: "/api/health",
  WS_EVENTS: "/ws/events",
} as const;

export const ROLES = {
  ADMIN: "admin",
  ANALYST: "analyst",
  VIEWER: "viewer",
} as const;

export type Role = (typeof ROLES)[keyof typeof ROLES];

export const ROLE_LABELS: Record<Role, string> = {
  admin: "Administrator",
  analyst: "Analyst",
  viewer: "Viewer",
};

export const ROLE_COLORS: Record<Role, string> = {
  admin: "bg-red-50 text-red-700 border-red-200",
  analyst: "bg-blue-50 text-blue-700 border-blue-200",
  viewer: "bg-gray-50 text-gray-700 border-gray-200",
};

export const STATUS = {
  ACTIVE: "active",
  INACTIVE: "inactive",
  PENDING: "pending",
} as const;

export type Status = (typeof STATUS)[keyof typeof STATUS];

export const STATUS_COLORS: Record<Status, string> = {
  active: "bg-emerald-50 text-emerald-700",
  inactive: "bg-gray-100 text-gray-500",
  pending: "bg-amber-50 text-amber-700",
};

export const PIPELINE_STAGES = [
  { id: "ingest", label: "Data Ingestion", icon: "database" },
  { id: "preprocess", label: "Preprocessing", icon: "filter" },
  { id: "segment", label: "Segmentation", icon: "layers" },
  { id: "validate", label: "Validation", icon: "check-circle" },
  { id: "export", label: "Export", icon: "download" },
] as const;

export type PipelineStageId = (typeof PIPELINE_STAGES)[number]["id"];

export const MODEL_TYPES = [
  "unet",
  "attention_unet",
  "random_forest",
  "ndsi_threshold",
  "ensemble",
] as const;

export type ModelType = (typeof MODEL_TYPES)[number];

export const SPECTRAL_BANDS = [
  "B02", "B03", "B04", "B05", "B06",
  "B07", "B08", "NDSI", "NDWI", "BSI", "EVI",
] as const;

export const BAND_DESCRIPTIONS: Record<string, string> = {
  B02: "Blue (490nm)",
  B03: "Green (560nm)",
  B04: "Red (665nm)",
  B05: "Red Edge 1 (705nm)",
  B06: "Red Edge 2 (740nm)",
  B07: "Red Edge 3 (783nm)",
  B08: "NIR (842nm)",
  NDSI: "Normalized Difference Snow Index",
  NDWI: "Normalized Difference Water Index",
  BSI: "Bare Soil Index",
  EVI: "Enhanced Vegetation Index",
};

export const PAGE_SIZES = [10, 25, 50, 100] as const;

export const DATE_FORMATS = {
  SHORT: "yyyy-MM-dd",
  LONG: "MMMM d, yyyy",
  FULL: "yyyy-MM-dd HH:mm:ss",
  ISO: "iso",
} as const;

export const MAX_FILE_SIZE_MB = 100;
export const ALLOWED_RASTER_TYPES = [".tif", ".tiff", ".jp2", ".nc"];
export const ALLOWED_IMAGE_TYPES = [".png", ".jpg", ".jpeg", ".webp"];
