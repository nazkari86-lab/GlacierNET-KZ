"""Product-facing ML workspace endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services.ml_workspace_service import (
    TRAINING_DATASET_PREVIEW,
    analyze_glacier,
    get_ml_case,
    list_ml_cases,
    ml_readiness,
    training_dataset_readiness,
    verify_weighted_training_pipeline,
)

router = APIRouter(prefix="/api/ml", tags=["ml-workspace"])


class GlacierAnalysisRequest(BaseModel):
    year: int = Field(2024, ge=2015, le=2024)
    model_name: str = "temporal_s2_terrain_s1"
    use_tta: bool = True
    context_m: int = Field(400, ge=0, le=2000)
    refresh: bool = False


class TrainingPipelineCheckRequest(BaseModel):
    refresh: bool = False


@router.get("/readiness")
def readiness():
    return ml_readiness()


@router.get("/training-dataset")
def training_dataset():
    return training_dataset_readiness()


@router.get("/training-dataset/preview", response_class=FileResponse)
def training_dataset_preview():
    if not TRAINING_DATASET_PREVIEW.is_file():
        raise HTTPException(404, "Training QA preview is unavailable")
    return FileResponse(
        TRAINING_DATASET_PREVIEW,
        media_type="image/png",
        filename="GlacierNET-KZ_training_QA.png",
    )


@router.post("/training-dataset/verify")
async def verify_training_dataset(request: TrainingPipelineCheckRequest):
    return await asyncio.to_thread(
        verify_weighted_training_pipeline,
        refresh=request.refresh,
    )


@router.post("/glaciers/{rgi_id}/analyze")
async def analyze(rgi_id: str, request: GlacierAnalysisRequest):
    return await asyncio.to_thread(
        analyze_glacier,
        rgi_id,
        year=request.year,
        model_name=request.model_name,
        use_tta=request.use_tta,
        context_m=request.context_m,
        refresh=request.refresh,
    )


@router.get("/cases")
def cases(limit: int = Query(20, ge=1, le=100)):
    return list_ml_cases(limit)


@router.get("/cases/{case_id}")
def case(case_id: str):
    return get_ml_case(case_id)
