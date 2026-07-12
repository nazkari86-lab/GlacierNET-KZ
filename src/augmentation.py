"""
Расширенная аугментация данных для сегментации ледников.

Поддерживает:
- Геометрические преобразования (flip, rotate, crop, elastic)
- Фотометрические преобразования (яркость, контраст, gamma, шум)
- Специализированные для спутниковых снимков (spectral augmentation)
- MixUp, CutMix, Mosaic
- Stain normalization для мультиспектральных данных
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

from . import config

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# DATA CLASSES
# ----------------------------------------------------------------------


@dataclass
class AugmentationConfig:
    """Полная конфигурация аугментации."""

    # Вероятности (0..1)
    p_flip_lr: float = 0.5
    p_flip_ud: float = 0.5
    p_rotate90: float = 0.5
    p_rotate_random: float = 0.0
    p_brightness: float = 0.5
    p_contrast: float = 0.5
    p_gamma: float = 0.3
    p_gaussian_noise: float = 0.15
    p_gaussian_blur: float = 0.1
    p_elastic: float = 0.0
    p_mixup: float = 0.0
    p_cutmix: float = 0.0
    p_channel_dropout: float = 0.0
    p_spectral_jitter: float = 0.0

    # Параметры
    brightness_range: tuple[float, float] = (0.8, 1.2)
    brightness_offset: tuple[float, float] = (-0.05, 0.05)
    contrast_range: tuple[float, float] = (0.8, 1.2)
    gamma_range: tuple[float, float] = (0.8, 1.2)
    noise_std: float = 0.01
    blur_sigma_range: tuple[float, float] = (0.3, 0.8)
    elastic_alpha: float = 1200.0
    elastic_sigma: float = 40.0

    # MixUp/CutMix
    mixup_alpha: float = 0.2
    cutmix_alpha: float = 1.0

    # Channel dropout
    channel_dropout_prob: float = 0.1
    min_channels: int = 3

    # Spectral jitter
    spectral_jitter_std: float = 0.02

    # Ограничения
    preserve_glacier_ratio: bool = True
    min_glacier_fraction: float = 0.01

    def validate(self) -> list[str]:
        errors = []
        prob_fields = [
            "p_flip_lr",
            "p_flip_ud",
            "p_rotate90",
            "p_rotate_random",
            "p_brightness",
            "p_contrast",
            "p_gamma",
            "p_gaussian_noise",
            "p_gaussian_blur",
            "p_elastic",
            "p_mixup",
            "p_cutmix",
            "p_channel_dropout",
            "p_spectral_jitter",
        ]
        for f in prob_fields:
            val = getattr(self, f)
            if val < 0 or val > 1:
                errors.append(f"{f}={val} must be in [0, 1]")
        if self.noise_std < 0:
            errors.append(f"noise_std={self.noise_std} must be >= 0")
        return errors


# ----------------------------------------------------------------------
# GEOMETRIC AUGMENTATIONS
# ----------------------------------------------------------------------


def flip_lr(image: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Отражение по горизонтали."""
    return np.fliplr(image), np.fliplr(mask)


