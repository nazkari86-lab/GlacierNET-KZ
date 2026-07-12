# -*- coding: utf-8 -*-
"""
Experiment logging and tracking for GlacierNET-KZ.

Provides dual-backend image I/O (cv2 primary, scipy fallback),
lazy TensorFlow imports, and structured experiment lifecycle management.

Usage::

    from experiment_tracking import ExperimentTracker

    tracker = ExperimentTracker("runs/exp01")
    exp_id = tracker.log_experiment(
        name="glacier-segmentation",
        params={"lr": 1e-4, "batch_size": 16},
        metrics={"dice": 0.91, "iou": 0.84},
        tags={"dataset": "s2-glacier"},
    )
"""

from __future__ import annotations

import copy
import json
import logging
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Dual-backend image I/O: try cv2 first, fall back to scipy
# ---------------------------------------------------------------------------
try:
    import cv2  # type: ignore[import-untyped]

    _cv2_available = True
except ImportError:
    _cv2_available = False

try:
    from scipy.ndimage import imread as _scipy_imread  # type: ignore[attr-defined]

    _scipy_available = True
except ImportError:
    _scipy_available = False

# ---------------------------------------------------------------------------
# Lazy TensorFlow import
# ---------------------------------------------------------------------------
_tf_available: Optional[bool] = None


def _ensure_tf():
    """Import TensorFlow on first use and cache the module."""
    global _tf_available  # noqa: PLW0603
    if _tf_available is True:
        import tensorflow as tf  # noqa: F811

        return tf
    if _tf_available is False:
        raise RuntimeError("TensorFlow is not installed")
    try:
        import tensorflow as tf  # noqa: F811

        _tf_available = True
        return tf
    except ImportError:
        _tf_available = False
        raise RuntimeError("TensorFlow is not installed") from None


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
__all__ = [
    "Experiment",
    "ExperimentTracker",
    "EXPERIMENT_DIR",
    "generate_experiment_id",
    "format_duration",
    "load_image",
    "save_image",
]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EXPERIMENT_DIR: Path = Path("experiments")

_VALID_STATUSES = ("running", "completed", "failed")

_IMAGE_READ_FLAG = 1 if _cv2_available else 0  # cv2.IMREAD_COLOR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def generate_experiment_id() -> str:
    """Return a UUID-4 hex string suitable as an experiment identifier."""
    return uuid.uuid4().hex


def format_duration(start: datetime, end: datetime) -> str:
    """Return a human-readable string for the elapsed time between two datetimes.

    Parameters
    ----------
    start : datetime
        Timestamp when the experiment began.
    end : datetime
        Timestamp when the experiment finished.

    Returns
    -------
    str
        A compact representation, e.g. ``'2h 13m 7s'`` or ``'342ms'``.
    """
    delta = end - start
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        return "0s"
    if total_seconds < 1:
        ms = int(delta.microseconds / 1_000)
        return f"{ms}ms"
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def _now_utc() -> datetime:
    """Current UTC time with timezone info."""
    return datetime.now(timezone.utc)


