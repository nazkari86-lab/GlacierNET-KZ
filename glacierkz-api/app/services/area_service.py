from pathlib import Path

import numpy as np
from PIL import Image

from app.utils import resolve_core_dir

CORE_DIR = resolve_core_dir(__file__)

from src.data_loader import read_raster_meta  # noqa: E402
from src.metrics import pixels_to_area_km2  # noqa: E402


def calc_area_from_mask(mask_path: str, pixel_size_m: float = 10.0) -> dict:
    mask_path = Path(mask_path)
    ext = mask_path.suffix.lower()

    if ext in (".tif", ".tiff"):
        _, _, shape, pixel_area_m2 = read_raster_meta(mask_path)
        import rasterio

        with rasterio.open(mask_path) as src:
            mask = src.read(1)
        glacier_pixels = int((mask > 0).sum())
        area_km2 = pixels_to_area_km2(glacier_pixels, pixel_area_m2)
        return {
            "area_km2": round(area_km2, 4),
            "pixel_count": glacier_pixels,
            "pixel_size_m": round(np.sqrt(pixel_area_m2), 2),
        }

    mask = np.array(Image.open(mask_path).convert("L"))
    glacier_pixels = int((mask > 127).sum())
    area_m2 = glacier_pixels * (pixel_size_m**2)
    return {
        "area_km2": round(area_m2 / 1e6, 4),
        "pixel_count": glacier_pixels,
        "pixel_size_m": pixel_size_m,
    }
