import logging
import threading
import uuid
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from app.config import RESULTS_DIR
from app.utils import resolve_core_dir

logger = logging.getLogger(__name__)

CORE_DIR = resolve_core_dir(__file__)

import src.config as core_config  # noqa: E402
from src.data_loader import _append_sentinel2_indices, read_raster_meta  # noqa: E402
from src.data_loader import load_image as core_load_image  # noqa: E402
from src.metrics import pixels_to_area_km2  # noqa: E402
from src.model_registry import MODEL_SPECS, get_model_spec  # noqa: E402
from src.model_security import verify_trusted_model  # noqa: E402
from src.multimodal_features import build_runtime_feature_stack  # noqa: E402

_MODEL_CACHE: dict[str, object] = {}
_RF_MODEL = None
_cache_lock = threading.Lock()


def _metric_pixel_area(transform, crs) -> float | None:
    """Return affine pixel area in m² only when CRS units are known metric."""
    if transform is None or crs is None or not crs.is_projected:
        return None
    try:
        _, unit_to_metre = crs.linear_units_factor
        factor = float(unit_to_metre)
    except (AttributeError, TypeError, ValueError):
        return None
    affine_area = abs(float(transform.a * transform.e - transform.b * transform.d))
    return affine_area * factor * factor


def _lazy_load_tf():
    import tensorflow as tf

    return tf


def _lazy_load_models():
    from src.models import (
        build_attention_unet,
        build_model_by_name,
        build_unet,
        get_custom_objects,
        list_models,
    )

    return build_unet, build_attention_unet, get_custom_objects, build_model_by_name, list_models


def _load_keras_model(arch_name: str):
    cache_key = f"keras_{arch_name}"
    with _cache_lock:
        if cache_key in _MODEL_CACHE:
            return _MODEL_CACHE[cache_key]

    tf = _lazy_load_tf()
    build_unet, build_attention_unet, custom_objs, build_model_by_name, list_models = _lazy_load_models()

    available_keras = list_models()

    if arch_name not in available_keras:
        raise ValueError(f"Unknown Keras architecture: {arch_name}. Available: {available_keras}")

    input_shape = (core_config.PATCH_SIZE, core_config.PATCH_SIZE, core_config.N_CHANNELS)

    weights_map = {
        "unet": "unet_best.h5",
        "attention_unet": "attention_unet_best.h5",
        "unet_plus_plus": "unet_plus_plus_best.h5",
    }

    weights_name = weights_map.get(arch_name)
    if weights_name is None:
        raise ValueError(f"No weights mapping for architecture: {arch_name}")

    weights_path = core_config.MODELS_DIR / weights_name
    if not weights_path.exists():
        raise FileNotFoundError(
            f"Weights for {arch_name} not found at {weights_path}. "
            f"Train the model or choose an available architecture "
            f"(GET /api/models lists models with weights on disk)."
        )

    verify_trusted_model(weights_path, root=core_config.PROJECT_ROOT)
    model = build_model_by_name(arch_name, input_shape)
    model.load_weights(str(weights_path))
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=core_config.LEARNING_RATE),
        loss=custom_objs.get("combined_loss"),
    )
    with _cache_lock:
        _MODEL_CACHE[cache_key] = model
    return model


def _load_temporal_model(model_name: str):
    cache_key = f"saved_model_{model_name}"
    with _cache_lock:
        if cache_key in _MODEL_CACHE:
            return _MODEL_CACHE[cache_key]
    spec = get_model_spec(model_name)
    model_path = spec.artifact_path(core_config.PROJECT_ROOT)
    if model_path is None or not model_path.exists():
        raise FileNotFoundError(f"SavedModel is missing for {model_name}: {model_path}")
    verify_trusted_model(model_path, root=core_config.PROJECT_ROOT)
    tf = _lazy_load_tf()
    model = tf.keras.models.load_model(model_path, compile=False)
    actual_channels = int(model.input_shape[-1])
    if actual_channels != spec.channel_count:
        raise ValueError(
            f"Model signature mismatch for {model_name}: artifact expects {actual_channels} "
            f"channels, registry declares {spec.channel_count}"
        )
    with _cache_lock:
        _MODEL_CACHE[cache_key] = model
    return model


def _load_rf_model():
    global _RF_MODEL
    with _cache_lock:
        if _RF_MODEL is not None:
            return _RF_MODEL
    import pickle

    rf_path = core_config.MODELS_DIR / "random_forest.pkl"
    if not rf_path.exists():
        raise FileNotFoundError(f"Random Forest model not found at {rf_path}.")
    verify_trusted_model(rf_path, root=core_config.PROJECT_ROOT)
    with open(rf_path, "rb") as f:
        model = pickle.load(f)  # nosec B301
    with _cache_lock:
        _RF_MODEL = model
    return _RF_MODEL