def _ensure_dir(path: Path) -> Path:
    """Create *path* (and parents) if it does not exist and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Image I/O helpers (dual-backend)
# ---------------------------------------------------------------------------
def load_image(path: str | Path, *, as_rgb: bool = True) -> np.ndarray:
    """Read an image from *path* using cv2 (preferred) or scipy.

    Parameters
    ----------
    path : str or Path
        File-system path to the image.
    as_rgb : bool, optional
        If ``True`` (default) convert BGR → RGB when using OpenCV.

    Returns
    -------
    np.ndarray
        Image array with shape ``(H, W, 3)`` (uint8).
    """
    path = str(path)
    if _cv2_available:
        flag = cv2.IMREAD_COLOR if as_rgb else cv2.IMREAD_UNCHANGED
        img = cv2.imread(path, flag)  # type: ignore[union-attr]
        if img is None:
            raise FileNotFoundError(f"cv2 could not read {path}")
        if as_rgb and img.ndim == 3 and img.shape[2] == 3:
            img = img[..., ::-1].copy()
        return img
    if _scipy_available:
        img = _scipy_imread(path, mode="RGB" if as_rgb else "L")
        return np.asarray(img)
    raise RuntimeError("No image backend available – install opencv-python or scipy")


def save_image(path: str | Path, image: np.ndarray) -> None:
    """Write *image* to disk via cv2 or PIL/scipy fallback.

    Parameters
    ----------
    path : str or Path
        Destination path.
    image : np.ndarray
        Array to write (uint8 expected).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if _cv2_available:
        img_bgr = image[..., ::-1].copy() if image.ndim == 3 and image.shape[2] == 3 else image
        cv2.imwrite(str(path), img_bgr)  # type: ignore[union-attr]
        return
    # PIL fallback via scipy-compatible import
    try:
        from PIL import Image as _PILImage

        _PILImage.fromarray(image).save(str(path))
    except ImportError:
        # Last resort – raw binary dump (will not be a valid image).
        path.write_bytes(image.tobytes())
        logger.warning("PIL unavailable – wrote raw bytes to %s", path)


# ---------------------------------------------------------------------------
# Experiment dataclass
# ---------------------------------------------------------------------------
@dataclass
class Experiment:
    """Immutable-ish container for a single experiment run.

    Attributes
    ----------
    id : str
        Unique identifier (UUID-4 hex).
    name : str
        Human-readable experiment name.
    model : str
        Model identifier / architecture name.
    params : dict
        Hyper-parameters and configuration.
    metrics : dict
        Evaluation metrics produced by the run.
    start_time : datetime
        When the run started.
    end_time : datetime | None
        When the run finished (``None`` while still running).
    artifacts : list[str]
        Paths to saved artefacts (checkpoints, figures, …).
    tags : dict[str, str]
        Free-form key/value metadata.
    status : str
        One of ``'running'``, ``'completed'``, ``'failed'``.
    """

    id: str = field(default_factory=generate_experiment_id)
    name: str = ""
    model: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=_now_utc)
    end_time: Optional[datetime] = None
    artifacts: List[str] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)
    status: str = "running"

    # -- helpers -----------------------------------------------------------

    @property
    def duration_str(self) -> Optional[str]:
        """Human-readable duration if *end_time* is set, else ``None``."""
        if self.end_time is None:
            return None
        return format_duration(self.start_time, self.end_time)

    @property
    def elapsed_seconds(self) -> Optional[float]:
        """Elapsed wall-clock seconds, or ``None`` if still running."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary (JSON-safe)."""
        d = asdict(self)
        # Convert datetimes to ISO-8601 strings
        for key in ("start_time", "end_time"):
            val = d[key]
            if isinstance(val, datetime):
                d[key] = val.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Experiment":
        """Deserialise a dict back into an :class:`Experiment`."""
        d = copy.deepcopy(data)
        for key in ("start_time", "end_time"):
            val = d.get(key)
            if isinstance(val, str):
                d[key] = datetime.fromisoformat(val)
        return cls(**d)


