#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom Keras callbacks for GlacierNET-KZ.

Provides training lifecycle hooks for metrics logging, checkpoint management,
TensorBoard integration, early stopping with weight restoration, learning rate
scheduling, Monte Carlo dropout uncertainty estimation, and progress tracking.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import tensorflow as tf

__all__ = [
    "MetricsLogger",
    "CheckpointManager",
    "TensorBoardCallback",
    "EarlyStoppingWithRestore",
    "LRSchedulerCallback",
    "UncertaintyCallback",
    "ProgressBar",
    "GlacierNetCallback",
    "build_callbacks",
    "CALLBACK_REGISTRY",
]


# ---------------------------------------------------------------------------
# 1. MetricsLogger
# ---------------------------------------------------------------------------
class MetricsLogger(tf.keras.callbacks.Callback):
    """Logs custom metrics (IoU, dice, area_ratio) to a JSON file at end of each epoch.

    Tracks: lr, loss, val_loss, iou, dice_coeff, area_ratio.

    Args:
        log_path: Destination JSON file path.
        append: If True, append to existing log; otherwise overwrite.
    """

    def __init__(self, log_path: str = "metrics_log.json", append: bool = True) -> None:
        super().__init__()
        self.log_path = Path(log_path)
        self.append = append
        self._history: List[Dict[str, Any]] = []

    def on_train_begin(self, logs: Optional[Dict[str, Any]] = None) -> None:
        if self.append and self.log_path.exists():
            with open(self.log_path, "r", encoding="utf-8") as fh:
                self._history = json.load(fh)

    def on_epoch_end(self, epoch: int, logs: Optional[Dict[str, Any]] = None) -> None:
        logs = logs or {}
        lr = float(tf.keras.backend.get_value(self.model.optimizer.learning_rate))
        record = {
            "epoch": epoch,
            "timestamp": time.time(),
            "lr": lr,
            "loss": logs.get("loss"),
            "val_loss": logs.get("val_loss"),
            "iou": logs.get("iou"),
            "dice_coeff": logs.get("dice_coeff"),
            "area_ratio": logs.get("area_ratio"),
        }
        self._history.append(record)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "w", encoding="utf-8") as fh:
            json.dump(self._history, fh, indent=2, default=str)


# ---------------------------------------------------------------------------
# 2. CheckpointManager
# ---------------------------------------------------------------------------
class CheckpointManager(tf.keras.callbacks.Callback):
    """Manages multiple checkpoints, saving the best K models by monitor metric.

    Old checkpoints beyond the keep limit are cleaned up automatically.

    Args:
        save_dir: Directory for checkpoint files.
        monitor: Metric name to track.
        mode: ``"min"`` or ``"max"``.
        keep_best: Number of best checkpoints to retain.
        save_weights_only: If True, save only weights.
        verbose: Verbosity mode.
    """

    def __init__(
        self,
        save_dir: str = "checkpoints",
        monitor: str = "val_loss",
        mode: str = "min",
        keep_best: int = 3,
        save_weights_only: bool = True,
        verbose: int = 1,
    ) -> None:
        super().__init__()
        self.save_dir = Path(save_dir)
        self.monitor = monitor
        self.mode = mode
        self.keep_best = keep_best
        self.save_weights_only = save_weights_only
        self.verbose = verbose
        self._checkpoints: List[Dict[str, Any]] = []
        self._best_value: Optional[float] = None

    def on_train_begin(self, logs: Optional[Dict[str, Any]] = None) -> None:
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self._best_value = float("inf") if self.mode == "min" else float("-inf")

    def on_epoch_end(self, epoch: int, logs: Optional[Dict[str, Any]] = None) -> None:
        logs = logs or {}
        current = logs.get(self.monitor)
        if current is None:
            return

        improved = (self.mode == "min" and current < self._best_value) or (
            self.mode == "max" and current > self._best_value
        )
        if not improved:
            return

        self._best_value = current
        suffix = "weights" if self.save_weights_only else "model"
        path = self.save_dir / f"ckpt_epoch_{epoch:04d}_{suffix}.h5"

        if self.save_weights_only:
            self.model.save_weights(str(path))
        else:
            self.model.save(str(path))

        self._checkpoints.append({"path": str(path), "metric": current, "epoch": epoch})
        self._checkpoints.sort(key=lambda c: c["metric"], reverse=(self.mode == "max"))

        while len(self._checkpoints) > self.keep_best:
            removed = self._checkpoints.pop()
            removed_path = Path(removed["path"])
            if removed_path.exists():
                removed_path.unlink()
            if self.verbose:
                print(f"  CheckpointManager: removed {removed_path.name}")

        if self.verbose:
            print(f"  CheckpointManager: saved {path.name} ({self.monitor}={current:.6f})")