def _load_image(path: Path) -> tuple[np.ndarray, Optional[dict]]:
    ext = path.suffix.lower()
    if ext in (".tif", ".tiff"):
        try:
            img = core_load_image(path)
            transform, crs, shape, _ = read_raster_meta(path)
            pixel_area = _metric_pixel_area(transform, crs)
            import rasterio

            with rasterio.open(path) as source:
                descriptions = tuple(value or "" for value in source.descriptions)
            return img, {
                "pixel_area_m2": pixel_area,
                "transform": transform,
                "crs": crs,
                "shape": shape,
                "band_descriptions": descriptions,
            }
        except Exception:
            import rasterio

            with rasterio.open(path) as src:
                arr = src.read()
                arr = np.moveaxis(arr, 0, -1).astype(np.float32)
                transform = src.transform
                crs = src.crs
                descriptions = tuple(value or "" for value in src.descriptions)
            n_reflectance = min(7, arr.shape[-1])
            finite_reflectance = arr[..., :n_reflectance][np.isfinite(arr[..., :n_reflectance])]
            scale = 10000.0 if finite_reflectance.size and float(np.max(np.abs(finite_reflectance))) > 2.0 else 1.0
            arr[..., :n_reflectance] = np.clip(arr[..., :n_reflectance] / scale, 0.0, 1.0)
            if arr.shape[-1] > 7:
                arr[..., 7:] = np.clip(arr[..., 7:], -1.0, 1.0)
            arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=0.0)
            return arr, {
                "pixel_area_m2": _metric_pixel_area(transform, crs),
                "transform": transform,
                "crs": crs,
                "shape": arr.shape[:2],
                "band_descriptions": descriptions,
            }
    img = Image.open(path).convert("RGB")
    arr = np.array(img).astype(np.float32) / 255.0
    return arr, None


def _save_mask(mask: np.ndarray, name: str) -> Path:
    save_path = RESULTS_DIR / f"{name}.png"
    Image.fromarray((mask * 255).astype(np.uint8)).save(save_path)
    return save_path


def _save_geotiff(mask: np.ndarray, name: str, meta: Optional[dict]) -> Path | None:
    """Preserve georeferencing for GIS/QGIS use instead of returning PNG only."""
    if not meta or meta.get("transform") is None or meta.get("crs") is None:
        return None
    import rasterio

    save_path = RESULTS_DIR / f"{name}.tif"
    with rasterio.open(
        save_path,
        "w",
        driver="GTiff",
        height=mask.shape[0],
        width=mask.shape[1],
        count=1,
        dtype="uint8",
        crs=meta["crs"],
        transform=meta["transform"],
        compress="deflate",
    ) as destination:
        destination.write(mask.astype(np.uint8), 1)
        destination.set_band_description(1, "glacier_mask")
    return save_path


def _save_float_geotiff(
    values: np.ndarray,
    name: str,
    meta: Optional[dict],
    *,
    description: str,
) -> Path | None:
    if not meta or meta.get("transform") is None or meta.get("crs") is None:
        return None
    import rasterio

    save_path = RESULTS_DIR / f"{name}.tif"
    with rasterio.open(
        save_path,
        "w",
        driver="GTiff",
        height=values.shape[0],
        width=values.shape[1],
        count=1,
        dtype="float32",
        crs=meta["crs"],
        transform=meta["transform"],
        compress="deflate",
        nodata=np.nan,
    ) as destination:
        destination.write(values.astype(np.float32), 1)
        destination.set_band_description(1, description)
    return save_path


def _save_overlay(image: np.ndarray, mask: np.ndarray, name: str) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    save_path = RESULTS_DIR / f"{name}_overlay.png"
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))
    if image.ndim == 3 and image.shape[-1] >= 3:
        rgb = image[..., core_config.RGB_INDICES]
        img_display = (np.clip(rgb, 0, 1) * 255).astype(np.uint8) if rgb.max() <= 1 else rgb.astype(np.uint8)
        ax1.imshow(img_display)
    else:
        ax1.imshow(image, cmap="gray")
    ax1.set_title("Original")
    ax1.axis("off")
    ax2.imshow(mask, cmap="gray")
    ax2.set_title("Glacier Mask")
    ax2.axis("off")
    overlay = np.zeros((*mask.shape, 4), dtype=np.uint8)
    overlay[..., 1] = 100
    overlay[..., 2] = 255
    overlay[..., 3] = (mask * 128).astype(np.uint8)
    if image.ndim == 3 and image.shape[-1] >= 3:
        ax3.imshow(img_display)
        ax3.imshow(overlay)
    ax3.set_title("Overlay")
    ax3.axis("off")
    try:
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    finally:
        plt.close()
    return save_path


