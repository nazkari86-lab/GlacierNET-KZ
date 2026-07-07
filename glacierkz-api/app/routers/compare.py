import asyncio

from fastapi import APIRouter, File, Form, UploadFile

from app.services.segmentation_service import run_compare
from app.storage.uploads import save_upload
from app.utils import path_to_url

router = APIRouter(prefix="/api", tags=["Compare"])


@router.post("/compare")
async def compare_models(
    file: UploadFile = File(...),
    model_names: str = Form("unet,attention_unet,ndsi,ensemble"),
    use_tta: bool = Form(True),
    use_crf: bool = Form(False),
):
    names = [m.strip() for m in model_names.split(",")]
    image_path = await save_upload(file)
    result = await asyncio.to_thread(run_compare, image_path, names, use_tta, use_crf)
    for seg in result.get("segments", []):
        seg["mask_path"] = path_to_url(seg["mask_path"])
        seg["overlay_path"] = path_to_url(seg["overlay_path"])
    return result
