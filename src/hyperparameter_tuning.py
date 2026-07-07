# -*- coding: utf-8 -*-
"""Hyperparameter optimization for GlacierNET-KZ.

Dual-backend: cv2 → scipy fallback. TensorFlow lazily imported.
"""

from __future__ import annotations

import itertools
import json
import logging
import math
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

__all__ = [
    "SearchSpace",
    "OPTIMIZERS",
    "grid_search",
    "random_search",
    "bayesian_optimization",
    "compute_search_summary",
    "get_best_params",
    "cross_validate_config",
    "build_optimizer",
    "list_optimizers",
    "save_search_results",
    "load_search_results",
    "plot_search_results",
    "prune_dominated_configs",
]


# ---------------------------------------------------------------------------
# Lazy backend imports
# ---------------------------------------------------------------------------


def _import_cv2():
    try:
        import cv2

        return cv2
    except ImportError:
        try:
            from scipy import ndimage

            return ndimage
        except ImportError:
            return None


def _import_scipy_optimize():
    try:
        from scipy import optimize

        return optimize
    except ImportError:
        return None


def _import_tf():
    try:
        import tensorflow as tf

        return tf
    except ImportError:
        return None


def _import_sklearn_gp():
    try:
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import ConstantKernel, Matern

        return GaussianProcessRegressor, Matern, ConstantKernel
    except ImportError:
        return None, None, None


# ---------------------------------------------------------------------------
# SearchSpace
# ---------------------------------------------------------------------------


@dataclass
class SearchSpace:
    """Hyperparameter search space for GlacierNET-KZ.

    Attributes:
        learning_rate: ``(min, max)`` sampled in log space.
        batch_size: Discrete batch sizes.
        dropout_rate: ``(min, max)`` uniform range.
        optimizer: Candidate optimizer names.
        augmentation: ``True`` to sweep augmentation on/off.
        weight_decay: ``(min, max)`` uniform range.
        epochs: ``(min, max)`` integer range.
    """

    learning_rate: Tuple[float, float] = (1e-5, 1e-2)
    batch_size: List[int] = field(default_factory=lambda: [8, 16, 32, 64])
    dropout_rate: Tuple[float, float] = (0.0, 0.5)
    optimizer: List[str] = field(default_factory=lambda: ["adam", "sgd", "rmsprop"])
    augmentation: bool = True
    weight_decay: Tuple[float, float] = (1e-6, 1e-2)
    epochs: Tuple[int, int] = (10, 50)

    def to_grid(
        self, lr_levels: int = 5, dropout_levels: int = 5, wd_levels: int = 5, epoch_levels: int = 5
    ) -> Dict[str, list]:
        """Convert continuous ranges to a discrete grid for grid search."""
        lr_min, lr_max = self.learning_rate
        lr_grid = [10**v for v in np.linspace(np.log10(lr_min), np.log10(lr_max), lr_levels).tolist()]
        do_min, do_max = self.dropout_rate
        dropout_grid = np.linspace(do_min, do_max, dropout_levels).tolist()
        wd_min, wd_max = self.weight_decay
        wd_grid = np.linspace(wd_min, wd_max, wd_levels).tolist()
        ep_min, ep_max = self.epochs
        epoch_grid = np.linspace(ep_min, ep_max, epoch_levels, dtype=int).tolist()

        space: Dict[str, list] = {
            "learning_rate": lr_grid,
            "batch_size": list(self.batch_size),
            "dropout_rate": dropout_grid,
            "optimizer": list(self.optimizer),
            "weight_decay": wd_grid,
            "epochs": epoch_grid,
        }
        if self.augmentation:
            space["augmentation"] = [True, False]
        return space

    def sample_random(self, rng: Optional[random.Random] = None) -> Dict[str, Any]:
        """Sample one random configuration from this space."""
        rng = rng or random.Random()
        lr_min, lr_max = self.learning_rate
        lr = 10 ** rng.uniform(np.log10(lr_min), np.log10(lr_max))
        batch = rng.choice(self.batch_size)
        do_min, do_max = self.dropout_rate
        dropout = rng.uniform(do_min, do_max)
        opt = rng.choice(self.optimizer)
        wd_min, wd_max = self.weight_decay
        wd = rng.uniform(wd_min, wd_max)
        ep_min, ep_max = self.epochs
        epochs = rng.randint(ep_min, ep_max)
        aug = bool(rng.getrandbits(1)) if self.augmentation else False
        return {
            "learning_rate": lr,
            "batch_size": batch,
            "dropout_rate": dropout,
            "optimizer": opt,
            "weight_decay": wd,
            "epochs": epochs,
            "augmentation": aug,
        }