DEFAULT_PIXEL_SIZE_M = 10.0


def _calc_area(
    mask: np.ndarray,
    pixel_area_m2: Optional[float] = None,
    *,
    allow_default: bool = True,
) -> float | None:
    glacier_pixels = int(mask.sum())
    if pixel_area_m2 is None and allow_default:
        pixel_area_m2 = DEFAULT_PIXEL_SIZE_M**2
    if pixel_area_m2 is not None:
        return round(pixels_to_area_km2(glacier_pixels, pixel_area_m2), 4)
    return None


_KERAS_MODELS = {"unet", "attention_unet", "unet_plus_plus"}
_TEMPORAL_MODELS = {name for name, spec in MODEL_SPECS.items() if spec.evidence_tier == "silver_temporal_holdout"}


def run_segmentation(
    image_path: Path,
    model_name: str = "unet",
    use_tta: bool = True,
    use_crf: bool = False,
    ndsi_threshold: Optional[float] = None,
    year: Optional[int] = None,
) -> dict:
    task_id = uuid.uuid4().hex[:12]
    image, meta = _load_image(image_path)
    pixel_area = meta.get("pixel_area_m2") if meta else DEFAULT_PIXEL_SIZE_M**2

    mask = np.zeros((image.shape[0], image.shape[1]), dtype=np.float32)
    inference_details: dict[str, object] = {}

    try:
        if model_name == "ndsi":
            mask = _run_ndsi(image, threshold=ndsi_threshold or core_config.BEST_NDSI_THRESHOLD)
        elif model_name == "rf":
            mask = _run_rf(image)
        elif model_name in _KERAS_MODELS:
            mask = _run_unet(image, model_name, use_tta, use_crf)
        elif model_name in _TEMPORAL_MODELS:
            mask, inference_details = _run_temporal_model(image, meta, model_name, use_tta, year)
        elif model_name == "ensemble":
            mask = _run_ensemble(image, use_crf)
        else:
            return {"task_id": task_id, "status": "failed", "error": f"Unknown model: {model_name}"}
    except Exception as e:
        return {"task_id": task_id, "status": "failed", "error": str(e)}

    if mask.dtype != np.float32:
        mask = mask.astype(np.float32)
    if mask.max() > 1.0:
        mask = mask / 255.0

    mask_path = _save_mask(mask, f"{task_id}_mask")
    geotiff_path = _save_geotiff(mask, f"{task_id}_mask", meta)
    probability = inference_details.pop("_probability", None)
    entropy = inference_details.pop("_entropy", None)
    probability_path = None
    probability_geotiff_path = None
    entropy_path = None
    entropy_geotiff_path = None
    if isinstance(probability, np.ndarray):
        probability_path = _save_mask(probability, f"{task_id}_probability")
        probability_geotiff_path = _save_float_geotiff(
            probability,
            f"{task_id}_probability",
            meta,
            description="glacier_probability",
        )
    if isinstance(entropy, np.ndarray):
        entropy_path = _save_mask(entropy / np.log(2.0), f"{task_id}_entropy")
        entropy_geotiff_path = _save_float_geotiff(
            entropy,
            f"{task_id}_entropy",
            meta,
            description="predictive_entropy_nats",
        )
    overlay_path = _save_overlay(image, mask, task_id)
    area_km2 = _calc_area(mask, pixel_area, allow_default=meta is None)
    if meta and pixel_area is None:
        inference_details.setdefault("warnings", [])
        inference_details["warnings"].append(
            "Area is omitted because the uploaded raster CRS does not have verified metre units."
        )

    result = {
        "task_id": task_id,
        "status": "completed",
        "mask_path": str(mask_path),
        "overlay_path": str(overlay_path),
        "area_km2": round(area_km2, 4) if area_km2 is not None else None,
        "model_name": model_name,
    }
    if geotiff_path is not None:
        result["geotiff_path"] = str(geotiff_path)
    for key, path in (
        ("probability_path", probability_path),
        ("probability_geotiff_path", probability_geotiff_path),
        ("entropy_path", entropy_path),
        ("entropy_geotiff_path", entropy_geotiff_path),
    ):
        if path is not None:
            result[key] = str(path)
    result.update(inference_details)
    return result


