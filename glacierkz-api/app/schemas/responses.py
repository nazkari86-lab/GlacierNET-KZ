from typing import Optional

from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    name: str
    display_name: str
    description: str
    supports_tta: bool
    supports_crf: bool
    supports_uncertainty: bool
    channel_count: Optional[int] = None
    feature_schema: list[str] = Field(default_factory=list)
    decision_threshold: Optional[float] = None
    inference_variant: Optional[str] = None
    evidence_tier: Optional[str] = None
    recommended: bool = False
    year_range: Optional[list[Optional[int]]] = None


class SegmentationResult(BaseModel):
    task_id: str
    status: str  # pending, processing, completed, failed
    mask_path: Optional[str] = None
    overlay_path: Optional[str] = None
    area_km2: Optional[float] = None
    error: Optional[str] = None
    model_name: Optional[str] = None
    geotiff_path: Optional[str] = None
    probability_path: Optional[str] = None
    probability_geotiff_path: Optional[str] = None
    entropy_path: Optional[str] = None
    entropy_geotiff_path: Optional[str] = None
    decision_threshold: Optional[float] = None
    inference_variant: Optional[str] = None
    feature_schema: list[str] = Field(default_factory=list)
    uncertain_pixel_fraction: Optional[float] = None
    warnings: list[str] = Field(default_factory=list)


class CompareSegment(BaseModel):
    model_name: str
    mask_path: str
    overlay_path: str
    area_km2: Optional[float] = None


class CompareResult(BaseModel):
    task_id: str
    segments: list[CompareSegment]


class AreaResponse(BaseModel):
    area_km2: float
    pixel_count: int
    pixel_size_m: float


class UncertaintyResult(BaseModel):
    task_id: str
    mean_path: str
    std_path: str
    entropy_path: str


class TrendPoint(BaseModel):
    year: int
    area_km2: float


class ForecastPoint(TrendPoint):
    ci_lower: float = 0.0
    ci_upper: float = 0.0


class TrendResult(BaseModel):
    data: list[TrendPoint]
    forecast: list[ForecastPoint]
    loss_rate_km2_per_year: float
    total_loss_percent: float
    r_squared: float
    p_value: float = 0.0
    significant: bool = False


class HistoryItem(BaseModel):
    id: int
    task_id: str
    model_name: str
    area_km2: Optional[float] = None
    year: Optional[int] = None
    created_at: str
    thumbnail_path: Optional[str] = None
    status: str


class ExportResponse(BaseModel):
    file_path: str
    format: str


class LLMAnalyzeResponse(BaseModel):
    content: str
    provider: str
    model: str
    fallback_used: bool = False


class LLMModelInfo(BaseModel):
    id: str
    name: str = ""
    free: bool = False


class LLMProviderInfo(BaseModel):
    provider: str
    label: str
    models: list[LLMModelInfo]
    needs_key: bool


class ErrorResponse(BaseModel):
    detail: str