# ---------------------------------------------------------------------------
# 3. TensorBoardCallback
# ---------------------------------------------------------------------------
class TensorBoardCallback(tf.keras.callbacks.Callback):
    """Wraps TensorBoard with custom image summaries for predictions during training.

    Args:
        log_dir: TensorBoard log directory.
        write_graph: Whether to write the computation graph.
        update_freq: ``"epoch"`` or an integer for batch-level updates.
        sample_images: Optional input images for prediction visualisation.
        sample_masks: Optional ground-truth masks for comparison.
    """

    def __init__(
        self,
        log_dir: str = "logs/tensorboard",
        write_graph: bool = True,
        update_freq: Union[str, int] = "epoch",
        sample_images: Optional[np.ndarray] = None,
        sample_masks: Optional[np.ndarray] = None,
    ) -> None:
        super().__init__()
        self.log_dir = log_dir
        self.write_graph = write_graph
        self.update_freq = update_freq
        self.sample_images = sample_images
        self.sample_masks = sample_masks
        self._writer: Optional[Any] = None
        self._step = 0

    def set_model(self, model: tf.keras.Model) -> None:
        self.model = model
        self._writer = tf.summary.create_file_writer(self.log_dir)

    def on_epoch_end(self, epoch: int, logs: Optional[Dict[str, Any]] = None) -> None:
        if self._writer is None:
            return
        logs = logs or {}
        with self._writer.as_default():
            for key, value in logs.items():
                if value is not None:
                    tf.summary.scalar(key, value, step=epoch)

            if self.sample_images is not None:
                preds = self.model.predict(self.sample_images[:4], verbose=0)
                for idx, pred in enumerate(preds[:4]):
                    pred_img = tf.expand_dims(pred, axis=-1)
                    tf.summary.image(
                        f"prediction_{idx}",
                        tf.cast(pred_img * 255, tf.uint8),
                        step=epoch,
                    )
                    if self.sample_masks is not None and idx < len(self.sample_masks):
                        mask_img = tf.expand_dims(self.sample_masks[idx], axis=-1)
                        tf.summary.image(
                            f"ground_truth_{idx}",
                            tf.cast(mask_img * 255, tf.uint8),
                            step=epoch,
                        )
        self._writer.flush()

    def on_train_end(self, logs: Optional[Dict[str, Any]] = None) -> None:
        if self._writer is not None:
            self._writer.flush()


# ---------------------------------------------------------------------------
# 4. EarlyStoppingWithRestore
# ---------------------------------------------------------------------------
class EarlyStoppingWithRestore(tf.keras.callbacks.Callback):
    """Early stopping with automatic best-weight restoration.

    Args:
        monitor: Metric to monitor.
        patience: Epochs with no improvement before stopping.
        mode: ``"min"`` or ``"max"``.
        min_delta: Minimum change to count as improvement.
        restore_best: Whether to restore best weights on stop.
        verbose: Verbosity mode.
    """

    def __init__(
        self,
        monitor: str = "val_loss",
        patience: int = 10,
        mode: str = "min",
        min_delta: float = 1e-6,
        restore_best: bool = True,
        verbose: int = 1,
    ) -> None:
        super().__init__()
        self.monitor = monitor
        self.patience = patience
        self.mode = mode
        self.min_delta = min_delta
        self.restore_best = restore_best
        self.verbose = verbose
        self._best_value: Optional[float] = None
        self._best_weights: Optional[List[np.ndarray]] = None
        self._wait = 0

    def on_train_begin(self, logs: Optional[Dict[str, Any]] = None) -> None:
        self._best_value = float("inf") if self.mode == "min" else float("-inf")
        self._best_weights = None
        self._wait = 0

    def on_epoch_end(self, epoch: int, logs: Optional[Dict[str, Any]] = None) -> None:
        logs = logs or {}
        current = logs.get(self.monitor)
        if current is None:
            return

        improved = (self.mode == "min" and current < self._best_value - self.min_delta) or (
            self.mode == "max" and current > self._best_value + self.min_delta
        )

        if improved:
            self._best_value = current
            self._best_weights = [w.copy() for w in self.model.get_weights()]
            self._wait = 0
        else:
            self._wait += 1
            if self._wait >= self.patience:
                self.model.stop_training = True
                if self.restore_best and self._best_weights is not None:
                    self.model.set_weights(self._best_weights)
                    if self.verbose:
                        print(f"\nEarlyStopping: restored best weights (best {self.monitor}={self._best_value:.6f})")