def run_compare(
    image_path: Path,
    model_names: list[str],
    use_tta: bool,
    use_crf: bool,
    year: Optional[int] = None,
) -> dict:
    task_id = uuid.uuid4().hex[:12]
    image, meta = _load_image(image_path)
    pixel_area = meta.get("pixel_area_m2") if meta else DEFAULT_PIXEL_SIZE_M**2
    segments = []
    failures = []

    for name in model_names:
        try:
            if name == "ndsi":
                mask = _run_ndsi(image)
            elif name == "rf":
                mask = _run_rf(image)
            elif name in _KERAS_MODELS:
                mask = _run_unet(image, name, use_tta, use_crf)
            elif name in _TEMPORAL_MODELS:
                mask, _ = _run_temporal_model(image, meta, name, use_tta, year=year)
            elif name == "ensemble":
                mask = _run_ensemble(image, use_crf)
            else:
                failures.append({"model_name": name, "error": f"Unknown model: {name}"})
                continue

            if mask.dtype != np.float32:
                mask = mask.astype(np.float32)
            if mask.max() > 1.0:
                mask = mask / 255.0
        except Exception as exc:
            logger.warning("Model %s failed in run_compare: %s", name, exc)
            failures.append({"model_name": name, "error": str(exc)})
            continue

        seg_id = f"{task_id}_{name}"
        mask_path = _save_mask(mask, seg_id)
        overlay_path = _save_overlay(image, mask, seg_id)
        area_km2 = _calc_area(mask, pixel_area, allow_default=meta is None)
        segments.append(
            {
                "model_name": name,
                "mask_path": str(mask_path),
                "overlay_path": str(overlay_path),
                "area_km2": round(area_km2, 4) if area_km2 is not None else None,
            }
        )

    return {"task_id": task_id, "segments": segments, "failures": failures}


def run_uncertainty(
    image_path: Path,
    model_name: str = "unet",
    n_samples: int = 10,
    year: Optional[int] = None,
) -> dict:
    if not 2 <= n_samples <= 50:
        raise ValueError("n_samples must be between 2 and 50")
    task_id = uuid.uuid4().hex[:12]
    image, meta = _load_image(image_path)

    from src.models import mc_dropout_predict

    if model_name in _TEMPORAL_MODELS:
        spec = get_model_spec(model_name)
        image, schema, _ = build_runtime_feature_stack(
            image,
            target_channels=spec.channel_count,
            transform=meta.get("transform") if meta else None,
            crs=meta.get("crs") if meta else None,
            year=year,
            root=core_config.PROJECT_ROOT,
        )
        model = _load_temporal_model(model_name)
        threshold = spec.calibrated_threshold(core_config.PROJECT_ROOT)
    elif model_name in _KERAS_MODELS:
        model = _load_keras_model(model_name)
        schema = tuple(core_config.ALL_BAND_NAMES)
        threshold = 0.5
    else:
        raise ValueError(f"Uncertainty is not supported for model: {model_name}")
    mean, std = mc_dropout_predict(image, model, n_runs=n_samples, patch_size=core_config.PATCH_SIZE)

    eps = 1e-8
    entropy = -mean * np.log(mean + eps) - (1 - mean) * np.log(1 - mean + eps)

    mean_path = _save_mask(mean, f"{task_id}_mean")
    std_path = _save_mask(std / (std.max() + eps), f"{task_id}_std")
    entropy_path = _save_mask(entropy / (entropy.max() + eps), f"{task_id}_entropy")
    return {
        "task_id": task_id,
        "mean_path": str(mean_path),
        "std_path": str(std_path),
        "entropy_path": str(entropy_path),
        "model_name": model_name,
        "n_samples": n_samples,
        "decision_threshold": threshold,
        "feature_schema": list(schema),
        "uncertainty_semantics": "MC-dropout epistemic spread plus predictive entropy; not event probability",
    }


def _run_ndsi(image: np.ndarray, threshold: float = 0.4) -> np.ndarray:
    H, W = image.shape[:2]
    if image.ndim != 3 or image.shape[-1] < 3:
        return np.zeros((H, W), dtype=np.float32)

    try:
        green_idx = core_config.BAND_INDEX["B3"]
        swir_idx = core_config.BAND_INDEX["B11"]
        if swir_idx < image.shape[-1]:
            green = image[:, :, green_idx].astype(np.float32)
            swir = image[:, :, swir_idx].astype(np.float32)
        else:
            green = image[:, :, 1].astype(np.float32)
            swir = image[:, :, -1].astype(np.float32)
    except (KeyError, IndexError):
        green = image[:, :, 1].astype(np.float32)
        swir = image[:, :, -1].astype(np.float32)

    ndsi = (green - swir) / (green + swir + 1e-8)
    return (ndsi > threshold).astype(np.float32)


