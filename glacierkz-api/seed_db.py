#!/usr/bin/env python3
"""
Seed the history database by running segmentation on all available satellite images.
"""
import os
import re
import sys
import time
from pathlib import Path

# --- Bootstrap paths ---
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

os.environ.setdefault("CORE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("DATA_DIR", str(SCRIPT_DIR))
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

from app.services.segmentation_service import run_segmentation
from app.storage.results import get_history, save_result


def extract_year(path: Path) -> int | None:
    m = re.search(r"(\d{4})", path.stem)
    return int(m.group(1)) if m else None


def detect_num_bands(path: Path) -> int:
    import rasterio
    with rasterio.open(path) as src:
        return src.count


def seed():
    raw_dir = PROJECT_ROOT / "data" / "raw"
    images = sorted(raw_dir.rglob("*.tif"))

    if not images:
        print("No satellite images found under", raw_dir)
        return

    print(f"Found {len(images)} satellite images")

    for i, img_path in enumerate(images, 1):
        year = extract_year(img_path)
        source = "sentinel2" if "sentinel" in img_path.name.lower() else "landsat"
        n_bands = detect_num_bands(img_path)

        print(f"\n[{i}/{len(images)}] {img_path.name} ({source}, {n_bands} bands, year={year})")

        # Choose model strategy based on available bands
        strategies = []
        if n_bands >= 11:
            strategies = ["unet", "attention_unet", "ensemble", "rf", "ndsi"]
        elif n_bands >= 3:
            strategies = ["rf", "ndsi"]
        else:
            strategies = ["ndsi"]

        for model_name in strategies:
            print(f"  → Trying model: {model_name} ...")
            try:
                result = run_segmentation(
                    image_path=img_path,
                    model_name=model_name,
                    use_tta=True,
                    use_crf=False,
                )
                if result.get("status") == "completed":
                    save_result(
                        task_id=result["task_id"],
                        model_name=model_name,
                        image_path=str(img_path),
                        mask_path=result["mask_path"],
                        overlay_path=result["overlay_path"],
                        area_km2=result["area_km2"],
                        year=year,
                    )
                    print(f"    ✓ task_id={result['task_id']} area={result['area_km2']} km²")
                    break
                else:
                    print(f"    ✗ failed: {result.get('error', 'unknown error')}")
            except Exception as e:
                print(f"    ✗ exception: {e}")
                import traceback
                traceback.print_exc()

        time.sleep(0.5)

    # Show summary
    print("\n" + "=" * 60)
    print("DATABASE SUMMARY")
    print("=" * 60)
    entries = get_history(limit=100)
    if entries:
        print(f"Total history entries: {len(entries)}")
        for e in entries:
            print(f"  #{e['id']} | {e['task_id']} | {e['model_name']} | "
                  f"year={e['year']} | {e['area_km2']} km² | {e['created_at']}")
    else:
        print("No entries in database!")


if __name__ == "__main__":
    seed()
