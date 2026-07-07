#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Model performance benchmarking for GlacierNET-KZ.

Inference timing, memory profiling, throughput measurement, latency
distribution, FLOPs approximation, and benchmark report generation.

Dual-backend: cv2 with scipy fallback. TensorFlow imported lazily.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy TensorFlow
# ---------------------------------------------------------------------------

_tf: Any = None


def _get_tf() -> Any:
    """Return TensorFlow module, importing on first use."""
    global _tf  # noqa: PLW0603
    if _tf is None:
        try:
            import tensorflow as _tensorflow  # noqa: WPS433

            _tf = _tensorflow
        except ImportError:
            raise ImportError("TensorFlow is required for model operations.") from None
    return _tf


# ---------------------------------------------------------------------------
# Dual-backend image I/O
# ---------------------------------------------------------------------------


def _load_image(path: str | Path) -> np.ndarray:
    """Load an image using cv2 with scipy fallback."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    try:
        import cv2  # noqa: WPS433

        img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if img is None:
            raise IOError(f"cv2 failed to read: {path}")  # noqa: TRY003
        return img
    except ImportError:
        pass
    try:
        from scipy.ndimage import imread as _scipy_imread  # noqa: WPS433, F811

        return _scipy_imread(str(path))
    except ImportError:
        pass
    raise ImportError("No image backend. Install opencv-python or scipy.")


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

BENCHMARK_CACHE: dict[str, dict[str, Any]] = {}


def _cache_key(name: str, image: np.ndarray) -> str:
    """Deterministic cache key from model name + image content hash."""
    img_hash = hashlib.sha256(image.tobytes()).hexdigest()[:16]
    return f"{name}::{img_hash}"


def clear_benchmark_cache() -> None:
    """Clear all cached benchmark results."""
    BENCHMARK_CACHE.clear()


# ---------------------------------------------------------------------------
# Inference benchmark
# ---------------------------------------------------------------------------


def benchmark_inference(
    model: Any,
    image: np.ndarray,
    n_runs: int = 100,
    warmup: int = 10,
    model_name: str = "model",
) -> dict[str, Any]:
    """Benchmark single-image inference time and memory.

    Returns timing stats (mean/std/min/max/p50/p95/p99), peak memory MB,
    and throughput (images/sec). Results are cached by model name + image hash.
    """
    if image.ndim == 3:
        image = image[np.newaxis, ...]
    image = image.astype(np.float32)

    for _ in range(warmup):
        model.predict(image, verbose=0)

    tracemalloc.start()
    times: list[float] = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        model.predict(image, verbose=0)
        times.append(time.perf_counter() - t0)
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    arr = np.array(times, dtype=np.float64)
    result: dict[str, Any] = {
        "mean_s": float(arr.mean()),
        "std_s": float(arr.std()),
        "min_s": float(arr.min()),
        "max_s": float(arr.max()),
        "p50_s": float(np.percentile(arr, 50)),
        "p95_s": float(np.percentile(arr, 95)),
        "p99_s": float(np.percentile(arr, 99)),
        "median_s": float(np.median(arr)),
        "peak_memory_mb": round(peak_mem / 1048576, 2),
        "throughput_fps": float(1.0 / arr.mean()) if arr.mean() > 0 else 0.0,
        "total_time_s": float(arr.sum()),
        "n_runs": n_runs,
    }
    BENCHMARK_CACHE[_cache_key(model_name, image)] = result
    return result


# ---------------------------------------------------------------------------
# Throughput across batch sizes
# ---------------------------------------------------------------------------


def benchmark_throughput(
    model: Any,
    images: list[np.ndarray],
    batch_sizes: Sequence[int] | None = None,
    n_runs: int = 10,
    model_name: str = "model",
) -> dict[str, dict[str, Any]]:
    """Measure throughput across batch sizes [1,2,4,8,16,32].

    Returns mapping from batch size string to timing statistics.
    """
    if batch_sizes is None:
        batch_sizes = [1, 2, 4, 8, 16, 32]

    arr = np.array([img.astype(np.float32) for img in images])
    results: dict[str, dict[str, Any]] = {}

    for bs in batch_sizes:
        if bs > len(arr):
            continue
        batch = arr[:bs]
        if batch.ndim == 3:
            batch = batch[np.newaxis, ...]

        for _ in range(min(3, n_runs)):
            model.predict(batch, verbose=0)

        times: list[float] = []
        for _ in range(n_runs):
            t0 = time.perf_counter()
            model.predict(batch, verbose=0)
            times.append(time.perf_counter() - t0)

        t_arr = np.array(times, dtype=np.float64)
        results[str(bs)] = {
            "batch_size": bs,
            "mean_s": float(t_arr.mean()),
            "std_s": float(t_arr.std()),
            "min_s": float(t_arr.min()),
            "max_s": float(t_arr.max()),
            "images_per_s": float(bs / t_arr.mean()) if t_arr.mean() > 0 else 0.0,
            "ms_per_image": float(t_arr.mean() * 1000 / bs) if bs > 0 else 0.0,
        }

    BENCHMARK_CACHE[f"throughput_{model_name}"] = results
    return results


# ---------------------------------------------------------------------------
# Latency measurement
# ---------------------------------------------------------------------------


def measure_latency(
    model: Any,
    image: np.ndarray,
    n_runs: int = 1000,
    warmup: int = 50,
    model_name: str = "model",
) -> dict[str, Any]:
    """Measure inference latency percentiles in ms (p50/p95/p99/p999)."""
    if image.ndim == 3:
        image = image[np.newaxis, ...]
    image = image.astype(np.float32)

    for _ in range(warmup):
        model.predict(image, verbose=0)

    times: list[float] = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        model.predict(image, verbose=0)
        times.append((time.perf_counter() - t0) * 1000)

    arr = np.array(times, dtype=np.float64)
    result: dict[str, Any] = {
        "p50_ms": float(np.percentile(arr, 50)),
        "p95_ms": float(np.percentile(arr, 95)),
        "p99_ms": float(np.percentile(arr, 99)),
        "p999_ms": float(np.percentile(arr, 99.9)),
        "mean_ms": float(arr.mean()),
        "std_ms": float(arr.std()),
        "min_ms": float(arr.min()),
        "max_ms": float(arr.max()),
        "n_runs": n_runs,
    }
    BENCHMARK_CACHE[f"latency_{model_name}"] = result
    return result


# ---------------------------------------------------------------------------
# Model comparison
# ---------------------------------------------------------------------------


def compare_benchmarks(
    models: list[Any],
    image: np.ndarray,
    names: list[str] | None = None,
    n_runs: int = 100,
) -> pd.DataFrame:
    """Compare inference benchmarks across multiple models side-by-side."""
    if names is None:
        names = [f"Model {i + 1}" for i in range(len(models))]

    rows: list[dict[str, Any]] = []
    for model, name in zip(models, names, strict=False):
        res = benchmark_inference(model, image, n_runs=n_runs, model_name=name)
        res["model"] = name
        rows.append(res)

    df = pd.DataFrame(rows)
    if "model" in df.columns:
        df = df[["model"] + [c for c in df.columns if c != "model"]]
    return df


# ---------------------------------------------------------------------------
# Memory profiling
# ---------------------------------------------------------------------------


def profile_memory(model: Any, image: np.ndarray) -> dict[str, Any]:
    """Profile memory: peak/current allocation, model params, activations."""
    if image.ndim == 3:
        image = image[np.newaxis, ...]
    image = image.astype(np.float32)

    tracemalloc.start()
    model.predict(image, verbose=0)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    param_bytes = param_count = 0
    try:
        for w in model.weights:
            count = int(np.prod(w.shape))
            param_count += count
            param_bytes += count * 4
    except Exception:
        pass

    activation_bytes = 0
    try:
        os_ = model.output_shape
        if os_ and len(os_) > 1:
            activation_bytes = int(np.prod(os_[1:])) * 4
    except Exception:
        pass

    return {
        "peak_bytes": peak,
        "peak_mb": round(peak / 1048576, 2),
        "current_bytes": current,
        "current_mb": round(current / 1048576, 2),
        "model_param_bytes": param_bytes,
        "model_param_mb": round(param_bytes / 1048576, 2),
        "model_param_count": param_count,
        "activation_bytes": activation_bytes,
        "activation_mb": round(activation_bytes / 1048576, 2),
    }


# ---------------------------------------------------------------------------
# FLOPs approximation
# ---------------------------------------------------------------------------


def compute_flops(model: Any, input_shape: tuple[int, ...]) -> dict[str, Any]:
    """Approximate FLOPs via layer-wise computation.

    Counts MACs for Conv2D, DepthwiseConv2D, Dense, BatchNorm.
    """
    total_flops = 0
    per_layer: list[dict[str, Any]] = []

    try:
        for layer in model.layers:
            lf = 0
            cfg = layer.get_config()
            lt = layer.__class__.__name__
            is_ = layer.input_shape
            os_ = layer.output_shape

            if lt == "Conv2D":
                ks = cfg.get("kernel_size", (3, 3))
                fo = cfg.get("filters", 0)
                fi = is_[-1] if is_ else 1
                oh = os_[1] if os_ and len(os_) > 1 else 1
                ow = os_[2] if os_ and len(os_) > 2 else 1
                lf = int(np.prod(ks) * fi * fo * oh * ow)
            elif lt == "DepthwiseConv2D":
                ks = cfg.get("kernel_size", (3, 3))
                dm = cfg.get("depth_multiplier", 1)
                ch = is_[-1] if is_ else 1
                oh = os_[1] if os_ and len(os_) > 1 else 1
                ow = os_[2] if os_ and len(os_) > 2 else 1
                lf = int(np.prod(ks) * ch * dm * oh * ow)
            elif lt == "Dense":
                lf = int(cfg.get("units", 0) * (is_[-1] if is_ else 1))
            elif lt == "BatchNormalization":
                lf = (int(np.prod(os_[1:])) if os_ else 0) * 2

            if lf > 0:
                per_layer.append({"layer": layer.name, "type": lt, "flops": lf})
                total_flops += lf
    except Exception as exc:
        logger.warning("FLOPs computation failed: %s", exc)

    return {
        "total_flops": total_flops,
        "total_mflops": round(total_flops / 1e6, 2),
        "total_gflops": round(total_flops / 1e9, 4),
        "per_layer": per_layer,
    }


# ---------------------------------------------------------------------------
# Preprocessing benchmark
# ---------------------------------------------------------------------------


def benchmark_preprocessing(
    pipeline_fn: Callable[[np.ndarray], np.ndarray],
    images: list[np.ndarray],
    n_runs: int = 100,
) -> dict[str, Any]:
    """Benchmark a preprocessing pipeline over repeated iterations."""
    if not images:
        return {"error": "empty image list"}

    times: list[float] = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        for img in images:
            pipeline_fn(img)
        times.append(time.perf_counter() - t0)

    arr = np.array(times, dtype=np.float64)
    n_images = len(images)
    return {
        "mean_s": float(arr.mean()),
        "std_s": float(arr.std()),
        "min_s": float(arr.min()),
        "max_s": float(arr.max()),
        "median_s": float(np.median(arr)),
        "p95_s": float(np.percentile(arr, 95)),
        "p99_s": float(np.percentile(arr, 99)),
        "throughput_fps": float(n_images / arr.mean()) if arr.mean() > 0 else 0.0,
        "ms_per_image": float(arr.mean() * 1000 / n_images) if n_images else 0.0,
        "n_images": n_images,
        "n_runs": n_runs,
    }


# ---------------------------------------------------------------------------
# Model size estimation
# ---------------------------------------------------------------------------


def estimate_model_size(model: Any) -> dict[str, Any]:
    """Estimate model size: param count, weight MB, activation MB."""
    param_count = weight_bytes = 0

    try:
        param_count = model.count_params()
    except Exception:
        pass

    try:
        for w in model.weights:
            count = int(np.prod(w.shape))
            param_count = max(param_count, count)
            weight_bytes += count * 4
    except Exception:
        try:
            weight_bytes = sum(int(np.prod(w.numpy().shape)) * w.numpy().nbytes for w in model.weights)
        except Exception:
            pass

    if param_count == 0:
        try:
            param_count = model.count_params()
        except Exception:
            pass

    activation_bytes = 0
    try:
        os_ = model.output_shape
        if os_ and len(os_) > 1:
            activation_bytes = int(np.prod(os_[1:])) * 4
    except Exception:
        pass

    return {
        "param_count": param_count,
        "weight_file_size_mb": round(weight_bytes / 1048576, 2),
        "activation_memory_mb": round(activation_bytes / 1048576, 2),
        "total_memory_mb": round((weight_bytes + activation_bytes) / 1048576, 2),
    }


# ---------------------------------------------------------------------------
# Throughput comparison
# ---------------------------------------------------------------------------


def compute_throughput_comparison(
    results_list: list[dict[str, Any]],
    names: list[str],
) -> pd.DataFrame:
    """Build throughput comparison table: rows=batch sizes, cols=models."""
    all_bs: set[int] = set()
    parsed: list[dict[str, dict[str, Any]]] = []

    for res in results_list:
        md: dict[str, dict[str, Any]] = {}
        for k, v in res.items():
            if isinstance(v, dict) and "batch_size" in v:
                bs = v["batch_size"]
                all_bs.add(bs)
                md[str(bs)] = v
        parsed.append(md)

    rows: list[dict[str, Any]] = []
    for bs in sorted(all_bs):
        row: dict[str, Any] = {"batch_size": bs}
        for name, data in zip(names, parsed, strict=False):
            row[name] = round(data[str(bs)]["images_per_s"], 2) if str(bs) in data else np.nan
        rows.append(row)

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------


def generate_benchmark_report(results: dict[str, Any]) -> str:
    """Generate a Markdown benchmark report from collected results."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines: list[str] = ["# GlacierNET-KZ Benchmark Report", "", f"**Generated**: {ts}", ""]

    def _table(rows: list[tuple[str, str]]) -> list[str]:
        out = ["| Metric | Value |", "|--------|-------|"]
        out += [f"| {k} | {v} |" for k, v in rows]
        return out + [""]

    if "mean_s" in results:
        lines += ["## Inference Timing", ""] + _table(
            [
                ("Mean", f"{results['mean_s']:.4f} s"),
                ("Std", f"{results.get('std_s', 0):.4f} s"),
                ("Min", f"{results.get('min_s', 0):.4f} s"),
                ("Max", f"{results.get('max_s', 0):.4f} s"),
                ("p50", f"{results.get('p50_s', 0):.4f} s"),
                ("p95", f"{results.get('p95_s', 0):.4f} s"),
                ("p99", f"{results.get('p99_s', 0):.4f} s"),
                ("Throughput", f"{results.get('throughput_fps', 0):.1f} FPS"),
                ("Runs", str(results.get("n_runs", 0))),
            ]
        )

    if "p50_ms" in results:
        lines += ["## Latency Distribution", ""] + _table(
            [
                ("p50", f"{results['p50_ms']:.2f} ms"),
                ("p95", f"{results['p95_ms']:.2f} ms"),
                ("p99", f"{results['p99_ms']:.2f} ms"),
                ("p999", f"{results.get('p999_ms', 0):.2f} ms"),
                ("Mean", f"{results.get('mean_ms', 0):.2f} ms"),
            ]
        )

    if "peak_mb" in results:
        lines += ["## Memory Usage", ""] + _table(
            [
                ("Peak", f"{results['peak_mb']:.2f} MB"),
                ("Current", f"{results.get('current_mb', 0):.2f} MB"),
                ("Model Params", f"{results.get('model_param_mb', 0):.2f} MB"),
                ("Activations", f"{results.get('activation_mb', 0):.2f} MB"),
            ]
        )

    if "param_count" in results and "weight_file_size_mb" in results:
        lines += ["## Model Size", ""] + _table(
            [
                ("Parameters", f"{results['param_count']:,}"),
                ("Weight Size", f"{results['weight_file_size_mb']:.2f} MB"),
                ("Activation Memory", f"{results.get('activation_memory_mb', 0):.2f} MB"),
                ("Total Memory", f"{results.get('total_memory_mb', 0):.2f} MB"),
            ]
        )

    if "total_flops" in results:
        lines += ["## Computational Cost", ""] + _table(
            [
                ("Total FLOPs", f"{results['total_flops']:,}"),
                ("MFLOPs", f"{results.get('total_mflops', 0):.2f}"),
                ("GFLOPs", f"{results.get('total_gflops', 0):.4f}"),
            ]
        )

    if "throughput_fps" in results and "n_images" in results:
        lines += ["## Preprocessing Timing", ""] + _table(
            [
                ("Mean", f"{results.get('mean_s', 0):.4f} s"),
                ("Throughput", f"{results.get('throughput_fps', 0):.1f} images/s"),
                ("ms/image", f"{results.get('ms_per_image', 0):.2f} ms"),
            ]
        )

    batch_keys = [k for k in results if k.isdigit()]
    if batch_keys:
        lines += [
            "## Throughput by Batch Size",
            "",
            "| Batch | Mean (s) | Images/s | ms/image |",
            "|-------|----------|----------|----------|",
        ]
        for k in sorted(batch_keys, key=int):
            v = results[k]
            if isinstance(v, dict) and "mean_s" in v:
                lines.append(
                    f"| {v['batch_size']} | {v['mean_s']:.4f} | {v['images_per_s']:.1f} | {v['ms_per_image']:.2f} |"
                )
        lines.append("")

    if len(lines) <= 3:
        lines.append("*No benchmark data available.*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON export / import
# ---------------------------------------------------------------------------


def save_benchmark_results(results: dict[str, Any], path: str | Path) -> None:
    """Save benchmark results to a JSON file. Creates parent dirs."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(json.loads(json.dumps(results, default=str)), fh, indent=2, ensure_ascii=False)
    logger.info("Benchmark results saved to %s", path)


def load_benchmark_results(path: str | Path) -> dict[str, Any]:
    """Load benchmark results from a JSON file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    logger.info("Benchmark results loaded from %s", path)
    return data