def _ensure_11_channels(image: np.ndarray) -> np.ndarray:
    if image.shape[-1] >= core_config.N_CHANNELS:
        return image[..., : core_config.N_CHANNELS]
    if image.shape[-1] == len(core_config.S2_BANDS):
        return _append_sentinel2_indices(image)
    raise ValueError(
        f"Model requires {core_config.N_CHANNELS}-channel input "
        f"(7 Sentinel-2 bands + 4 indices), but got {image.shape[-1]} channels. "
        f"Upload an 11-band GeoTIFF."
    )


def _run_rf(image: np.ndarray) -> np.ndarray:
    H, W = image.shape[:2]
    model = _load_rf_model()
    img_full = _ensure_11_channels(image)
    features = img_full.reshape(-1, img_full.shape[-1])
    pred = model.predict(features)
    return pred.reshape(H, W).astype(np.float32)


def _run_unet(image: np.ndarray, model_name: str, use_tta: bool, use_crf: bool) -> np.ndarray:
    from src.models import apply_crf, predict_full_image, tta_predict_full_image

    model = _load_keras_model(model_name)
    H, W = image.shape[:2]
    img_full = _ensure_11_channels(image)

    if use_tta:
        prob, mask = tta_predict_full_image(model, img_full, threshold=0.5)
    else:
        prob, mask = predict_full_image(img_full, model, patch_size=core_config.PATCH_SIZE)

    if use_crf:
        rgb = img_full[..., core_config.RGB_INDICES]
        prob = apply_crf(prob, rgb)
        mask = (prob > 0.5).astype(np.uint8)

    return mask.astype(np.float32)


def _run_temporal_model(
    image: np.ndarray,
    meta: Optional[dict],
    model_name: str,
    use_tta: bool,
    year: Optional[int],
) -> tuple[np.ndarray, dict[str, object]]:
    from src.models import predict_full_image, tta_predict_full_image

    spec = get_model_spec(model_name)
    feature_stack, schema, warnings = build_runtime_feature_stack(
        image,
        target_channels=spec.channel_count,
        transform=meta.get("transform") if meta else None,
        crs=meta.get("crs") if meta else None,
        year=year,
        root=core_config.PROJECT_ROOT,
    )
    if tuple(schema) != spec.feature_schema:
        raise ValueError(f"Feature schema mismatch for {model_name}")
    threshold = spec.calibrated_threshold(core_config.PROJECT_ROOT)
    model = _load_temporal_model(model_name)
    if use_tta:
        probability, mask = tta_predict_full_image(model, feature_stack, threshold=threshold)
    else:
        probability, mask = predict_full_image(
            feature_stack,
            model,
            patch_size=core_config.PATCH_SIZE,
            threshold=threshold,
        )
    entropy = -probability * np.log(probability + 1e-8) - (1 - probability) * np.log(1 - probability + 1e-8)
    uncertain_fraction = float(np.mean(entropy > 0.65))
    return mask.astype(np.float32), {
        "_probability": probability,
        "_entropy": entropy,
        "decision_threshold": threshold,
        "inference_variant": "flip_tta_4" if use_tta else "single_pass",
        "feature_schema": list(schema),
        "uncertain_pixel_fraction": uncertain_fraction,
        "warnings": warnings
        + [
            "Uncertainty is predictive entropy, not calibrated event probability.",
            "Silver RGI-derived labels do not constitute independent expert validation.",
        ],
    }


def _run_ensemble(image: np.ndarray, use_crf: bool) -> np.ndarray:
    preds = []
    for name in ["ndsi", "unet", "rf"]:
        try:
            if name == "ndsi":
                m = _run_ndsi(image)
            elif name == "rf":
                m = _run_rf(image)
            else:
                m = _run_unet(image, "unet", use_tta=True, use_crf=False)
            preds.append(m.astype(np.float32))
        except Exception:
            continue

    if not preds:
        raise RuntimeError("All ensemble models failed")

    prob = np.stack(preds).mean(axis=0)

    if use_crf and image.shape[-1] >= 3:
        from src.models import apply_crf

        prob = apply_crf(prob, image[..., :3])

    return (prob > 0.5).astype(np.float32)