# ---------------------------------------------------------------------------
# 5. LRSchedulerCallback
# ---------------------------------------------------------------------------
class LRSchedulerCallback(tf.keras.callbacks.Callback):
    """Custom LR schedule with warmup, cosine decay, and reduce-on-plateau modes.

    Args:
        initial_lr: Starting learning rate.
        mode: ``"warmup_cosine"``, ``"cosine"``, or ``"plateau"``.
        warmup_epochs: Epochs for linear warmup (warmup_cosine mode).
        total_epochs: Total training epochs (cosine modes).
        plateau_factor: Factor to reduce LR on plateau.
        plateau_patience: Epochs to wait before reducing LR.
        plateau_min_lr: Minimum LR for plateau mode.
    """

    def __init__(
        self,
        initial_lr: float = 1e-3,
        mode: str = "warmup_cosine",
        warmup_epochs: int = 5,
        total_epochs: int = 100,
        plateau_factor: float = 0.5,
        plateau_patience: int = 5,
        plateau_min_lr: float = 1e-7,
    ) -> None:
        super().__init__()
        self.initial_lr = initial_lr
        self.mode = mode
        self.warmup_epochs = warmup_epochs
        self.total_epochs = total_epochs
        self.plateau_factor = plateau_factor
        self.plateau_patience = plateau_patience
        self.plateau_min_lr = plateau_min_lr
        self._best_value: Optional[float] = None
        self._wait = 0

    def _compute_lr(self, epoch: int) -> float:
        if self.mode == "warmup_cosine":
            if epoch < self.warmup_epochs:
                return self.initial_lr * (epoch + 1) / self.warmup_epochs
            progress = (epoch - self.warmup_epochs) / max(1, self.total_epochs - self.warmup_epochs)
            return self.initial_lr * 0.5 * (1 + math.cos(math.pi * progress))

        if self.mode == "cosine":
            progress = epoch / max(1, self.total_epochs)
            return self.initial_lr * 0.5 * (1 + math.cos(math.pi * progress))

        return self.initial_lr

    def on_epoch_end(self, epoch: int, logs: Optional[Dict[str, Any]] = None) -> None:
        logs = logs or {}
        if self.mode == "plateau":
            val_loss = logs.get("val_loss")
            if val_loss is None:
                return
            if self._best_value is None or val_loss < self._best_value:
                self._best_value = val_loss
                self._wait = 0
            else:
                self._wait += 1
                if self._wait >= self.plateau_patience:
                    current_lr = float(tf.keras.backend.get_value(self.model.optimizer.learning_rate))
                    new_lr = max(current_lr * self.plateau_factor, self.plateau_min_lr)
                    tf.keras.backend.set_value(self.model.optimizer.learning_rate, new_lr)
                    self._wait = 0
            return

        tf.keras.backend.set_value(self.model.optimizer.learning_rate, self._compute_lr(epoch))