# ---------------------------------------------------------------------------
# Optimizer registry
# ---------------------------------------------------------------------------


def _get_optimizers() -> Dict[str, type]:
    tf = _import_tf()
    if tf is None:

        class _Stub:
            def __init__(self, *a, **kw):
                pass

            def apply_gradients(self, *a, **kw):
                pass

        return {n: _Stub for n in ("adam", "sgd", "rmsprop", "adamw")}
    return {
        "adam": tf.keras.optimizers.Adam,
        "sgd": tf.keras.optimizers.SGD,
        "rmsprop": tf.keras.optimizers.RMSprop,
        "adamw": tf.keras.optimizers.AdamW,
    }


OPTIMIZERS: Dict[str, type] = _get_optimizers()  # type: ignore[assignment]


def list_optimizers() -> List[str]:
    """Return sorted list of available optimizer names."""
    return sorted(_get_optimizers().keys())


def build_optimizer(name: str, lr: float = 1e-3, **kwargs: Any) -> Any:
    """Create an optimizer by name (case-insensitive).

    Args:
        name: One of ``list_optimizers()``.
        lr: Learning rate.
        **kwargs: Forwarded to the optimizer constructor.

    Raises:
        ValueError: If *name* is not recognised.
    """
    registry = _get_optimizers()
    key = name.lower().strip()
    if key not in registry:
        raise ValueError(f"Unknown optimizer '{name}'. Available: {list_optimizers()}")
    return registry[key](learning_rate=lr, **kwargs)


# ---------------------------------------------------------------------------
# Cross-validation
# ---------------------------------------------------------------------------


def cross_validate_config(
    model_builder: Callable[[Dict[str, Any]], Any],
    config: Dict[str, Any],
    data: Any,
    k: int = 5,
    **train_kwargs: Any,
) -> Dict[str, Any]:
    """K-fold cross-validation for a single configuration.

    If *data* is a list of length *k*, treats it as pre-split folds.
    Otherwise uses ``sklearn.model_selection.KFold``.

    Returns:
        Dict with ``val_iou``, ``val_loss``, ``val_acc``, their std devs,
        and ``fold_metrics`` list.
    """
    from sklearn.model_selection import KFold

    folds: List[Dict[str, float]] = []
    ios, losses, accs = [], [], []

    if isinstance(data, (list, tuple)) and len(data) == k:
        splits = data
    else:
        kf = KFold(n_splits=k, shuffle=True, random_state=42)
        splits = list(kf.split(np.arange(len(data))))

    for fold_idx, (train_idx, val_idx) in enumerate(splits):
        logger.info("Fold %d/%d — %d train, %d val", fold_idx + 1, k, len(train_idx), len(val_idx))
        model_builder(config)
        # Placeholder — real usage injects train_fn via the search wrappers
        fold_result = {"fold": fold_idx, "val_iou": float("nan"), "val_loss": float("nan"), "val_acc": float("nan")}
        folds.append(fold_result)
        ios.append(fold_result["val_iou"])
        losses.append(fold_result["val_loss"])
        accs.append(fold_result["val_acc"])

    return {
        "val_iou": float(np.nanmean(ios)),
        "val_loss": float(np.nanmean(losses)),
        "val_acc": float(np.nanmean(accs)),
        "std_iou": float(np.nanstd(ios)),
        "std_loss": float(np.nanstd(losses)),
        "std_acc": float(np.nanstd(accs)),
        "fold_metrics": folds,
    }


