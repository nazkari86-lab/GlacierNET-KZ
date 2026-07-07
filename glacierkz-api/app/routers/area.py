from fastapi import APIRouter, HTTPException

from app.schemas.responses import AreaResponse
from app.services.area_service import calc_area_from_mask

router = APIRouter(prefix="/api", tags=["Area"])


@router.post("/area", response_model=AreaResponse)
def calculate_area(mask_path: str, pixel_size_m: float = 10.0):
    try:
        return calc_area_from_mask(mask_path, pixel_size_m)
    except Exception as e:
        raise HTTPException(400, str(e))
