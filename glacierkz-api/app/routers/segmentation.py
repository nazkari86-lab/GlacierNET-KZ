import asyncio
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas.responses import SegmentationResult
from app.services.segmentation_service import run_segmentation
from app.storage.results import get_result, save_result
from app.storage.uploads import save_upload
from app.utils import path_to_url

router = APIRouter(prefix="/api", tags=["Segmentation"])


@router.post("/predict", response_model=SegmentationResult)
async def predict(
    file: UploadFile = File(...),
    model_name: str = Form("unet"),
    use_tta: bool = Form(True),
    use_crf: bool = Form(False),
    ndsi_threshold: Optional[float] = Form(None),
    year: Optional[int] = Form(None),
):
    image_path = await save_upload(file)
    result = await asyncio.to_thread(run_segmentation, image_path, model_name, use_tta, use_crf, ndsi_threshold)
    if result["status"] == "completed":
        save_result(
            task_id=result["task_id"],
            model_name=model_name,
            image_path=str(image_path),
            mask_path=result["mask_path"],
            overlay_path=result["overlay_path"],
            area_km2=result["area_km2"],
            year=year,
        )
        result["mask_path"] = path_to_url(result["mask_path"])
        result["overlay_path"] = path_to_url(result["overlay_path"])
    return result


@router.get("/predict/{task_id}")
def get_prediction(task_id: str):
    r = get_result(task_id)
    if not r:
        raise HTTPException(404, "Task not found")
    if r.get("mask_path"):
        r["mask_path"] = path_to_url(r["mask_path"])
    if r.get("overlay_path"):
        r["overlay_path"] = path_to_url(r["overlay_path"])
    if r.get("image_path"):
        r["image_path"] = path_to_url(r["image_path"])
    if r.get("thumbnail_path"):
        r["thumbnail_path"] = path_to_url(r["thumbnail_path"])
    return r