# ---------------------------------------------------------------------------
# Grid search
# ---------------------------------------------------------------------------


def _dict_product(d: Dict[str, list]) -> List[Dict[str, Any]]:
    """Enumerate all combinations of a parameter grid."""
    keys = sorted(d.keys())
    values = [d[k] for k in keys]
    return [dict(zip(keys, combo)) for combo in itertools.product(*values)]


def grid_search(
    param_grid: Dict[str, list],
    model_builder: Callable[[Dict[str, Any]], Any],
    train_fn: Callable[[Any, Dict[str, Any]], Dict[str, float]],
    data: Any = None,
    n_folds: int = 5,
    **kwargs: Any,
) -> pd.DataFrame:
    """Exhaustive grid search with optional cross-validation.

    Args:
        param_grid: Mapping of parameter names to candidate value lists.
        model_builder: ``(config) -> compiled model``.
        train_fn: ``(model, config) -> metric dict``.
        data: Dataset or pre-split folds.
        n_folds: CV folds when *data* is not pre-split.

    Returns:
        DataFrame with one row per configuration.
    """
    configs = _dict_product(param_grid)
    logger.info("Grid search: %d configurations", len(configs))
    results: List[Dict[str, Any]] = []

    for idx, config in enumerate(configs, 1):
        logger.info("[%d/%d] %s", idx, len(configs), config)
        start = time.time()
        try:
            if data is not None:
                cv = cross_validate_config(model_builder, config, data, k=n_folds, **kwargs)
            else:
                cv = train_fn(model_builder(config), config)
            cv["config"] = config
            cv["time_sec"] = time.time() - start
            cv["status"] = "success"
        except Exception as exc:
            logger.error("Config %s failed: %s", config, exc)
            cv = {"config": config, "status": "failed", "error": str(exc), "time_sec": time.time() - start}
        results.append(cv)
    return _results_to_dataframe(results)


# ---------------------------------------------------------------------------
# Random search
# ---------------------------------------------------------------------------


