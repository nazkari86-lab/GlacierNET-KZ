from fastapi import APIRouter, HTTPException

from app.storage.results import delete_result, get_history
from app.utils import path_to_url

router = APIRouter(prefix="/api", tags=["History"])


@router.get("/history")
def list_history(limit: int = 50, offset: int = 0):
    rows = get_history(limit, offset)
    for r in rows:
        for key in ("mask_path", "overlay_path", "image_path", "thumbnail_path"):
            if r.get(key):
                r[key] = path_to_url(r[key])
    return rows


@router.delete("/history/{task_id}")
def remove_history(task_id: str):
    if not delete_result(task_id):
        raise HTTPException(404, "History entry not found")
    return {"ok": True}