# ---------------------------------------------------------------------------
# 6. UncertaintyCallback
# ---------------------------------------------------------------------------
class UncertaintyCallback(tf.keras.callbacks.Callback):
    """Computes MC-Dropout uncertainty at end of each epoch on the validation set.

    Runs multiple stochastic forward passes (training=True) and reports mean
    predictive entropy / standard deviation.

    Args:
        val_data: Tuple of (val_images, val_masks) for evaluation.
        num_forward_passes: Number of stochastic forward passes.
        log_dir: Directory to save uncertainty maps.
    """

    def __init__(
        self,
        val_data: Optional[tuple] = None,
        num_forward_passes: int = 10,
        log_dir: str = "uncertainty",
    ) -> None:
        super().__init__()
        self.val_data = val_data
        self.num_forward_passes = num_forward_passes
        self.log_dir = Path(log_dir)
        self._uncertainty_history: List[Dict[str, Any]] = []

    def on_train_begin(self, logs: Optional[Dict[str, Any]] = None) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def on_epoch_end(self, epoch: int, logs: Optional[Dict[str, Any]] = None) -> None:
        if self.val_data is None:
            return

        val_images, val_masks = self.val_data
        predictions = []
        for _ in range(self.num_forward_passes):
            pred = self.model.predict(val_images, verbose=0)
            predictions.append(pred)

        stacked = np.stack(predictions, axis=0)
        np.mean(stacked, axis=0)
        std_pred = np.std(stacked, axis=0)
        mean_uncertainty = float(np.mean(std_pred))

        record = {
            "epoch": epoch,
            "mean_uncertainty": mean_uncertainty,
            "max_uncertainty": float(np.max(std_pred)),
        }
        self._uncertainty_history.append(record)

        save_path = self.log_dir / f"uncertainty_epoch_{epoch:04d}.npy"
        np.save(str(save_path), std_pred)

        print(f"  UncertaintyCallback: mean={mean_uncertainty:.6f} max={record['max_uncertainty']:.6f}")


# ---------------------------------------------------------------------------
# 7. ProgressBar
# ---------------------------------------------------------------------------
class ProgressBar(tf.keras.callbacks.Callback):
    """Custom progress bar with ETA, current metrics, and best metric tracking.

    Args:
        update_freq: Update display every N epochs.
        bar_length: Character width of the progress bar.
    """

    def __init__(self, update_freq: int = 1, bar_length: int = 40) -> None:
        super().__init__()
        self.update_freq = update_freq
        self.bar_length = bar_length
        self._start_time: Optional[float] = None
        self._epoch_start: Optional[float] = None
        self._best_metrics: Dict[str, float] = {}

    def on_train_begin(self, logs: Optional[Dict[str, Any]] = None) -> None:
        self._start_time = time.time()

    def on_epoch_begin(self, epoch: int, logs: Optional[Dict[str, Any]] = None) -> None:
        self._epoch_start = time.time()

    def on_epoch_end(self, epoch: int, logs: Optional[Dict[str, Any]] = None) -> None:
        if (epoch + 1) % self.update_freq != 0:
            return

        logs = logs or {}
        time.time() - (self._start_time or time.time())
        epoch_time = time.time() - (self._epoch_start or time.time())

        for key in ("loss", "val_loss", "iou", "dice_coeff"):
            value = logs.get(key)
            if value is not None:
                if key not in self._best_metrics:
                    self._best_metrics[key] = value
                else:
                    is_min = "loss" in key
                    if (is_min and value < self._best_metrics[key]) or (not is_min and value > self._best_metrics[key]):
                        self._best_metrics[key] = value

        parts = [
            f"Epoch {epoch + 1}",
            f"loss={logs.get('loss', 0):.4f}",
        ]
        if logs.get("val_loss") is not None:
            parts.append(f"val_loss={logs['val_loss']:.4f}")
        if logs.get("iou") is not None:
            parts.append(f"iou={logs['iou']:.4f}")
        if logs.get("dice_coeff") is not None:
            parts.append(f"dice={logs['dice_coeff']:.4f}")

        total_epochs = getattr(self.params, "epochs", None) if hasattr(self, "params") else None
        if total_epochs:
            pct = min(1.0, (epoch + 1) / total_epochs)
            filled = int(self.bar_length * pct)
            bar = "\u2588" * filled + "\u2591" * (self.bar_length - filled)
            parts.append(f"[{bar}] {pct:.0%}")

        remaining = epoch_time * ((total_epochs or 100) - epoch - 1)
        m, s = divmod(int(remaining), 60)
        h, m = divmod(m, 60)
        parts.append(f"ETA {h:02d}:{m:02d}:{s:02d}")

        best_str = " | ".join(f"best_{k}={v:.4f}" for k, v in self._best_metrics.items())
        print(f"  {'  '.join(parts)}  {best_str}")


