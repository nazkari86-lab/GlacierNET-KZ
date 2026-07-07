"""
Расширенный набор функций потерь для семантической сегментации ледников.

Включает:
- BCE, Dice, Focal, Tversky, Lovász-softmax, Combined losses
- Boundary-aware losses
- Class-weighted variants
- Online hard example mining
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

import numpy as np

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# DATA CLASS
# ----------------------------------------------------------------------


@dataclass
class LossConfig:
    """Конфигурация функции потерь."""

    name: str = "combined"  # bce, dice, focal, tversky, lovasz, combined, boundary
    alpha: float = 0.25  # Focal alpha
    gamma: float = 2.0  # Focal gamma
    smooth: float = 1.0  # Dice smooth
    tversky_alpha: float = 0.7  # Tversky FP weight
    tversky_beta: float = 0.3  # Tversky FN weight
    bce_weight: float = 0.5  # Weight of BCE in combined loss
    dice_weight: float = 0.5  # Weight of Dice in combined loss
    class_weights: list[float] | None = None
    ohem_threshold: float = 0.7  # Online Hard Example Mining threshold

    def validate(self) -> list[str]:
        errors = []
        valid_names = {"bce", "dice", "focal", "tversky", "lovasz", "combined", "boundary"}
        if self.name not in valid_names:
            errors.append(f"Unknown loss: {self.name}. Valid: {valid_names}")
        if self.alpha < 0 or self.alpha > 1:
            errors.append(f"alpha={self.alpha} must be in [0, 1]")
        if self.gamma < 0:
            errors.append(f"gamma={self.gamma} must be >= 0")
        return errors


# ----------------------------------------------------------------------
# BINARY CROSS-ENTROPY
# ----------------------------------------------------------------------


def bce_loss(y_true, y_pred, smooth: float = 0.0):
    """Binary Cross-Entropy Loss with optional label smoothing."""
    import tensorflow as tf

    y_true = tf.cast(y_true, tf.float32)
    if smooth > 0:
        y_true = y_true * (1 - smooth) + 0.5 * smooth
    y_pred = tf.clip_by_value(y_pred, 1e-7, 1 - 1e-7)
    bce = -(y_true * tf.math.log(y_pred) + (1 - y_true) * tf.math.log(1 - y_pred))
    return tf.reduce_mean(bce)


def weighted_bce_loss(y_true, y_pred, class_weights=None, smooth: float = 0.0):
    """Weighted Binary Cross-Entropy Loss with optional label smoothing."""
    import tensorflow as tf

    y_true = tf.cast(y_true, tf.float32)
    if smooth > 0:
        y_true = y_true * (1 - smooth) + 0.5 * smooth
    y_pred = tf.clip_by_value(y_pred, 1e-7, 1 - 1e-7)

    bce = -(y_true * tf.math.log(y_pred) + (1 - y_true) * tf.math.log(1 - y_pred))

    if class_weights is not None:
        w = tf.constant(class_weights, dtype=tf.float32)
        weight_map = y_true * w[1] + (1 - y_true) * w[0]
        bce = bce * weight_map

    return tf.reduce_mean(bce)


# ----------------------------------------------------------------------
# DICE LOSS
# ----------------------------------------------------------------------


def dice_loss(y_true, y_pred, smooth: float = 1.0):
    """Dice Loss: 1 - Dice Coefficient."""
    import tensorflow as tf

    y_true_f = tf.keras.backend.flatten(tf.cast(y_true, tf.float32))
    y_pred_f = tf.keras.backend.flatten(y_pred)
    intersection = tf.keras.backend.sum(y_true_f * y_pred_f)
    return 1.0 - (2.0 * intersection + smooth) / (
        tf.keras.backend.sum(y_true_f) + tf.keras.backend.sum(y_pred_f) + smooth
    )


def dice_coefficient(y_true, y_pred, smooth: float = 1.0):
    """Dice Coefficient (для метрики)."""
    import tensorflow as tf

    y_true_f = tf.keras.backend.flatten(tf.cast(y_true, tf.float32))
    y_pred_f = tf.keras.backend.flatten(y_pred)
    intersection = tf.keras.backend.sum(y_true_f * y_pred_f)
    return (2.0 * intersection + smooth) / (tf.keras.backend.sum(y_true_f) + tf.keras.backend.sum(y_pred_f) + smooth)


# ----------------------------------------------------------------------
# FOCAL LOSS
# ----------------------------------------------------------------------


def focal_loss(y_true, y_pred, alpha: float = 0.25, gamma: float = 2.0):
    """Focal Loss: фокус на сложных примерах, подавляет easy negatives.

    Lin et al., "Focal Loss for Dense Object Detection", 2017.
    """
    import tensorflow as tf

    y_true = tf.cast(y_true, tf.float32)
    y_pred = tf.clip_by_value(y_pred, 1e-7, 1 - 1e-7)
    bce = -y_true * tf.math.log(y_pred) - (1 - y_true) * tf.math.log(1 - y_pred)
    p_t = y_true * y_pred + (1 - y_true) * (1 - y_pred)
    alpha_t = y_true * alpha + (1 - y_true) * (1 - alpha)
    focal_weight = alpha_t * (1 - p_t) ** gamma
    return tf.reduce_mean(focal_weight * bce)


# ----------------------------------------------------------------------
# TVERSKY LOSS
# ----------------------------------------------------------------------


def tversky_loss(y_true, y_pred, alpha: float = 0.7, beta: float = 0.3, smooth: float = 1.0):
    """Tversky Loss: взвешивает FP и FN differently.

    Tversky et al., "Alpha-Divergence GAN", 2017.
    alpha > 0.5 penalizes FN more (good for glacier under-segmentation).
    """
    import tensorflow as tf

    y_true_f = tf.keras.backend.flatten(tf.cast(y_true, tf.float32))
    y_pred_f = tf.keras.backend.flatten(y_pred)
    true_pos = tf.keras.backend.sum(y_true_f * y_pred_f)
    false_neg = tf.keras.backend.sum(y_true_f * (1 - y_pred_f))
    false_pos = tf.keras.backend.sum((1 - y_true_f) * y_pred_f)
    tversky_index = (true_pos + smooth) / (true_pos + alpha * false_pos + beta * false_neg + smooth)
    return 1.0 - tversky_index


def focal_tversky_loss(y_true, y_pred, alpha: float = 0.7, beta: float = 0.3, gamma: float = 0.75, smooth: float = 1.0):
    """Focal Tversky Loss: Tversky + focal modulator.

    Abraham & Khan, "A Novel Focal Tversky Loss Function with Improved
    Attention U-Net for Lesion Segmentation", 2019.
    """
    import tensorflow as tf

    tv = tversky_loss(y_true, y_pred, alpha, beta, smooth)
    return tf.pow(tv, gamma)


# ----------------------------------------------------------------------
# LOVÁSZ-SOFTMAX LOSS
# ----------------------------------------------------------------------


def lovasz_hinge_loss(y_true, y_pred):
    """Lovász-softmax loss для бинарной сегментации.

    Placeholder — requires tensorflow-addons or custom implementation.
    Falls back to dice loss if not available.
    """
    try:
        import tensorflow_addons as tfa

        return tfa.losses.lovasz_hinge(y_true, y_pred)
    except ImportError:
        logger.warning("tensorflow-addons not available, falling back to dice_loss")
        return dice_loss(y_true, y_pred)


# ----------------------------------------------------------------------
# BOUNDARY-AWARE LOSS
# ----------------------------------------------------------------------


def boundary_loss(y_true, y_pred, smooth: float = 1.0):
    """Boundary Loss: фокусируется на границах объектов.

    Uses distance transform of ground truth as target.
    """
    import tensorflow as tf

    try:
        from scipy.ndimage import distance_transform_edt

        y_true_np = y_true.numpy() if hasattr(y_true, "numpy") else np.array(y_true)
        if y_true_np.ndim == 4:
            y_true_np = y_true_np[..., 0]

        dist_maps = []
        for mask in y_true_np:
            if mask.max() == 0:
                dist_maps.append(np.zeros_like(mask))
                continue
            pos_dist = distance_transform_edt(mask)
            neg_dist = distance_transform_edt(1 - mask)
            dist = pos_dist - neg_dist
            dist = dist / (np.abs(dist).max() + 1e-8)
            dist_maps.append(dist)

        dist_target = tf.constant(np.stack(dist_maps, axis=0), dtype=tf.float32)
        if y_pred.ndim == 4:
            y_pred = y_pred[..., 0]

        return tf.reduce_mean(tf.keras.backend.binary_crossentropy(dist_target, y_pred))
    except ImportError:
        return dice_loss(y_true, y_pred)


def boundary_dice_loss(y_true, y_pred, boundary_weight: float = 0.5, smooth: float = 1.0):
    """Комбинация Dice + Boundary Loss."""
    dl = dice_loss(y_true, y_pred, smooth)
    bl = boundary_loss(y_true, y_pred, smooth)
    return boundary_weight * bl + (1 - boundary_weight) * dl


# ----------------------------------------------------------------------
# COMBINED LOSSES
# ----------------------------------------------------------------------


def combined_bce_dice_loss(
    y_true,
    y_pred,
    bce_weight: float = 0.5,
    dice_weight: float = 0.5,
    dice_smooth: float = 1.0,
    bce_label_smooth: float = 0.0,
):
    """BCE + Dice Loss.

    Parameters
    ----------
    dice_smooth : float
        Numerical stabilizer for Dice coefficient (default 1.0 is correct).
    bce_label_smooth : float
        Label smoothing for BCE only (default 0.0 = no smoothing).
        Do NOT pass dice_smooth here — it would collapse BCE targets to 0.5
        and kill all BCE gradient.
    """
    bce = bce_loss(y_true, y_pred, bce_label_smooth)
    dice = dice_loss(y_true, y_pred, dice_smooth)
    return bce_weight * bce + dice_weight * dice


def combined_focal_dice_loss(y_true, y_pred, alpha: float = 0.25, gamma: float = 2.0, smooth: float = 1.0):
    """Focal + Dice Loss."""
    fl = focal_loss(y_true, y_pred, alpha, gamma)
    dl = dice_loss(y_true, y_pred, smooth)
    return fl + dl


# ----------------------------------------------------------------------
# ONLINE HARD EXAMPLE MINING (OHEM)
# ----------------------------------------------------------------------


def ohem_loss(
    y_true,
    y_pred,
    base_loss_fn: Callable | None = None,
    threshold: float = 0.7,
    min_kept: int = 100,
):
    """Online Hard Example Mining: фокусируется на hardest examples."""
    import tensorflow as tf

    if base_loss_fn is None:
        base_loss_fn = focal_loss

    per_pixel_loss = tf.keras.losses.binary_crossentropy(y_true, y_pred)

    if per_pixel_loss.ndim > 1:
        flat_loss = tf.reshape(per_pixel_loss, [-1])
    else:
        flat_loss = per_pixel_loss

    n_pixels = tf.size(flat_loss)
    n_keep = tf.maximum(tf.cast(tf.cast(n_pixels, tf.float32) * (1 - threshold), tf.int32), min_kept)

    _, top_indices = tf.math.top_k(flat_loss, k=n_keep)
    hard_loss = tf.gather(flat_loss, top_indices)

    return tf.reduce_mean(hard_loss)


# ----------------------------------------------------------------------
# LOSS FUNCTION REGISTRY
# ----------------------------------------------------------------------


LOSS_REGISTRY: dict[str, Callable] = {
    "bce": bce_loss,
    "dice": dice_loss,
    "focal": focal_loss,
    "tversky": tversky_loss,
    "focal_tversky": focal_tversky_loss,
    "lovasz": lovasz_hinge_loss,
    "boundary": boundary_loss,
    "combined_bce_dice": combined_bce_dice_loss,
    "combined_focal_dice": combined_focal_dice_loss,
    "boundary_dice": boundary_dice_loss,
}


def get_loss_fn(name: str, **kwargs) -> Callable:
    """Возвращает функцию потерь по имени.

    Parameters
    ----------
    name : str
        Имя функции потерь.
    **kwargs
        Дополнительные параметры.

    Returns
    -------
    Callable
        Функция потерь.
    """
    if name not in LOSS_REGISTRY:
        raise ValueError(f"Unknown loss: {name}. Available: {list(LOSS_REGISTRY.keys())}")

    loss_fn = LOSS_REGISTRY[name]

    if kwargs:

        def wrapped(y_true, y_pred):
            return loss_fn(y_true, y_pred, **kwargs)

        return wrapped

    return loss_fn


def build_loss(config: LossConfig) -> Callable:
    """Строит функцию потерь по конфигурации."""
    errors = config.validate()
    if errors:
        raise ValueError(f"Invalid loss config: {errors}")

    kwargs = {}
    if config.name == "focal":
        kwargs = {"alpha": config.alpha, "gamma": config.gamma}
    elif config.name == "tversky":
        kwargs = {"alpha": config.tversky_alpha, "beta": config.tversky_beta}
    elif config.name == "combined_bce_dice":
        kwargs = {"bce_weight": config.bce_weight, "dice_weight": config.dice_weight}
    elif config.name == "combined_focal_dice":
        kwargs = {"alpha": config.alpha, "gamma": config.gamma}
    elif config.name == "boundary_dice":
        kwargs = {"boundary_weight": config.bce_weight}

    return get_loss_fn(config.name, **kwargs)


def list_losses() -> list[str]:
    """Возвращает список доступных функций потерь."""
    return list(LOSS_REGISTRY.keys())


# ----------------------------------------------------------------------
# CUSTOM TF LOSSES FOR COMPILE
# ----------------------------------------------------------------------


def make_combined_loss(alpha: float = 0.25, gamma: float = 2.0, smooth: float = 1.0):
    """Фабрика: создаёт combined focal + dice loss с заданными параметрами."""

    def loss(y_true, y_pred):
        return combined_focal_dice_loss(y_true, y_pred, alpha, gamma, smooth)

    return loss


def make_dice_loss(smooth: float = 1.0):
    """Фабрика: создаёт dice loss с заданным smooth."""

    def loss(y_true, y_pred):
        return dice_loss(y_true, y_pred, smooth)

    return loss


def get_custom_objects() -> dict[str, Callable]:
    """Возвращает словарь custom_objects для tf.keras.models.load_model."""
    return {
        "bce_loss": bce_loss,
        "dice_loss": dice_loss,
        "dice_coefficient": dice_coefficient,
        "focal_loss": focal_loss,
        "tversky_loss": tversky_loss,
        "focal_tversky_loss": focal_tversky_loss,
        "combined_bce_dice_loss": combined_bce_dice_loss,
        "combined_focal_dice_loss": combined_focal_dice_loss,
        "boundary_loss": boundary_loss,
        "boundary_dice_loss": boundary_dice_loss,
        "ohem_loss": ohem_loss,
    }