def flip_ud(image: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Отражение по вертикали."""
    return np.flipud(image), np.flipud(mask)


def rotate90(image: np.ndarray, mask: np.ndarray, k: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """Поворот на 90*k градусов."""
    return np.rot90(image, k), np.rot90(mask, k)


def random_rotate(
    image: np.ndarray,
    mask: np.ndarray,
    rng: np.random.Generator,
    angle_range: tuple[float, float] = (-15, 15),
) -> tuple[np.ndarray, np.ndarray]:
    """Случайный поворот на угол из angle_range."""
    try:
        import cv2

        angle = rng.uniform(*angle_range)
        h, w = image.shape[:2]
        center = (w / 2, h / 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)

        rotated_img = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        rotated_mask = cv2.warpAffine(
            mask.astype(np.float32), M, (w, h), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_REFLECT
        )
        return rotated_img, rotated_mask.astype(mask.dtype)
    except ImportError:
        k = rng.integers(0, 4)
        return rotate90(image, mask, int(k))


def random_crop(
    image: np.ndarray,
    mask: np.ndarray,
    rng: np.random.Generator,
    crop_ratio: float = 0.8,
) -> tuple[np.ndarray, np.ndarray]:
    """Случайный crop с возвратом к исходному размеру (resize)."""
    try:
        import cv2

        h, w = image.shape[:2]
        crop_h, crop_w = int(h * crop_ratio), int(w * crop_ratio)

        y_start = rng.integers(0, h - crop_h + 1)
        x_start = rng.integers(0, w - crop_w + 1)

        img_crop = image[y_start : y_start + crop_h, x_start : x_start + crop_w]
        mask_crop = mask[y_start : y_start + crop_h, x_start : x_start + crop_w]

        img_resized = cv2.resize(img_crop, (w, h), interpolation=cv2.INTER_LINEAR)
        mask_resized = cv2.resize(mask_crop, (w, h), interpolation=cv2.INTER_NEAREST)

        return img_resized, mask_resized.astype(mask.dtype)
    except ImportError:
        return image, mask


# ----------------------------------------------------------------------
# ELASTIC DEFORMATION
# ----------------------------------------------------------------------


def elastic_deformation(
    image: np.ndarray,
    mask: np.ndarray,
    alpha: float = 1200.0,
    sigma: float = 40.0,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Эластичная деформация (Simard et al., 2003).

    Генерирует случайное поле смещений и применяет его к image и mask.
    """
    if rng is None:
        rng = np.random.default_rng()

    H, W = image.shape[:2]

    dx = rng.normal(0, sigma, (H, W)).astype(np.float32)
    dy = rng.normal(0, sigma, (H, W)).astype(np.float32)

    try:
        from scipy.ndimage import gaussian_filter

        dx = gaussian_filter(dx, sigma)
        dy = gaussian_filter(dy, sigma)
    except ImportError:
        pass

    dx *= alpha / (H * W)
    dy *= alpha / (H * W)

    x, y = np.meshgrid(np.arange(W), np.arange(H))
    x_new = np.clip(x + dx, 0, W - 1).astype(np.float32)
    y_new = np.clip(y + dy, 0, H - 1).astype(np.float32)

    try:
        import cv2

        map_x = x_new
        map_y = y_new

        deformed_img = cv2.remap(image, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        deformed_mask = cv2.remap(
            mask.astype(np.float32), map_x, map_y, interpolation=cv2.INTER_NEAREST, borderMode=cv2.BORDER_REFLECT
        )
        return deformed_img, deformed_mask.astype(mask.dtype)
    except ImportError:
        from scipy.ndimage import map_coordinates

        channels = image.shape[-1] if image.ndim == 3 else 1
        coords = [y_new, x_new]
        deformed_channels = []
        for c in range(channels):
            ch = image[..., c] if image.ndim == 3 else image
            deformed_ch = map_coordinates(ch, coords, order=1, mode="reflect")
            deformed_channels.append(deformed_ch)

        if image.ndim == 3:
            deformed_img = np.stack(deformed_channels, axis=-1)
        else:
            deformed_img = deformed_channels[0]

        deformed_mask = map_coordinates(mask.astype(np.float32), coords, order=0, mode="reflect")
        return deformed_img, deformed_mask.astype(mask.dtype)


# ----------------------------------------------------------------------
# PHOTOMETRIC AUGMENTATIONS
# ----------------------------------------------------------------------


def adjust_brightness(
    image: np.ndarray,
    rng: np.random.Generator,
    alpha_range: tuple[float, float] = (0.8, 1.2),
    beta_range: tuple[float, float] = (-0.05, 0.05),
) -> np.ndarray:
    """Случайная коррекция яркости: image = image * alpha + beta."""
    alpha = rng.uniform(*alpha_range)
    beta = rng.uniform(*beta_range)
    return np.clip(image * alpha + beta, 0, 1).astype(np.float32)


def adjust_contrast(
    image: np.ndarray,
    rng: np.random.Generator,
    contrast_range: tuple[float, float] = (0.8, 1.2),
) -> np.ndarray:
    """Случайная коррекция контраста."""
    factor = rng.uniform(*contrast_range)
    mean = image.mean()
    return np.clip((image - mean) * factor + mean, 0, 1).astype(np.float32)


def adjust_gamma(
    image: np.ndarray,
    rng: np.random.Generator,
    gamma_range: tuple[float, float] = (0.8, 1.2),
) -> np.ndarray:
    """Gamma-коррекция: image = image ^ gamma."""
    gamma = rng.uniform(*gamma_range)
    return np.power(np.clip(image, 0, 1), gamma).astype(np.float32)


def add_gaussian_noise(image: np.ndarray, rng: np.random.Generator, std: float = 0.01) -> np.ndarray:
    """Добавляет гауссов шум."""
    noise = rng.normal(0, std, image.shape).astype(np.float32)
    return np.clip(image + noise, 0, 1).astype(np.float32)


def gaussian_blur(
    image: np.ndarray,
    rng: np.random.Generator,
    sigma_range: tuple[float, float] = (0.3, 0.8),
) -> np.ndarray:
    """Гауссово размытие."""
    try:
        from scipy.ndimage import gaussian_filter

        sigma = rng.uniform(*sigma_range)
        blurred = np.zeros_like(image)
        for c in range(image.shape[-1]):
            blurred[..., c] = gaussian_filter(image[..., c], sigma=sigma)
        return blurred.astype(np.float32)
    except ImportError:
        return image


def channel_dropout(
    image: np.ndarray,
    rng: np.random.Generator,
    drop_prob: float = 0.1,
    min_channels: int = 3,
) -> np.ndarray:
    """Dropout случайных спектральных каналов."""
    n_channels = image.shape[-1]
    if n_channels <= min_channels:
        return image

    result = image.copy()
    for c in range(n_channels):
        if rng.random() < drop_prob:
            result[..., c] = 0
    return result


def spectral_jitter(image: np.ndarray, rng: np.random.Generator, std: float = 0.02) -> np.ndarray:
    """Спектральный джиттер: небольшие смещения значений каналов."""
    n_channels = image.shape[-1]
    shifts = rng.normal(0, std, n_channels).astype(np.float32)
    result = image + shifts
    return np.clip(result, 0, 1).astype(np.float32)


# ----------------------------------------------------------------------
# MIXUP & CUTMIX
# ----------------------------------------------------------------------


def mixup(
    image1: np.ndarray,
    mask1: np.ndarray,
    image2: np.ndarray,
    mask2: np.ndarray,
    alpha: float = 0.2,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """MixUp: взвешенное суммирование двух примеров."""
    if rng is None:
        rng = np.random.default_rng()

    lam = rng.beta(alpha, alpha)
    mixed_image = lam * image1 + (1 - lam) * image2
    mixed_mask = (lam * mask1 + (1 - lam) * mask2).astype(mask1.dtype)
    return mixed_image.astype(np.float32), mixed_mask


def cutmix(
    image1: np.ndarray,
    mask1: np.ndarray,
    image2: np.ndarray,
    mask2: np.ndarray,
    alpha: float = 1.0,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """CutMix: вырезает прямоугольник из одного примера и вставляет в другой."""
    if rng is None:
        rng = np.random.default_rng()

    H, W = image1.shape[:2]
    lam = rng.beta(alpha, alpha)

    cut_ratio = np.sqrt(1 - lam)
    cut_h = int(H * cut_ratio)
    cut_w = int(W * cut_ratio)

    cy = rng.integers(0, H)
    cx = rng.integers(0, W)

    y1 = max(cy - cut_h // 2, 0)
    y2 = min(cy + cut_h // 2, H)
    x1 = max(cx - cut_w // 2, 0)
    x2 = min(cx + cut_w // 2, W)

    mixed_image = image1.copy()
    mixed_mask = mask1.copy()

    mixed_image[y1:y2, x1:x2] = image2[y1:y2, x1:x2]
    mixed_mask[y1:y2, x1:x2] = mask2[y1:y2, x1:x2]

    1 - (y2 - y1) * (x2 - x1) / (H * W)
    return mixed_image.astype(np.float32), mixed_mask.astype(mask1.dtype)


# ----------------------------------------------------------------------
# FULL AUGMENTATION PIPELINE
# ----------------------------------------------------------------------


def augment_patch(
    image: np.ndarray,
    mask: np.ndarray,
    rng: np.random.Generator | None = None,
    cfg: AugmentationConfig | None = None,
    photometric_channels: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Полный пайплайн аугментации для одного патча.

    Применяет все преобразования согласно конфигурации.

    Parameters
    ----------
    image : np.ndarray
        Патч снимка (H, W, C).
    mask : np.ndarray
        Маска (H, W).
    rng : np.random.Generator
        Генератор случайных чисел.
    cfg : AugmentationConfig, optional
        Конфигурация аугментации.
    photometric_channels : int, optional
        Число первых каналов, к которым применяются фотометрические
        преобразования. Остальные каналы (например, индексы и terrain
        features) сохраняют физический диапазон значений.

    Returns
    -------
    tuple of (augmented_image, augmented_mask)
    """
    if rng is None:
        rng = np.random.default_rng()
    if cfg is None:
        cfg = AugmentationConfig()

    img, msk = image.copy(), mask.copy()
    n_photometric = image.shape[-1] if photometric_channels is None else photometric_channels
    if not 1 <= n_photometric <= image.shape[-1]:
        raise ValueError(f"photometric_channels must be in [1, {image.shape[-1]}], got {n_photometric}")

    def transform_photometric(transform, *args):
        result = img.copy()
        result[..., :n_photometric] = transform(result[..., :n_photometric], *args)
        return result

    # Геометрические
    if rng.random() < cfg.p_flip_lr:
        img, msk = flip_lr(img, msk)

    if rng.random() < cfg.p_flip_ud:
        img, msk = flip_ud(img, msk)

    if rng.random() < cfg.p_rotate90:
        k = int(rng.integers(0, 4))
        img, msk = rotate90(img, msk, k)

    if rng.random() < cfg.p_rotate_random:
        img, msk = random_rotate(img, msk, rng)

    if rng.random() < cfg.p_elastic:
        img, msk = elastic_deformation(img, msk, cfg.elastic_alpha, cfg.elastic_sigma, rng)

    # Фотометрические
    if rng.random() < cfg.p_brightness:
        img = transform_photometric(adjust_brightness, rng, cfg.brightness_range, cfg.brightness_offset)

    if rng.random() < cfg.p_contrast:
        img = transform_photometric(adjust_contrast, rng, cfg.contrast_range)

    if rng.random() < cfg.p_gamma:
        img = transform_photometric(adjust_gamma, rng, cfg.gamma_range)

    if rng.random() < cfg.p_gaussian_noise:
        img = transform_photometric(add_gaussian_noise, rng, cfg.noise_std)

    if rng.random() < cfg.p_gaussian_blur:
        img = transform_photometric(gaussian_blur, rng, cfg.blur_sigma_range)

    if rng.random() < cfg.p_channel_dropout:
        img = transform_photometric(channel_dropout, rng, cfg.channel_dropout_prob, cfg.min_channels)

    if rng.random() < cfg.p_spectral_jitter:
        img = transform_photometric(spectral_jitter, rng, cfg.spectral_jitter_std)

    return img, msk


# ----------------------------------------------------------------------
# BATCH AUGMENTATION
# ----------------------------------------------------------------------


def augment_batch(
    images: np.ndarray,
    masks: np.ndarray,
    rng: np.random.Generator | None = None,
    cfg: AugmentationConfig | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Аугментация батча патчей.

    Parameters
    ----------
    images : np.ndarray
        Батч снимков (N, H, W, C).
    masks : np.ndarray
        Батч масок (N, H, W).

    Returns
    -------
    tuple of (augmented_images, augmented_masks)
    """
    if rng is None:
        rng = np.random.default_rng()
    if cfg is None:
        cfg = AugmentationConfig()

    N = images.shape[0]
    aug_images = np.zeros_like(images, dtype=np.float32)
    aug_masks = np.zeros_like(masks, dtype=masks.dtype)

    for i in range(N):
        img, msk = augment_patch(images[i], masks[i], rng, cfg)
        aug_images[i] = img
        aug_masks[i] = msk

    return aug_images, aug_masks


# ----------------------------------------------------------------------
# AUGMENTATION STATISTICS
# ----------------------------------------------------------------------


def compute_augmentation_statistics(
    images: np.ndarray,
    masks: np.ndarray,
    n_augmentations: int = 100,
    cfg: AugmentationConfig | None = None,
) -> dict[str, Any]:
    """Вычисляет статистику после аугментации (для визуализации/отчёта)."""
    rng = np.random.default_rng(config.RANDOM_SEED)
    if cfg is None:
        cfg = AugmentationConfig()

    original_stats = _compute_batch_stats(images, masks)

    aug_images_list = []
    aug_masks_list = []
    for _ in range(n_augmentations):
        idx = rng.integers(0, len(images))
        img, msk = augment_patch(images[idx], masks[idx], rng, cfg)
        aug_images_list.append(img)
        aug_masks_list.append(msk)

    aug_images = np.array(aug_images_list)
    aug_masks = np.array(aug_masks_list)
    augmented_stats = _compute_batch_stats(aug_images, aug_masks)

    return {
        "original": original_stats,
        "augmented": augmented_stats,
        "n_augmentations": n_augmentations,
    }


def _compute_batch_stats(images: np.ndarray, masks: np.ndarray) -> dict[str, Any]:
    """Вычисляет базовую статистику по батчу."""
    return {
        "n_samples": len(images),
        "image_mean": float(images.mean()),
        "image_std": float(images.std()),
        "image_min": float(images.min()),
        "image_max": float(images.max()),
        "mask_glacier_fraction": float(masks.mean()),
        "mask_shape": list(masks.shape),
        "image_shape": list(images.shape),
    }


# ----------------------------------------------------------------------
# PRESET CONFIGURATIONS
# ----------------------------------------------------------------------


AUGMENTATION_PRESETS: dict[str, AugmentationConfig] = {
    "light": AugmentationConfig(
        p_flip_lr=0.5,
        p_flip_ud=0.5,
        p_rotate90=0.5,
        p_brightness=0.3,
        p_contrast=0.3,
        p_gamma=0.2,
        p_gaussian_noise=0.1,
        p_gaussian_blur=0.05,
    ),
    "medium": AugmentationConfig(
        p_flip_lr=0.5,
        p_flip_ud=0.5,
        p_rotate90=0.5,
        p_brightness=0.5,
        p_contrast=0.5,
        p_gamma=0.3,
        p_gaussian_noise=0.15,
        p_gaussian_blur=0.1,
        p_channel_dropout=0.1,
        p_spectral_jitter=0.1,
    ),
    "heavy": AugmentationConfig(
        p_flip_lr=0.5,
        p_flip_ud=0.5,
        p_rotate90=0.5,
        p_rotate_random=0.3,
        p_elastic=0.2,
        p_brightness=0.6,
        p_contrast=0.6,
        p_gamma=0.4,
        p_gaussian_noise=0.2,
        p_gaussian_blur=0.15,
        p_channel_dropout=0.15,
        p_spectral_jitter=0.2,
    ),
    "satellite": AugmentationConfig(
        p_flip_lr=0.5,
        p_flip_ud=0.5,
        p_rotate90=0.5,
        p_brightness=0.4,
        p_contrast=0.4,
        p_gamma=0.3,
        p_gaussian_noise=0.1,
        p_gaussian_blur=0.05,
        p_channel_dropout=0.1,
        p_spectral_jitter=0.15,
    ),
    "minimal": AugmentationConfig(
        p_flip_lr=0.5,
        p_flip_ud=0.5,
        p_rotate90=0.5,
        p_brightness=0.2,
        p_contrast=0.2,
    ),
}


def get_preset(name: str) -> AugmentationConfig:
    """Возвращает предустановленную конфигурацию."""
    if name not in AUGMENTATION_PRESETS:
        raise ValueError(f"Unknown preset: {name}. Available: {list(AUGMENTATION_PRESETS.keys())}")
    return AUGMENTATION_PRESETS[name]