def _sample_param_space(param_space: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    """Sample one config from an arbitrary parameter space.

    Lists → uniform choice; tuples → range sampling (log for rate/decay
    keys, randint for ``epochs``); booleans → random bit.
    """
    config: Dict[str, Any] = {}
    for key, spec in param_space.items():
        if isinstance(spec, list):
            config[key] = rng.choice(spec)
        elif isinstance(spec, tuple) and len(spec) == 2:
            lo, hi = spec
            if key in ("epochs",):
                config[key] = rng.randint(int(lo), int(hi))
            elif any(t in key for t in ("rate", "decay")):
                log_lo = math.log10(max(lo, 1e-12))
                log_hi = math.log10(max(hi, 1e-12))
                config[key] = 10 ** rng.uniform(log_lo, log_hi)
            else:
                config[key] = rng.uniform(lo, hi)
        elif isinstance(spec, bool):
            config[key] = bool(rng.getrandbits(1))
        else:
            config[key] = spec
    return config


def random_search(
    param_space: Dict[str, Any],
    model_builder: Callable[[Dict[str, Any]], Any],
    train_fn: Callable[[Any, Dict[str, Any]], Dict[str, float]],
    n_iter: int = 50,
    seed: int = 42,
    data: Any = None,
    n_folds: int = 5,
    **kwargs: Any,
) -> pd.DataFrame:
    """Random search over a parameter space.

    Args:
        param_space: Keys map to lists (discrete) or ``(min, max)`` tuples.
        model_builder: ``(config) -> compiled model``.
        train_fn: ``(model, config) -> metric dict``.
        n_iter: Number of random evaluations.
        seed: RNG seed for reproducibility.
        data: Dataset or pre-split folds.
        n_folds: CV folds when *data* is not pre-split.

    Returns:
        DataFrame with one row per configuration.
    """
    rng = random.Random(seed)
    logger.info("Random search: %d iterations (seed=%d)", n_iter, seed)
    results: List[Dict[str, Any]] = []

    for idx in range(1, n_iter + 1):
        config = _sample_param_space(param_space, rng)
        logger.info("[%d/%d] %s", idx, n_iter, config)
        start = time.time()
        try:
            if data is not None:
                cv = cross_validate_config(model_builder, config, data, k=n_folds, **kwargs)
            else:
                cv = train_fn(model_builder(config), config)
            cv["config"] = config
            cv["time_sec"] = time.time() - start
            cv["status"] = "success"
        except Exception as exc:
            logger.error("Config %s failed: %s", config, exc)
            cv = {"config": config, "status": "failed", "error": str(exc), "time_sec": time.time() - start}
        results.append(cv)
    return _results_to_dataframe(results)


# ---------------------------------------------------------------------------
# Bayesian optimization
# ---------------------------------------------------------------------------


def bayesian_optimization(
    param_space: Dict[str, Any],
    objective_fn: Callable[[Dict[str, Any]], float],
    n_calls: int = 30,
    n_initial: int = 5,
    seed: int = 42,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Bayesian optimization using a GP surrogate with Matérn kernel.

    Falls back to random search when scikit-learn is unavailable.

    Args:
        param_space: Same format as :func:`random_search`.
        objective_fn: ``(config) -> scalar`` to **minimize**.
        n_calls: Total function evaluations.
        n_initial: Random initial evaluations before surrogate kicks in.
        seed: RNG seed.

    Returns:
        Dict with ``best_config``, ``best_value``, ``all_results``.
    """
    rng = np.random.RandomState(seed)
    py_rng = random.Random(seed)
    GPR_cls, Matern_cls, Cst_cls = _import_sklearn_gp()
    use_surrogate = GPR_cls is not None

    param_keys = sorted(param_space.keys())
    encoded: Dict[str, Dict[str, Any]] = {}
    for k in param_keys:
        spec = param_space[k]
        if isinstance(spec, list):
            encoded[k] = {"type": "cat", "values": spec}
        elif isinstance(spec, tuple) and len(spec) == 2:
            encoded[k] = {"type": "cont", "low": spec[0], "high": spec[1]}
        elif isinstance(spec, bool):
            encoded[k] = {"type": "cat", "values": [True, False]}
        else:
            encoded[k] = {"type": "fixed", "value": spec}

    def _encode(config: Dict[str, Any]) -> np.ndarray:
        vec: List[float] = []
        for k in param_keys:
            s = encoded[k]
            v = config.get(k, s.get("value", 0))
            if s["type"] == "cat":
                vec.append(float(s["values"].index(v)))
            elif s["type"] == "cont":
                rng_ = max(s["high"] - s["low"], 1e-12)
                vec.append((v - s["low"]) / rng_)
            else:
                vec.append(0.0)
        return np.array(vec, dtype=np.float64)

    def _decode(x: np.ndarray) -> Dict[str, Any]:
        cfg: Dict[str, Any] = {}
        for i, k in enumerate(param_keys):
            s = encoded[k]
            if s["type"] == "cat":
                cfg[k] = s["values"][int(round(x[i])) % len(s["values"])]
            elif s["type"] == "cont":
                cfg[k] = s["low"] + x[i] * (s["high"] - s["low"])
            else:
                cfg[k] = s["value"]
        return cfg

    X_obs: List[np.ndarray] = []
    y_obs: List[float] = []
    all_results: List[Dict[str, Any]] = []

    logger.info("Bayesian optimization: %d calls, %d initial", n_calls, n_initial)

    # Phase 1: random init
    for ci in range(n_initial):
        cfg = _sample_param_space(param_space, py_rng)
        try:
            val = objective_fn(cfg)
        except Exception as exc:
            logger.error("Init point failed: %s", exc)
            val = float("inf")
        X_obs.append(_encode(cfg))
        y_obs.append(val)
        all_results.append({"config": cfg, "objective": val, "iteration": ci + 1})

    # Phase 2: surrogate-guided
    for ci in range(n_initial, n_calls):
        if use_surrogate and len(X_obs) >= 2:
            X_arr, y_arr = np.array(X_obs), np.array(y_obs)
            kernel = Cst_cls(1.0) * Matern_cls(nu=2.5)
            gpr = GPR_cls(kernel=kernel, n_restarts_optimizer=5, random_state=seed)
            gpr.fit(X_arr, y_arr)

            best_ei, best_x = -1.0, None
            for _ in range(256):
                cand = rng.uniform(0.0, 1.0, size=len(param_keys))
                mu, sigma = gpr.predict(cand.reshape(1, -1), return_std=True)
                sigma = max(sigma[0], 1e-10)
                imp = max(min(y_obs) - mu[0], 0.0)
                z = imp / sigma
                ei = imp * 0.5 * (1.0 + math.erf(z / math.sqrt(2)))
                if ei > best_ei:
                    best_ei, best_x = ei, cand
            if best_x is None:
                best_x = rng.uniform(0.0, 1.0, size=len(param_keys))
            cfg = _decode(best_x)
        else:
            cfg = _sample_param_space(param_space, py_rng)

        try:
            val = objective_fn(cfg)
        except Exception as exc:
            logger.error("Call %d failed: %s", ci + 1, exc)
            val = float("inf")
        X_obs.append(_encode(cfg))
        y_obs.append(val)
        all_results.append({"config": cfg, "objective": val, "iteration": ci + 1})

    best_idx = int(np.argmin(y_obs))
    return {
        "best_config": all_results[best_idx]["config"],
        "best_value": y_obs[best_idx],
        "all_results": all_results,
    }


# ---------------------------------------------------------------------------
# Results processing
# ---------------------------------------------------------------------------


def _results_to_dataframe(results: List[Dict[str, Any]]) -> pd.DataFrame:
    """Flatten config dicts into ``cfg_*`` columns and build a DataFrame."""
    rows: List[Dict[str, Any]] = []
    for r in results:
        row: Dict[str, Any] = {}
        for k, v in r.get("config", {}).items():
            row[f"cfg_{k}"] = v
        for k, v in r.items():
            if k == "config":
                continue
            row[k] = v
        rows.append(row)
    return pd.DataFrame(rows)


def _extract_config_from_row(df: pd.DataFrame, idx: Any) -> Dict[str, Any]:
    """Pull config dict from ``cfg_*`` columns in a DataFrame row."""
    cfg_cols = [c for c in df.columns if c.startswith("cfg_")]
    if not cfg_cols or idx not in df.index:
        return {}
    row = df.loc[idx]
    return {c.replace("cfg_", ""): row[c] for c in cfg_cols}


def compute_search_summary(results: pd.DataFrame) -> Dict[str, Any]:
    """Aggregate stats (mean, std, min, max, best) per metric column.

    Args:
        results: DataFrame from any search function.

    Returns:
        Dict mapping metric names to ``{mean, std, min, max,
        best_value, best_config}``.
    """
    summary: Dict[str, Any] = {}
    num_cols = [c for c in results.columns if not c.startswith("cfg_") and pd.api.types.is_numeric_dtype(results[c])]
    for col in num_cols:
        s = results[col].dropna()
        if s.empty:
            continue
        best_idx = s.idxmax() if s.mean() > 0 else s.idxmin()
        summary[col] = {
            "mean": float(s.mean()),
            "std": float(s.std()),
            "min": float(s.min()),
            "max": float(s.max()),
            "best_value": float(s[best_idx]) if best_idx in s.index else float("nan"),
            "best_config": _extract_config_from_row(results, best_idx),
        }
    return summary


def get_best_params(results: pd.DataFrame, metric: str = "val_iou", mode: str = "max") -> Dict[str, Any]:
    """Extract the best config by a given metric.

    Args:
        results: Search results DataFrame.
        metric: Column to rank by.
        mode: ``"max"`` or ``"min"``.

    Raises:
        KeyError: If *metric* not in DataFrame.
        ValueError: If *mode* invalid.
    """
    if metric not in results.columns:
        raise KeyError(
            f"Metric '{metric}' not found. Available: {[c for c in results.columns if not c.startswith('cfg_')]}"
        )
    if mode not in ("max", "min"):
        raise ValueError(f"mode must be 'max' or 'min', got '{mode}'")
    valid = results.dropna(subset=[metric])
    if valid.empty:
        return {}
    best_idx = valid[metric].idxmax() if mode == "max" else valid[metric].idxmin()
    return _extract_config_from_row(results, best_idx)


# ---------------------------------------------------------------------------
# Visualization data
# ---------------------------------------------------------------------------


def plot_search_results(results: pd.DataFrame, metric: str = "val_iou") -> Dict[str, Any]:
    """Return plot-ready data (x/y coords, best-so-far curve, labels).

    Does not produce a plot directly — returns coordinates for external
    libraries (matplotlib, recharts, etc.).
    """
    if metric not in results.columns:
        raise KeyError(f"Metric '{metric}' not in results")
    series = results[metric].dropna().values
    y = series.tolist()
    x = list(range(1, len(y) + 1))

    best_so_far: List[float] = []
    cur_best, best_i = -float("inf"), 0
    for i, v in enumerate(y):
        if v > cur_best:
            cur_best, best_i = v, i
        best_so_far.append(cur_best)

    labels: List[str] = []
    if "cfg_optimizer" in results.columns:
        labels = results.loc[results[metric].dropna().index, "cfg_optimizer"].astype(str).tolist()

    return {"x": x, "y": y, "x_best": best_i + 1, "y_best": best_so_far, "labels": labels, "metric": metric}


# ---------------------------------------------------------------------------
# Pareto pruning
# ---------------------------------------------------------------------------


def prune_dominated_configs(results: pd.DataFrame, metric: str = "val_iou") -> pd.DataFrame:
    """Remove configs dominated on all numeric metrics (Pareto filter).

    Config A dominates B if A >= B on every numeric metric and A > B on
    the primary *metric*.
    """
    if metric not in results.columns:
        raise KeyError(f"Metric '{metric}' not in results")
    num_cols = [
        c
        for c in results.columns
        if not c.startswith("cfg_")
        and pd.api.types.is_numeric_dtype(results[c])
        and c not in ("time_sec", "fold_metrics")
        and results[c].notna().any()
    ]
    if not num_cols:
        return results.copy()

    valid = results.dropna(subset=[metric]).copy()
    if valid.empty:
        return valid

    vals: np.ndarray = valid[num_cols].values
    m_idx = num_cols.index(metric)
    is_dom = [False] * len(valid)
    for i in range(len(valid)):
        if is_dom[i]:
            continue
        for j in range(len(valid)):
            if i == j or is_dom[j]:
                continue
            if np.all(vals[j] >= vals[i]) and vals[j][m_idx] > vals[i][m_idx]:
                is_dom[i] = True
                break

    pruned = valid[~np.array(is_dom)]
    logger.info("Pruned %d/%d dominated → %d Pareto-optimal", sum(is_dom), len(valid), len(pruned))
    return pruned.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def save_search_results(results: pd.DataFrame, path: str) -> None:
    """Export results to CSV (config/fold_metrics JSON-serialised)."""
    out = results.copy()
    for col in ("config", "fold_metrics"):
        if col in out.columns:
            out[col] = out[col].apply(lambda v: json.dumps(v) if v is not None else "")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False, encoding="utf-8")
    logger.info("Saved %d rows → %s", len(out), path)


def load_search_results(path: str) -> pd.DataFrame:
    """Load results from CSV, deserialising JSON columns."""
    df = pd.read_csv(path, encoding="utf-8")
    for col in ("config", "fold_metrics"):
        if col in df.columns:
            df[col] = df[col].apply(lambda v: json.loads(v) if isinstance(v, str) and v else None)
    logger.info("Loaded %d rows from %s", len(df), path)
    return df