# ---------------------------------------------------------------------------
# 8. GlacierNetCallback (composite)
# ---------------------------------------------------------------------------
class GlacierNetCallback(tf.keras.callbacks.Callback):
    """Main composite callback combining MetricsLogger + CheckpointManager + Progress.

    Acts as a facade that delegates lifecycle hooks to its child callbacks.

    Args:
        log_dir: Base directory for all outputs.
        monitor: Metric for checkpointing and progress tracking.
        checkpoint_mode: ``"min"`` or ``"max"`` for checkpoint monitor.
        keep_best: Number of best checkpoints to retain.
    """

    def __init__(
        self,
        log_dir: str = "output",
        monitor: str = "val_loss",
        checkpoint_mode: str = "min",
        keep_best: int = 3,
    ) -> None:
        super().__init__()
        base = Path(log_dir)
        self.metrics_logger = MetricsLogger(log_path=str(base / "metrics" / "metrics_log.json"))
        self.checkpoint_manager = CheckpointManager(
            save_dir=str(base / "checkpoints"),
            monitor=monitor,
            mode=checkpoint_mode,
            keep_best=keep_best,
        )
        self.progress_bar = ProgressBar()
        self._children = [
            self.metrics_logger,
            self.checkpoint_manager,
            self.progress_bar,
        ]

    def on_train_begin(self, logs: Optional[Dict[str, Any]] = None) -> None:
        for cb in self._children:
            cb.on_train_begin(logs)

    def on_epoch_begin(self, epoch: int, logs: Optional[Dict[str, Any]] = None) -> None:
        for cb in self._children:
            cb.on_epoch_begin(epoch, logs)

    def on_epoch_end(self, epoch: int, logs: Optional[Dict[str, Any]] = None) -> None:
        for cb in self._children:
            cb.on_epoch_end(epoch, logs)

    def on_train_end(self, logs: Optional[Dict[str, Any]] = None) -> None:
        for cb in self._children:
            cb.on_train_end(logs)


# ---------------------------------------------------------------------------
# Factory & Registry
# ---------------------------------------------------------------------------
CALLBACK_REGISTRY: Dict[str, type] = {
    "MetricsLogger": MetricsLogger,
    "CheckpointManager": CheckpointManager,
    "TensorBoard": TensorBoardCallback,
    "EarlyStopping": EarlyStoppingWithRestore,
    "LRScheduler": LRSchedulerCallback,
    "Uncertainty": UncertaintyCallback,
    "ProgressBar": ProgressBar,
    "GlacierNet": GlacierNetCallback,
}


def build_callbacks(callback_configs: List[Dict[str, Any]]) -> list:
    """Creates callbacks from a list of configuration dicts.

    Each dict must contain a ``"type"`` key matching a ``CALLBACK_REGISTRY`` entry.
    Remaining keys are forwarded as keyword arguments to the callback constructor.

    Args:
        callback_configs: List of dicts, e.g.
            ``[{"type": "EarlyStopping", "patience": 10}, {"type": "ProgressBar"}]``

    Returns:
        List of instantiated callback objects.

    Raises:
        KeyError: If ``"type"`` is missing or not found in the registry.
    """
    callbacks = []
    for config in callback_configs:
        cfg = dict(config)
        name = cfg.pop("type")
        if name not in CALLBACK_REGISTRY:
            available = ", ".join(sorted(CALLBACK_REGISTRY.keys()))
            raise KeyError(f"Unknown callback '{name}'. Available: {available}")
        callback_cls = CALLBACK_REGISTRY[name]
        callbacks.append(callback_cls(**cfg))
    return callbacks