# ---------------------------------------------------------------------------
# ExperimentTracker
# ---------------------------------------------------------------------------
class ExperimentTracker:
    """Persistent experiment tracker backed by JSON files on disk.

    Parameters
    ----------
    experiment_dir : str, optional
        Root directory where experiment data is stored.
        Defaults to the module-level :data:`EXPERIMENT_DIR`.
    """

    _INDEX_FILE = "_index.json"

    def __init__(self, experiment_dir: str = "experiments") -> None:
        self._root = Path(experiment_dir)
        _ensure_dir(self._root)
        self._index_path = self._root / self._INDEX_FILE
        self._ensure_index()
        logger.info("ExperimentTracker initialised in %s", self._root)

    # -- private helpers ---------------------------------------------------

    def _ensure_index(self) -> None:
        """Create the index file if it does not exist yet."""
        if not self._index_path.exists():
            self._index_path.write_text(json.dumps({}, indent=2), encoding="utf-8")

    def _load_index(self) -> Dict[str, Any]:
        """Return the experiment index mapping id → metadata."""
        try:
            return json.loads(self._index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_index(self, index: Dict[str, Any]) -> None:
        """Persist the experiment index."""
        self._index_path.write_text(json.dumps(index, indent=2, default=str), encoding="utf-8")

    def _experiment_dir(self, experiment_id: str) -> Path:
        """Return (and create) the directory for a single experiment."""
        d = self._root / experiment_id
        _ensure_dir(d)
        return d

    def _experiment_path(self, experiment_id: str) -> Path:
        """Return the JSON path for a single experiment."""
        return self._experiment_dir(experiment_id) / "experiment.json"

    def _read_experiment(self, experiment_id: str) -> Experiment:
        """Deserialise an :class:`Experiment` from disk."""
        path = self._experiment_path(experiment_id)
        if not path.exists():
            raise FileNotFoundError(f"Experiment {experiment_id!r} not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        return Experiment.from_dict(data)

    def _write_experiment(self, exp: Experiment) -> None:
        """Serialise an :class:`Experiment` to disk."""
        path = self._experiment_path(exp.id)
        path.write_text(json.dumps(exp.to_dict(), indent=2, default=str), encoding="utf-8")

    def _update_index(self, exp: Experiment) -> None:
        """Update the index entry for *exp*."""
        index = self._load_index()
        index[exp.id] = {
            "name": exp.name,
            "model": exp.model,
            "status": exp.status,
            "tags": exp.tags,
            "start_time": exp.start_time.isoformat(),
        }
        self._save_index(index)

    # -- public API --------------------------------------------------------

    def log_experiment(
        self,
        name: str,
        params: Dict[str, Any],
        metrics: Dict[str, Any],
        *,
        model: str = "",
        artifacts: Optional[List[str]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """Create and persist a new experiment.

        Parameters
        ----------
        name : str
            Human-readable experiment name (e.g. ``'glacier-segmentation'``).
        params : dict
            Hyper-parameters and configuration values.
        metrics : dict
            Evaluation metrics produced by the run.
        model : str, optional
            Model identifier / architecture name.
        artifacts : list[str], optional
            Paths to artefacts to record.
        tags : dict[str, str], optional
            Free-form key/value metadata.

        Returns
        -------
        str
            The new experiment's unique identifier.
        """
        now = _now_utc()
        exp = Experiment(
            id=generate_experiment_id(),
            name=name,
            model=model,
            params=copy.deepcopy(params),
            metrics=copy.deepcopy(metrics),
            start_time=now,
            end_time=now,
            artifacts=list(artifacts) if artifacts else [],
            tags=copy.deepcopy(tags) if tags else {},
            status="completed",
        )
        self._write_experiment(exp)
        self._update_index(exp)
        logger.info("Logged experiment %s (%s)", exp.name, exp.id[:8])
        return exp.id

    def get_experiment(self, experiment_id: str) -> Experiment:
        """Retrieve an experiment by its unique identifier.

        Parameters
        ----------
        experiment_id : str
            UUID-4 hex string returned by :meth:`log_experiment`.

        Returns
        -------
        Experiment
        """
        return self._read_experiment(experiment_id)

    def compare_experiments(self, experiment_ids: List[str]) -> pd.DataFrame:
        """Build a side-by-side comparison table for the given experiments.

        Parameters
        ----------
        experiment_ids : list[str]
            Experiment identifiers to include in the table.

        Returns
        -------
        pd.DataFrame
            One row per experiment, columns for name, model, status, all
            params, all metrics, tags, and duration.
        """
        rows: list[dict[str, Any]] = []
        for eid in experiment_ids:
            exp = self._read_experiment(eid)
            row: dict[str, Any] = {
                "id": exp.id,
                "name": exp.name,
                "model": exp.model,
                "status": exp.status,
                "duration": exp.duration_str or "N/A",
            }
            for k, v in exp.params.items():
                row[f"param:{k}"] = v
            for k, v in exp.metrics.items():
                row[f"metric:{k}"] = v
            for k, v in exp.tags.items():
                row[f"tag:{k}"] = v
            rows.append(row)
        return pd.DataFrame(rows)

    def get_experiment_history(self, name: str) -> List[dict]:
        """Return all runs for a given experiment *name*.

        Parameters
        ----------
        name : str
            The experiment name to filter on.

        Returns
        -------
        list[dict]
            Chronologically sorted list of experiment dicts whose ``name``
            field matches *name*.
        """
        index = self._load_index()
        matches = [(eid, meta) for eid, meta in index.items() if meta.get("name") == name]
        # Load full experiment data for each match
        results: list[dict] = []
        for eid, _meta in matches:
            try:
                exp = self._read_experiment(eid)
                results.append(exp.to_dict())
            except FileNotFoundError:
                continue
        results.sort(key=lambda d: d.get("start_time", ""))
        return results

    def save_experiment_report(self, experiment_id: str, output_path: str) -> None:
        """Generate and write a Markdown report for a single experiment.

        Parameters
        ----------
        experiment_id : str
            Experiment to report on.
        output_path : str
            Destination file path for the Markdown report.
        """
        exp = self._read_experiment(experiment_id)
        lines: list[str] = [
            f"# Experiment Report: {exp.name}",
            "",
            f"**ID:** `{exp.id}`  ",
            f"**Model:** {exp.model or 'N/A'}  ",
            f"**Status:** {exp.status}  ",
            f"**Start:** {exp.start_time.isoformat()}  ",
            f"**End:** {exp.end_time.isoformat() if exp.end_time else 'N/A'}  ",
            f"**Duration:** {exp.duration_str or 'N/A'}",
            "",
            "## Parameters",
            "",
        ]
        if exp.params:
            for k, v in exp.params.items():
                lines.append(f"- **{k}:** {v}")
        else:
            lines.append("_None recorded._")
        lines += ["", "## Metrics", ""]
        if exp.metrics:
            for k, v in exp.metrics.items():
                lines.append(f"- **{k}:** {v}")
        else:
            lines.append("_None recorded._")
        lines += ["", "## Tags", ""]
        if exp.tags:
            for k, v in exp.tags.items():
                lines.append(f"- **{k}:** {v}")
        else:
            lines.append("_None._")
        lines += ["", "## Artifacts", ""]
        if exp.artifacts:
            for art in exp.artifacts:
                lines.append(f"- `{art}`")
        else:
            lines.append("_None._")
        lines.append("")
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Report written to %s", out)

    def compute_experiment_stats(self, experiments: List[Experiment]) -> dict:
        """Compute aggregate statistics over a list of experiments.

        For each numeric metric, returns ``mean``, ``std``, ``best``,
        ``worst``, ``min``, and ``max``.

        Parameters
        ----------
        experiments : list[Experiment]
            Experiments to aggregate.

        Returns
        -------
        dict
            Nested ``{metric_name: {stat_name: value}}``.
        """
        if not experiments:
            return {}

        # Collect all metric keys
        all_keys: set[str] = set()
        for exp in experiments:
            all_keys.update(exp.metrics.keys())

        stats: dict[str, dict[str, float]] = {}
        for key in sorted(all_keys):
            values: list[float] = []
            for exp in experiments:
                val = exp.metrics.get(key)
                if val is not None:
                    try:
                        values.append(float(val))
                    except (TypeError, ValueError):
                        continue
            if not values:
                continue
            arr = np.array(values, dtype=np.float64)
            stats[key] = {
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr)) if len(arr) > 1 else 0.0,
                "best": float(np.max(arr)),
                "worst": float(np.min(arr)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "count": len(values),
            }
        return stats

    def tag_experiment(self, experiment_id: str, tags: Dict[str, str]) -> None:
        """Add or overwrite tags on an existing experiment.

        Parameters
        ----------
        experiment_id : str
            Target experiment.
        tags : dict[str, str]
            Key/value pairs to merge into the existing tags.
        """
        exp = self._read_experiment(experiment_id)
        exp.tags.update(tags)
        self._write_experiment(exp)
        self._update_index(exp)
        logger.debug("Tagged experiment %s with %s", experiment_id[:8], list(tags))

    def search_experiments(self, query: Dict[str, Any]) -> List[dict]:
        """Search experiments by name, model, status, or tags.

        Supported query keys:

        - ``name``: substring match (case-insensitive)
        - ``model``: substring match (case-insensitive)
        - ``status``: exact match
        - ``tags``: dict where each key/value pair must appear in the
          experiment's tags

        Parameters
        ----------
        query : dict
            Filter criteria.

        Returns
        -------
        list[dict]
            Matching experiment dicts.
        """
        index = self._load_index()
        results: list[dict] = []
        for eid, meta in index.items():
            if "name" in query and query["name"].lower() not in meta.get("name", "").lower():
                continue
            if "model" in query and query["model"].lower() not in meta.get("model", "").lower():
                continue
            if "status" in query and meta.get("status") != query["status"]:
                continue
            if "tags" in query:
                exp_tags = meta.get("tags", {})
                if not all(exp_tags.get(k) == v for k, v in query["tags"].items()):
                    continue
            try:
                exp = self._read_experiment(eid)
                results.append(exp.to_dict())
            except FileNotFoundError:
                continue
        return results

    def delete_experiment(self, experiment_id: str) -> None:
        """Remove an experiment and its artefacts from disk.

        Parameters
        ----------
        experiment_id : str
            Identifier of the experiment to delete.
        """
        # Remove from index
        index = self._load_index()
        index.pop(experiment_id, None)
        self._save_index(index)
        # Remove directory
        exp_dir = self._experiment_dir(experiment_id)
        if exp_dir.exists():
            shutil.rmtree(exp_dir)
            logger.info("Deleted experiment %s", experiment_id[:8])

    def list_experiments(
        self,
        *,
        name: Optional[str] = None,
        model: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[dict]:
        """List all experiments with optional filters.

        Parameters
        ----------
        name : str, optional
            Substring filter on experiment name.
        model : str, optional
            Substring filter on model name.
        status : str, optional
            Exact status filter.

        Returns
        -------
        list[dict]
            Lightweight dicts with ``id``, ``name``, ``model``, ``status``,
            ``tags``, and ``start_time``.
        """
        index = self._load_index()
        results: list[dict] = []
        for eid, meta in index.items():
            if name and name.lower() not in meta.get("name", "").lower():
                continue
            if model and model.lower() not in meta.get("model", "").lower():
                continue
            if status and meta.get("status") != status:
                continue
            results.append({"id": eid, **meta})
        results.sort(key=lambda d: d.get("start_time", ""), reverse=True)
        return results

    def export_all(self, output_path: str) -> None:
        """Export every experiment to a single JSON file.

        Parameters
        ----------
        output_path : str
            Destination path for the combined JSON export.
        """
        index = self._load_index()
        experiments: list[dict] = []
        for eid in index:
            try:
                exp = self._read_experiment(eid)
                experiments.append(exp.to_dict())
            except FileNotFoundError:
                continue
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(experiments, indent=2, default=str), encoding="utf-8")
        logger.info("Exported %d experiments to %s", len(experiments), out)

    def import_all(self, input_path: str) -> int:
        """Import experiments from a JSON file previously created by :meth:`export_all`.

        Parameters
        ----------
        input_path : str
            Path to the JSON export file.

        Returns
        -------
        int
            Number of experiments imported.
        """
        raw = Path(input_path).read_text(encoding="utf-8")
        experiments: list[dict] = json.loads(raw)
        count = 0
        for data in experiments:
            exp = Experiment.from_dict(data)
            self._write_experiment(exp)
            self._update_index(exp)
            count += 1
        logger.info("Imported %d experiments from %s", count, input_path)
        return count
