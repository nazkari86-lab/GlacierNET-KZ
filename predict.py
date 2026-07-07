#!/usr/bin/env python3
"""GlacierNET-KZ: Run trained models on real satellite TIFs by year.

Usage:
    python predict.py --year 2020
    python predict.py --year 2000 --models ndsi unet rf --save
    python predict.py --list-years
"""


import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


import argparse
import json
import warnings

import numpy as np
import rasterio

import src.config as config
from src.data_loader import _append_sentinel2_indices
from src.metrics import pixels_to_area_km2

warnings.filterwarnings("ignore")

S2_FILES = sorted(config.DATA_RAW_SENTINEL2.glob("*.tif"))
LS_FILES = sorted(config.DATA_RAW_LANDSAT.glob("*.tif"))

# column index in 11-ch array for each band
B2, B3, B4, B8, B8A, B11, B12, NDSI, NDWI, BSI, EVI = range(11)


def _load_sentinel2(filepath: Path) -> np.ndarray:
    """Load Sentinel-2 TIF → 11-channel normalized array [0,1] for reflectance, [-1,1] for indices."""
    with rasterio.open(filepath) as src:
        img = src.read()
    img = np.moveaxis(img, 0, -1).astype(np.float32)

    n_bands = img.shape[-1]
    if n_bands == 7:
        # raw reflectance only (e.g. sentinel2_2020.tif) — normalise + compute indices
        img = np.clip(img / config.S2_SCALE, 0.0, 1.0)
        img = _append_sentinel2_indices(img)
    elif n_bands == 11:
        # already has indices appended (e.g. sentinel2_2016/2017.tif)
        img[..., :7] = np.clip(img[..., :7] / config.S2_SCALE, 0.0, 1.0)
        img[..., 7:] = np.clip(img[..., 7:], -1.0, 1.0)
    else:
        raise ValueError(f"Sentinel-2 TIF has {n_bands} bands, expected 7 or 11")
    return np.nan_to_num(img).astype(np.float32)


def _load_landsat(filepath: Path) -> np.ndarray:
    """Load Landsat TIF → 11-channel array using ALL available bands.

    Landsat GeoTIFFs have 9 bands: 5 reflectance (B2,B3,B4,B8,B11) +
    4 pre-computed indices (NDSI, NDWI, BSI, EVI). We map to the 11-channel
    Sentinel-2 format by filling missing bands (B8A, B12) with the closest
    available Landsat proxies — B8 for B8A and B11 for B12 — so no channel
    is left zero. EVI in the source file is numerically corrupt, so we
    recompute it from reflectance and clip to [-1, 1].
    """
    with rasterio.open(filepath) as src:
        img = src.read()
    img = np.moveaxis(img, 0, -1).astype(np.float32)

    # 5 reflectance bands (scaled from DN to [0, 1])
    refl = np.clip(img[..., :5] / config.S2_SCALE, 0.0, 1.0)
    b2, b3, b4, b8, b11 = [refl[..., i] for i in range(5)]

    # Pre-computed indices from the file (bands 5-7 are valid; band 8 EVI garbage)
    ls_ndsi = np.clip(img[..., 5], -1.0, 1.0)
    ls_ndwi = np.clip(img[..., 6], -1.0, 1.0)
    ls_bsi = np.clip(img[..., 7], -1.0, 1.0)

    eps = 1e-8
    evi = 2.5 * (b8 - b4) / (b8 + 6.0 * b4 - 7.5 * b2 + 1.0 + eps)
    evi = np.clip(evi, -1.0, 1.0)

    # Fill missing S2 bands with closest Landsat proxy
    b8a = b8   # Landsat NIR broad band covers S2 B8A wavelength
    b12 = b11  # Landsat SWIR2 not in this TIF → use SWIR1 as proxy

    indices = np.stack([ls_ndsi, ls_ndwi, ls_bsi, evi], axis=-1)

    H, W = refl.shape[:2]
    out = np.zeros((H, W, 11), dtype=np.float32)
    out[..., B2] = b2
    out[..., B3] = b3
    out[..., B4] = b4
    out[..., B8] = b8
    out[..., B8A] = b8a
    out[..., B11] = b11
    out[..., B12] = b12
    out[..., NDSI:] = indices
    return out


