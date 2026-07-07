from fastapi import APIRouter, HTTPException

from app.schemas.requests import TrendRequest
from app.schemas.responses import TrendResult
from app.services.trend_service import compute_trend
from app.storage.results import get_result

router = APIRouter(prefix="/api", tags=["Trend"])


@router.post("/trend", response_model=TrendResult)
def trend_analysis(req: TrendRequest):
    areas = []
    for file_id in req.file_ids:
        r = get_result(file_id)
        if not r or r["area_km2"] is None:
            raise HTTPException(404, f"Result {file_id} not found or has no area data")
        areas.append(r["area_km2"])
    return compute_trend(req.years, areas, req.forecast_until)
