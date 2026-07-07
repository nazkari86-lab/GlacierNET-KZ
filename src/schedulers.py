#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive learning rate scheduler module for GlacierNET-KZ.

Supports:
- Cosine Annealing (with warm restarts)
- Warmup Cosine Decay
- Warmup Linear Decay
- Exponential Decay
- Step Decay
- Polynomial Decay
- Reduce-on-Plateau (callback)
- Cyclic / One-Cycle

Usage::

    from src.schedulers import build_scheduler, SchedulerConfig

    cfg = SchedulerConfig(
        name="warmup_cosine",
        initial_lr=1e-4,
        min_lr=1e-6,
        warmup_epochs=5,
        total_epochs=100,
        steps_per_epoch=50,
    )
    schedule = build_scheduler(cfg, optimizer)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)

__all__ = [
    "SchedulerConfig",
    "WarmupCosineDecay",
    "PolynomialDecay",
    "build_scheduler",
    "get_scheduler_fn",
    "create_warmup_schedule",
    "list_schedulers",
    "SCHEDULER_REGISTRY",
]


# ────────────────────────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────────────────────────


@dataclass
class SchedulerConfig:
    """Configuration for a learning-rate scheduler."""

    name: str = (
        "cosine"  # cosine, warmup_cosine, warmup_linear, exponential, step, polynomial, plateau, cyclic, one_cycle
    )
    initial_lr: float = 1e-4
    min_lr: float = 1e-6
    warmup_epochs: int = 0
    total_epochs: int = 100
    decay_steps: int = 0  # for step decay
    decay_rate: float = 0.1  # for step & exponential decay
    patience: int = 8  # for plateau
    factor: float = 0.5  # for plateau
    mode: str = "min"  # for plateau ('min' or 'max')
    cycle_momentum: bool = False  # for cyclic
    max_lr: float = 1e-3  # for cyclic / one_cycle
    steps_per_epoch: int = 0  # required for cyclic / one_cycle

    def validate(self) -> list[str]:
        """Return a list of validation error strings (empty if OK)."""
        errors: list[str] = []
        valid_names = {
            "cosine",
            "warmup_cosine",
            "warmup_linear",
            "exponential",
            "step",
            "polynomial",
            "plateau",
            "cyclic",
            "one_cycle",
        }
        if self.name not in valid_names:
            errors.append(f"Unknown scheduler: {self.name!r}. Valid: {sorted(valid_names)}")
        if self.initial_lr <= 0:
            errors.append(f"initial_lr={self.initial_lr} must be > 0")
        if self.min_lr < 0:
            errors.append(f"min_lr={self.min_lr} must be >= 0")
        if self.warmup_epochs < 0:
            errors.append(f"warmup_epochs={self.warmup_epochs} must be >= 0")
        if self.total_epochs <= 0:
            errors.append(f"total_epochs={self.total_epochs} must be > 0")
        if self.name in {"cyclic", "one_cycle"} and self.steps_per_epoch <= 0:
            errors.append(f"steps_per_epoch={self.steps_per_epoch} must be > 0 for {self.name}")
        return errors


# ────────────────────────────────────────────────────────────────────
# CUSTOM SCHEDULE CLASSES
# ────────────────────────────────────────────────────────────────────