def _load_tif(year: int) -> tuple[np.ndarray, dict]:
    """Load and prepare satellite data for a given year.

    Returns (11-channel array, metadata dict with H, W, pixel_area_m2, source).
    """
    s2_path = config.DATA_RAW_SENTINEL2 / f"sentinel2_{year}.tif"
    ls_path = config.DATA_RAW_LANDSAT / f"landsat_{year}.tif"

    if s2_path.exists():
        with rasterio.open(s2_path) as src:
            meta = dict(H=src.height, W=src.width,
                        pixel_area=abs(src.res[0] * src.res[1]),
                        crs=src.crs, source="Sentinel-2")
        img = _load_sentinel2(s2_path)
    elif ls_path.exists():
        with rasterio.open(ls_path) as src:
            meta = dict(H=src.height, W=src.width,
                        pixel_area=abs(src.res[0] * src.res[1]),
                        crs=src.crs, source="Landsat")
        img = _load_landsat(ls_path)
    else:
        available = list_available_years()
        raise FileNotFoundError(f"No data for year {year}. Available: {available}")
    return img, meta


def list_available_years() -> list[dict]:
    """Return list of {year, source} for all available TIF files."""
    import re
    years = []
    for p in S2_FILES:
        m = re.search(r"sentinel2_(\d{4})", p.name)
        if m:
            years.append({"year": int(m.group(1)), "source": "Sentinel-2"})
    for p in LS_FILES:
        m = re.search(r"landsat_(\d{4})", p.name)
        if m:
            years.append({"year": int(m.group(1)), "source": "Landsat"})
    return sorted(years, key=lambda x: x["year"])


# ─── NDSI ──────────────────────────────────────────────────────────────────


def run_ndsi(img: np.ndarray, threshold: float = 0.4) -> np.ndarray:
    """Binary glacier mask via NDSI threshold."""
    return (img[..., NDSI] > threshold).astype(np.uint8)


# ─── Random Forest ─────────────────────────────────────────────────────────


def load_rf():
    import joblib
    path = config.MODELS_DIR / "random_forest.pkl"
    if not path.exists():
        raise FileNotFoundError(f"RF model not found at {path}")
    return joblib.load(path)


def run_rf(model, img: np.ndarray, chunk_size: int = 500000) -> np.ndarray:
    """Random forest pixel-wise classification on 11-channel input.

    Processes pixels in chunks of `chunk_size` to bound peak memory
    and allow progress visibility on large images.
    """
    H, W = img.shape[:2]
    features = img.reshape(-1, img.shape[-1])
    n_samples = features.shape[0]
    pred = np.empty(n_samples, dtype=np.uint8)
    for start in range(0, n_samples, chunk_size):
        end = min(start + chunk_size, n_samples)
        pred[start:end] = model.predict(features[start:end])
        progress = min(end / n_samples * 100, 100)
        if end % (chunk_size * 5) == 0 or end == n_samples:
            print(f"\r  [2/3] Random Forest ... {progress:.0f}%", end="", flush=True)
    print(f"\r  [2/3] Random Forest ... done{' ' * 15}")
    return pred.reshape(H, W).astype(np.uint8)


# ─── U-Net ─────────────────────────────────────────────────────────────────


def load_unet():
    try:
        from tensorflow import keras

        from src.models import build_unet
    except ImportError:
        print("  ⚠ TensorFlow not installed — skipping U-Net")
        return None
    path = config.MODELS_DIR / "unet_best.h5"
    if not path.exists():
        print(f"  ⚠ U-Net model not found at {path} — skipping")
        return None
    model = build_unet(input_shape=(None, None, config.N_CHANNELS))
    model.load_weights(str(path))
    return model


def run_unet(model, img: np.ndarray, use_tta: bool = False) -> np.ndarray:
    """U-Net prediction via sliding window with optional TTA."""
    from src.models import predict_full_image, tta_predict
    if use_tta:
        _prob, mask = tta_predict(model, img)
    else:
        _prob, mask = predict_full_image(img, model)
    return mask


# ─── Main ──────────────────────────────────────────────────────────────────


