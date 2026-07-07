import asyncio

from fastapi import APIRouter, File, Form, UploadFile

from app.services.segmentation_service import run_uncertainty
from app.storage.uploads import save_upload
from app.utils import path_to_url

router = APIRouter(prefix="/api", tags=["Uncertainty"])


@router.post("/uncertainty")
async def uncertainty(
    file: UploadFile = File(...),
    model_name: str = Form("unet"),
    n_samples: int = Form(10),
):
    image_path = await save_upload(file)
    result = await asyncio.to_thread(run_uncertainty, image_path, model_name, n_samples)
    for key in ("mean_path", "std_path", "entropy_path"):
        if result.get(key):
            result[key] = path_to_url(result[key])
    return result