class WarmupCosineDecay:
    """Cosine decay from *initial_lr* to *min_lr* with a linear warmup phase.

    Implements ``tf.keras.optimizers.schedules.LearningRateSchedule`` so it
    can be passed directly to ``tf.keras.optimizers.Adam(learning_rate=…)``.

    Parameters
    ----------
    initial_lr : float
        Peak learning rate after warmup.
    min_lr : float
        Final (minimum) learning rate at the end of training.
    warmup_steps : int
        Number of steps for the linear warmup ramp.
    total_steps : int
        Total training steps (warmup + decay).
    """

    def __init__(
        self,
        initial_lr: float,
        min_lr: float,
        warmup_steps: int,
        total_steps: int,
    ) -> None:
        self.initial_lr = float(initial_lr)
        self.min_lr = float(min_lr)
        self.warmup_steps = max(int(warmup_steps), 0)
        self.total_steps = max(int(total_steps), 1)
        self.decay_steps = self.total_steps - self.warmup_steps

    def __call__(self, step) -> float:
        import tensorflow as tf

        step = tf.cast(step, tf.float64)
        warmup = tf.cast(self.warmup_steps, tf.float64)
        decay_steps = tf.cast(self.decay_steps, tf.float64)
        initial = tf.constant(self.initial_lr, dtype=tf.float64)
        minimum = tf.constant(self.min_lr, dtype=tf.float64)

        # Linear warmup: ramp from 0 → initial_lr
        warmup_lr = initial * step / tf.maximum(warmup, 1.0)

        # Cosine decay: initial_lr → min_lr
        progress = (step - warmup) / tf.maximum(decay_steps, 1.0)
        progress = tf.clip_by_value(progress, 0.0, 1.0)
        cosine_decay = 0.5 * (1.0 + tf.cos(tf.constant(3.141592653589793) * progress))
        cosine_lr = minimum + (initial - minimum) * cosine_decay

        return tf.where(step < warmup, warmup_lr, cosine_lr)

    def get_config(self) -> dict[str, Any]:
        return {
            "initial_lr": self.initial_lr,
            "min_lr": self.min_lr,
            "warmup_steps": self.warmup_steps,
            "total_steps": self.total_steps,
        }


class PolynomialDecay:
    """Polynomial decay from *initial_lr* to *min_lr* over *decay_steps*.

    Implements ``tf.keras.optimizers.schedules.LearningRateSchedule``.

    ``power`` controls the decay curve: linear (power=1), quadratic (power=2),
    square-root (power=0.5), etc.

    Parameters
    ----------
    initial_lr : float
        Starting learning rate.
    min_lr : float
        Final learning rate (floor).
    decay_steps : int
        Number of steps over which to decay.
    power : float
        Polynomial exponent.
    """

    def __init__(
        self,
        initial_lr: float,
        min_lr: float,
        decay_steps: int,
        power: float = 1.0,
    ) -> None:
        self.initial_lr = float(initial_lr)
        self.min_lr = float(min_lr)
        self.decay_steps = max(int(decay_steps), 1)
        self.power = float(power)

    def __call__(self, step) -> float:
        import tensorflow as tf

        step = tf.cast(step, tf.float64)
        decay_steps = tf.constant(self.decay_steps, dtype=tf.float64)
        initial = tf.constant(self.initial_lr, dtype=tf.float64)
        minimum = tf.constant(self.min_lr, dtype=tf.float64)

        p = tf.constant(self.power, dtype=tf.float64)
        progress = tf.minimum(step / decay_steps, 1.0)
        return minimum + (initial - minimum) * tf.pow(1.0 - progress, p)

    def get_config(self) -> dict[str, Any]:
        return {
            "initial_lr": self.initial_lr,
            "min_lr": self.min_lr,
            "decay_steps": self.decay_steps,
            "power": self.power,
        }


# ────────────────────────────────────────────────────────────────────
# BUILT-IN SCHEDULE FACTORIES
# ────────────────────────────────────────────────────────────────────


def _cosine_annealing(cfg: SchedulerConfig, optimizer=None) -> Callable:
    """Cosine annealing from initial_lr to min_lr (no warmup)."""
    total_steps = cfg.total_epochs * max(cfg.steps_per_epoch, 1)
    return WarmupCosineDecay(
        initial_lr=cfg.initial_lr,
        min_lr=cfg.min_lr,
        warmup_steps=0,
        total_steps=total_steps,
    )


def _warmup_cosine(cfg: SchedulerConfig, optimizer=None) -> Callable:
    """Linear warmup followed by cosine decay."""
    total_steps = cfg.total_epochs * max(cfg.steps_per_epoch, 1)
    warmup_steps = cfg.warmup_epochs * max(cfg.steps_per_epoch, 1)
    return WarmupCosineDecay(
        initial_lr=cfg.initial_lr,
        min_lr=cfg.min_lr,
        warmup_steps=warmup_steps,
        total_steps=total_steps,
    )