def predict_year(year: int, models: list[str] = ("ndsi", "rf", "unet"),
                 use_tta: bool = False, save: bool = False) -> dict:
    """Run selected models on a given year and return results."""
    print(f"\n{'='*60}")
    print(f"  Year: {year}")
    print(f"  Models: {', '.join(models)}")
    print(f"{'='*60}")

    img, meta = _load_tif(year)
    H, W, pix_area = meta["H"], meta["W"], meta["pixel_area"]
    print(f"  Source: {meta['source']}")
    print(f"  Size: {W}×{H} pixels ≈ {pixels_to_area_km2(H * W, pix_area):.1f} km² total")
    print()

    results = {}
    out_dir = ROOT / "predictions" / str(year)
    if save:
        out_dir.mkdir(parents=True, exist_ok=True)

    if "ndsi" in models:
        print("  [1/3] NDSI threshold ...", end=" ", flush=True)
        mask = run_ndsi(img)
        area_km2 = pixels_to_area_km2(mask.sum(), pix_area)
        results["ndsi"] = {"area_km2": float(f"{area_km2:.2f}"),
                           "glacier_pixels": int(mask.sum()),
                           "total_pixels": H * W}
        print(f"glacier area = {area_km2:.2f} km²")
        if save:
            _save_single_mask(year, mask, meta, out_dir / "ndsi_mask.tif")

    if "rf" in models:
        rf_model = load_rf()
        mask = run_rf(rf_model, img)
        area_km2 = pixels_to_area_km2(mask.sum(), pix_area)
        results["rf"] = {"area_km2": float(f"{area_km2:.2f}"),
                         "glacier_pixels": int(mask.sum()),
                         "total_pixels": H * W}
        print(f"  glacier area = {area_km2:.2f} km²")
        if save:
            _save_single_mask(year, mask, meta, out_dir / "rf_mask.tif")

    if "unet" in models:
        label = "U-Net" + (" (TTA)" if use_tta else "")
        print(f"  [3/3] {label} ...", end=" ", flush=True)
        unet_model = load_unet()
        if unet_model is None:
            print("skipped")
        else:
            mask = run_unet(unet_model, img, use_tta=use_tta)
            area_km2 = pixels_to_area_km2(mask.sum(), pix_area)
            results["unet"] = {"area_km2": float(f"{area_km2:.2f}"),
                               "glacier_pixels": int(mask.sum()),
                               "total_pixels": H * W}
            print(f"glacier area = {area_km2:.2f} km²")
            if save:
                _save_single_mask(year, mask, meta, out_dir / "unet_mask.tif")

    if save and results:
        _save_results_json(results, out_dir)
        _save_overlay(year, img, results, meta, out_dir)
        print(f"  → predictions saved in {out_dir}/")

    return results


def _save_single_mask(year: int, mask: np.ndarray, meta: dict, dst: Path):
    with rasterio.open(
        dst, "w", driver="GTiff", height=meta["H"], width=meta["W"],
        count=1, dtype=rasterio.uint8, crs=meta["crs"],
    ) as out:
        out.write(mask, 1)


def _save_results_json(results: dict, out_dir: Path):
    with open(out_dir / "results.json", "w") as f:
        json.dump(results, f, indent=2)


def _save_overlay(year: int, img: np.ndarray, results: dict, meta: dict, out_dir: Path):
    """Save overlay figure without re-running models (uses saved masks)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        n_models = len(results)
        fig, axes = plt.subplots(1, n_models + 1, figsize=(6 * (n_models + 1), 6))
        rgb = np.clip(np.stack([img[..., B4], img[..., B3], img[..., B2]], axis=-1), 0, 1)
        axes[0].imshow(rgb)
        axes[0].set_title(f"{year} — RGB")
        axes[0].axis("off")

        for i, name in enumerate(results):
            mask_path = out_dir / f"{name}_mask.tif"
            if mask_path.exists():
                with rasterio.open(mask_path) as src:
                    mask = src.read(1)
            else:
                mask = np.zeros((meta["H"], meta["W"]), dtype=np.uint8)

            axes[i + 1].imshow(rgb, alpha=0.6)
            axes[i + 1].imshow(mask, cmap="Reds", alpha=0.4 if mask.sum() > 0 else 1.0)
            axes[i + 1].set_title(f"{name.upper()} — {results[name]['area_km2']} km²")
            axes[i + 1].axis("off")

        plt.tight_layout()
        plt.savefig(out_dir / "overlay.png", dpi=150, bbox_inches="tight")
        plt.close()
        print(f"  → overlay saved to {out_dir / 'overlay.png'}")
    except Exception as e:
        print(f"  (skipping overlay: {e})")


def main():
    parser = argparse.ArgumentParser(
        description="GlacierNET-KZ: predict glacier extent from satellite imagery")
    parser.add_argument("--year", type=int, help="Target year (e.g. 2020)")
    parser.add_argument("--models", nargs="+", default=["ndsi", "rf", "unet"],
                        choices=["ndsi", "rf", "unet"],
                        help="Models to run (default: all)")
    parser.add_argument("--tta", action="store_true",
                        help="Use test-time augmentation for U-Net")
    parser.add_argument("--save", action="store_true",
                        help="Save prediction masks and overlay plot")
    parser.add_argument("--list-years", action="store_true",
                        help="Show available years and exit")
    args = parser.parse_args()

    if args.list_years:
        years = list_available_years()
        print(f"\nAvailable data ({len(years)} years):")
        print(f"  {'Year':<8} Source")
        print(f"  {'─'*20}")
        for y in years:
            print(f"  {y['year']:<8} {y['source']}")
        return

    if args.year is None:
        parser.print_help()
        return

    results = predict_year(args.year, models=args.models,
                           use_tta=args.tta, save=args.save)

    print(f"\n{'─'*40}")
    print("Summary:")
    for name, r in results.items():
        print(f"  {name.upper():>10}: {r['area_km2']} km²")
    print(f"{'─'*40}\n")


if __name__ == "__main__":
    main()
