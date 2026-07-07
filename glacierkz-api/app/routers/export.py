import os
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.services.export_service import export_service
from app.storage.results import get_result

router = APIRouter(prefix="/api", tags=["Export"])

VALID_FORMATS = {"png", "npy", "csv", "json", "geojson", "geotiff", "tif", "tiff"}


def _resolve_format(fmt: Optional[str], format_alias: Optional[str]) -> str:
    """Accept both `fmt` and legacy `format` query params."""
    raw = (fmt or format_alias or "png").lower()
    aliases = {"geotiff": "geotiff", "tif": "geotiff", "tiff": "geotiff"}
    return aliases.get(raw, raw)


def _export_geotiff(mask: np.ndarray, task_id: str, image_path: Optional[str]) -> str:
    """Write mask as GeoTIFF, copying georeferencing from source image when possible."""
    try:
        import rasterio
        from rasterio.transform import from_bounds
    except ImportError as exc:
        raise HTTPException(
            501,
            "GeoTIFF export requires rasterio. Install with: pip install rasterio",
        ) from exc

    from app.config import RESULTS_DIR

    out_path = RESULTS_DIR / f"{task_id}_mask.tif"
    mask_2d = mask.squeeze()
    if mask_2d.ndim != 2:
        mask_2d = mask_2d[0] if mask_2d.ndim == 3 else mask_2d
    mask_uint8 = (mask_2d * 255).astype(np.uint8) if mask_2d.max() <= 1.0 else mask_2d.astype(np.uint8)

    transform = from_bounds(0, 0, mask_uint8.shape[1], mask_uint8.shape[0], mask_uint8.shape[1], mask_uint8.shape[0])
    crs = None

    if image_path and os.path.isfile(image_path):
        try:
            with rasterio.open(image_path) as src:
                if src.transform and src.transform != rasterio.Affine.identity():
                    transform = src.transform
                crs = src.crs
        except Exception:
            pass

    with rasterio.open(
        out_path,
        "w",
        driver="GTiff",
        height=mask_uint8.shape[0],
        width=mask_uint8.shape[1],
        count=1,
        dtype=mask_uint8.dtype,
        crs=crs,
        transform=transform,
        compress="lzw",
    ) as dst:
        dst.write(mask_uint8, 1)

    return str(out_path)


@router.get("/export/{task_id}")
def export_result(
    task_id: str,
    fmt: str = Query("png", description="Export format"),
    format: Optional[str] = Query(None, description="Alias for fmt (legacy frontend)"),
):
    resolved = _resolve_format(fmt, format)
    if resolved not in VALID_FORMATS:
        raise HTTPException(400, f"Unsupported format '{resolved}'. Valid: {', '.join(sorted(VALID_FORMATS))}")
    r = get_result(task_id)
    if not r or not r.get("mask_path"):
        raise HTTPException(404, "Result not found or mask unavailable")

    mask_path = r["mask_path"]
    if not os.path.isfile(mask_path):
        raise HTTPException(404, f"Mask file not found: {mask_path}")

    try:
        if mask_path.lower().endswith(".npy"):
            masks = np.load(mask_path)
        else:
            from PIL import Image as _Img

            masks = np.asarray(_Img.open(mask_path)).astype(np.float32) / 255.0

        if resolved == "png":
            meta = export_service.export_masks_png(masks)
            zip_path = meta["file_paths"][0] if meta["file_paths"] else None
            if not zip_path:
                raise HTTPException(500, "Export produced no files")
            return FileResponse(zip_path, filename=f"glacier_{task_id}.png", media_type="image/png")

        if resolved == "npy":
            meta = export_service.export_masks_numpy(masks)
            return FileResponse(
                meta["file_path"],
                filename=f"glacier_{task_id}.npy",
                media_type="application/octet-stream",
            )

        if resolved == "json":
            meta = export_service.export_predictions_json({"task_id": task_id, "mask_shape": list(masks.shape)})
            return FileResponse(meta["file_path"], filename=f"glacier_{task_id}.json", media_type="application/json")

        if resolved == "geotiff":
            out_path = _export_geotiff(masks, task_id, r.get("image_path"))
            return FileResponse(out_path, filename=f"glacier_{task_id}.tif", media_type="image/tiff")

        raise HTTPException(400, f"Format '{resolved}' requires additional parameters")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/export/{task_id}/stats")
def export_stats(task_id: str):
    r = get_result(task_id)
    if not r:
        raise HTTPException(404, "Result not found")
    return {"task_id": task_id, "available_formats": sorted(VALID_FORMATS)}