def _warmup_linear(cfg: SchedulerConfig, optimizer=None) -> Callable:
    """Linear warmup followed by linear decay to min_lr."""
    import tensorflow as tf

    total_steps = cfg.total_epochs * max(cfg.steps_per_epoch, 1)
    warmup_steps = cfg.warmup_epochs * max(cfg.steps_per_epoch, 1)
    decay_steps = total_steps - warmup_steps

    initial = float(cfg.initial_lr)
    minimum = float(cfg.min_lr)
    warmup_f = float(max(warmup_steps, 1))
    decay_f = float(max(decay_steps, 1))

    def schedule(step):
        s = tf.cast(step, tf.float64)
        warmup_lr = initial * s / warmup_f
        linear_decay = initial - (initial - minimum) * (s - warmup_f) / decay_f
        linear_decay = tf.clip_by_value(linear_decay, minimum, initial)
        return tf.where(s < warmup_f, warmup_lr, linear_decay)

    return schedule


def _exponential_decay(cfg: SchedulerConfig, optimizer=None) -> Callable:
    """Exponential decay: lr = initial_lr * decay_rate ^ (step / decay_steps)."""
    import tensorflow as tf

    steps_per_epoch = max(cfg.steps_per_epoch, 1)
    decay_steps = max(cfg.decay_steps, 1) * steps_per_epoch
    initial = float(cfg.initial_lr)
    rate = float(cfg.decay_rate)

    def schedule(step):
        s = tf.cast(step, tf.float64)
        return initial * tf.pow(rate, s / float(decay_steps))

    return schedule


def _step_decay(cfg: SchedulerConfig, optimizer=None) -> Callable:
    """Step decay: multiply lr by decay_rate every decay_steps epochs."""
    import tensorflow as tf

    steps_per_epoch = max(cfg.steps_per_epoch, 1)
    decay_step_size = max(cfg.decay_steps, 1) * steps_per_epoch
    initial = float(cfg.initial_lr)
    rate = float(cfg.decay_rate)

    def schedule(step):
        s = tf.cast(step, tf.float64)
        factor = tf.pow(rate, tf.floor(s / float(decay_step_size)))
        return initial * factor

    return schedule


def _polynomial_decay(cfg: SchedulerConfig, optimizer=None) -> Callable:
    """Polynomial decay from initial_lr to min_lr."""
    total_steps = cfg.total_epochs * max(cfg.steps_per_epoch, 1)
    warmup_steps = cfg.warmup_epochs * max(cfg.steps_per_epoch, 1)
    return PolynomialDecay(
        initial_lr=cfg.initial_lr,
        min_lr=cfg.min_lr,
        decay_steps=total_steps - warmup_steps,
        power=1.0,
    )


def _plateau(cfg: SchedulerConfig, optimizer=None) -> Callable:
    """Reduce-on-plateau returns a callback (not a schedule function).

    The callback is stored as ``_plateau_callback`` on the returned object.
    Call ``get_scheduler_fn("plateau")(cfg)`` and attach the callback to
    ``model.fit()``.
    """
    import tensorflow as tf

    callback = tf.keras.callbacks.ReduceLROnPlateau(
        monitor="val_dice_coefficient" if cfg.mode == "max" else "val_loss",
        mode=cfg.mode,
        factor=cfg.factor,
        patience=cfg.patience,
        min_lr=cfg.min_lr,
        verbose=1,
    )

    # Return a dummy callable so it can be used in ``build_scheduler`` without
    # breaking the API, but the real work is the callback.
    def _noop(step):
        # Return a constant; the callback handles the actual adjustment.
        return cfg.initial_lr

    _noop._plateau_callback = callback  # type: ignore[attr-defined]
    return _noop


def _cyclic(cfg: SchedulerConfig, optimizer=None) -> Callable:
    """Triangular cyclic schedule (Smith 2017)."""
    import tensorflow as tf

    steps_per_cycle = max(cfg.steps_per_epoch * max(cfg.decay_steps or 1, 1), 1)
    base_lr = cfg.min_lr
    max_lr = cfg.max_lr

    def schedule(step):
        s = tf.cast(step, tf.float64)
        cycle = tf.floor(1.0 + s / float(steps_per_cycle))
        x = tf.abs(s / float(steps_per_cycle) - cycle + 1.0)
        return base_lr + (max_lr - base_lr) * tf.maximum(1.0 - x, 0.0)

    return schedule


def _one_cycle(cfg: SchedulerConfig, optimizer=None) -> Callable:
    """One-cycle policy (Smith & Topin 2019): warmup to max_lr, then anneal."""
    import tensorflow as tf

    total_steps = cfg.total_epochs * max(cfg.steps_per_epoch, 1)
    base_lr = cfg.min_lr
    max_lr = cfg.max_lr
    step_up = total_steps // 2

    def schedule(step):
        s = tf.cast(step, tf.float64)
        up = tf.minimum(s / float(step_up), 1.0)
        down = tf.minimum((s - step_up) / float(total_steps - step_up), 1.0)
        lr_up = base_lr + (max_lr - base_lr) * up
        lr_down = max_lr - (max_lr - base_lr) * down
        return tf.where(s < step_up, lr_up, lr_down)

    return schedule


# ────────────────────────────────────────────────────────────────────
# REGISTRY
# ────────────────────────────────────────────────────────────────────


SCHEDULER_REGISTRY: dict[str, Callable[[SchedulerConfig, Any], Any]] = {
    "cosine": _cosine_annealing,
    "warmup_cosine": _warmup_cosine,
    "warmup_linear": _warmup_linear,
    "exponential": _exponential_decay,
    "step": _step_decay,
    "polynomial": _polynomial_decay,
    "plateau": _plateau,
    "cyclic": _cyclic,
    "one_cycle": _one_cycle,
}


# ────────────────────────────────────────────────────────────────────
# PUBLIC API
# ────────────────────────────────────────────────────────────────────


def get_scheduler_fn(name: str) -> Callable:
    """Return the scheduler factory function for *name*.

    Parameters
    ----------
    name : str
        Key in ``SCHEDULER_REGISTRY``.

    Returns
    -------
    Callable
        ``factory(config, optimizer) -> schedule_or_callback``

    Raises
    ------
    ValueError
        If *name* is not registered.
    """
    if name not in SCHEDULER_REGISTRY:
        raise ValueError(f"Unknown scheduler: {name!r}. Available: {list(SCHEDULER_REGISTRY.keys())}")
    return SCHEDULER_REGISTRY[name]


def build_scheduler(config: SchedulerConfig, optimizer=None):
    """Build a learning-rate schedule (or callback) from *config*.

    Parameters
    ----------
    config : SchedulerConfig
        Scheduler parameters.
    optimizer : tf.keras.optimizers.Optimizer, optional
        Some TF schedules need the optimizer; provided for future use.

    Returns
    -------
    tf.keras.optimizers.schedules.LearningRateSchedule or tf.keras.callbacks.ReduceLROnPlateau
        A callable schedule (most schedulers) or a Keras callback (plateau).

    Raises
    ------
    ValueError
        If *config* fails validation.
    """
    errors = config.validate()
    if errors:
        raise ValueError(f"Invalid scheduler config: {errors}")

    factory = get_scheduler_fn(config.name)
    logger.info(
        "Building scheduler %s (initial_lr=%.2e, min_lr=%.2e, total_epochs=%d)",
        config.name,
        config.initial_lr,
        config.min_lr,
        config.total_epochs,
    )
    return factory(config, optimizer)


def create_warmup_schedule(
    initial_lr: float = 1e-4,
    min_lr: float = 1e-6,
    warmup_epochs: int = 5,
    total_epochs: int = 100,
    steps_per_epoch: int = 50,
) -> WarmupCosineDecay:
    """Convenience function that returns a ``WarmupCosineDecay`` schedule.

    Parameters
    ----------
    initial_lr : float
        Peak learning rate after warmup.
    min_lr : float
        Final learning rate.
    warmup_epochs : int
        Epochs for the linear warmup ramp.
    total_epochs : int
        Total training epochs.
    steps_per_epoch : int
        Steps per epoch (e.g. dataset_size // batch_size).

    Returns
    -------
    WarmupCosineDecay
        A TF-compatible learning-rate schedule.
    """
    total_steps = total_epochs * steps_per_epoch
    warmup_steps = warmup_epochs * steps_per_epoch
    return WarmupCosineDecay(
        initial_lr=initial_lr,
        min_lr=min_lr,
        warmup_steps=warmup_steps,
        total_steps=total_steps,
    )


def list_schedulers() -> list[str]:
    """Return the names of all registered schedulers."""
    return sorted(SCHEDULER_REGISTRY.keys())
