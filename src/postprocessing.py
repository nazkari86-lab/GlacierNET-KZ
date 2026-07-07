"""
Пост-обработка масок сегментации: морфологические операции,
связные компоненты, CRF-сглаживание, фильтрация шума,
уточнение границ ледников.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# DATA CLASSES
# ----------------------------------------------------------------------


@dataclass
class PostprocessConfig:
    """Конфигурация пост-обработки."""

    # Морфология
    morphological_op: Literal["none", "opening", "closing", "open_close", "close_open"] = "open_close"
    morph_kernel_size: int = 3
    morph_iterations: int = 1

    # Связные компоненты
    min_component_area: int = 50  # мин. площадь компонента в пикселях
    remove_small_components: bool = True

    # CRF
    use_crf: bool = False
    crf_iterations: int = 10
    crf_pos_xy_std: int = 3
    crf_bi_xy_std: int = 80
    crf_bi_rgb_std: int = 13

    # Фильтрация шума
    gaussian_sigma: float = 0.5
    median_kernel: int = 3
    apply_median_filter: bool = False
    apply_gaussian_filter: bool = False

    # Границы ледников
    boundary_refinement: bool = False
    boundary_dilation_pixels: int = 2

    # Валидация
    def validate(self) -> list[str]:
        errors = []
        if self.morph_kernel_size < 1:
            errors.append(f"morph_kernel_size={self.morph_kernel_size} must be >= 1")
        if self.min_component_area < 1:
            errors.append(f"min_component_area={self.min_component_area} must be >= 1")
        if self.gaussian_sigma < 0:
            errors.append(f"gaussian_sigma={self.gaussian_sigma} must be >= 0")
        if self.median_kernel < 1:
            errors.append(f"median_kernel={self.median_kernel} must be >= 1")
        return errors


@dataclass
class PostprocessResult:
    """Результат пост-обработки."""

    mask: np.ndarray
    probability_map: np.ndarray | None = None
    n_components_before: int = 0
    n_components_after: int = 0
    removed_components: int = 0
    total_area_before: int = 0
    total_area_after: int = 0
    applied_operations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ----------------------------------------------------------------------
# MORPHOLOGICAL OPERATIONS
# ----------------------------------------------------------------------


def morphological_opening(mask: np.ndarray, kernel_size: int = 3, iterations: int = 1) -> np.ndarray:
    """Морфологическое открытие: убирает мелкий шум («соль»)."""
    try:
        import cv2

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        return cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, kernel, iterations=iterations)
    except ImportError:
        from scipy.ndimage import binary_opening

        struct = _create_structuring_element(kernel_size)
        return binary_opening(mask.astype(bool), structure=struct, iterations=iterations).astype(np.uint8)


def morphological_closing(mask: np.ndarray, kernel_size: int = 3, iterations: int = 1) -> np.ndarray:
    """Морфологическое закрытие: заполняет мелкие дыры («перец»)."""
    try:
        import cv2

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        return cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel, iterations=iterations)
    except ImportError:
        from scipy.ndimage import binary_closing

        struct = _create_structuring_element(kernel_size)
        return binary_closing(mask.astype(bool), structure=struct, iterations=iterations).astype(np.uint8)


def morphological_open_close(mask: np.ndarray, kernel_size: int = 3, iterations: int = 1) -> np.ndarray:
    """Открытие + закрытие: сначала убирает шум, потом заполняет дыры."""
    result = morphological_opening(mask, kernel_size, iterations)
    result = morphological_closing(result, kernel_size, iterations)
    return result


def morphological_close_open(mask: np.ndarray, kernel_size: int = 3, iterations: int = 1) -> np.ndarray:
    """Закрытие + открытие: сначала заполняет дыры, потом убирает шум."""
    result = morphological_closing(mask, kernel_size, iterations)
    result = morphological_opening(result, kernel_size, iterations)
    return result


def _create_structuring_element(kernel_size: int) -> np.ndarray:
    """Создаёт структурный элемент для scipy (круглый)."""
    radius = kernel_size // 2
    y, x = np.ogrid[-radius : radius + 1, -radius : radius + 1]
    struct = (x**2 + y**2) <= radius**2
    return struct.astype(int)


def apply_morphological_operation(mask: np.ndarray, cfg: PostprocessConfig) -> tuple[np.ndarray, str]:
    """Применяет морфологическую операцию согласно конфигурации."""
    ops = {
        "none": lambda m: m,
        "opening": lambda m: morphological_opening(m, cfg.morph_kernel_size, cfg.morph_iterations),
        "closing": lambda m: morphological_closing(m, cfg.morph_kernel_size, cfg.morph_iterations),
        "open_close": lambda m: morphological_open_close(m, cfg.morph_kernel_size, cfg.morph_iterations),
        "close_open": lambda m: morphological_close_open(m, cfg.morph_kernel_size, cfg.morph_iterations),
    }
    op_fn = ops.get(cfg.morphological_op)
    if op_fn is None:
        raise ValueError(f"Unknown morphological_op: {cfg.morphological_op}")
    return op_fn(mask), cfg.morphological_op


# ----------------------------------------------------------------------
# CONNECTED COMPONENTS
# ----------------------------------------------------------------------


def remove_small_components(mask: np.ndarray, min_area: int = 50) -> tuple[np.ndarray, int, int]:
    """Удаляет связные компоненты площадью < min_area пикселей.

    Returns
    -------
    tuple of (cleaned_mask, n_removed, n_total_before)
    """
    try:
        import cv2

        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
        n_before = num_labels - 1  # минус фон

        areas = stats[1:, cv2.CC_STAT_AREA]
        keep_mask = areas >= min_area
        n_removed = int((~keep_mask).sum())

        cleaned = np.zeros_like(mask)
        for label_id in range(1, num_labels):
            if keep_mask[label_id - 1]:
                cleaned[labels == label_id] = 1

        return cleaned, n_removed, n_before

    except ImportError:
        from scipy.ndimage import label

        labeled, num_features = label(mask.astype(bool))
        n_before = num_features

        cleaned = np.zeros_like(mask)
        n_removed = 0
        for i in range(1, num_features + 1):
            component = labeled == i
            area = component.sum()
            if area >= min_area:
                cleaned[component] = 1
            else:
                n_removed += 1

        return cleaned, n_removed, n_before


def get_component_stats(mask: np.ndarray) -> dict[str, Any]:
    """Возвращает статистику по связным компонентам."""
    try:
        import cv2

        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
        areas = stats[1:, cv2.CC_STAT_AREA]
        return {
            "n_components": num_labels - 1,
            "areas": areas.tolist(),
            "mean_area": float(areas.mean()) if len(areas) > 0 else 0,
            "std_area": float(areas.std()) if len(areas) > 0 else 0,
            "max_area": int(areas.max()) if len(areas) > 0 else 0,
            "min_area": int(areas.min()) if len(areas) > 0 else 0,
            "total_pixels": int(mask.sum()),
        }
    except ImportError:
        from scipy.ndimage import label

        labeled, num_features = label(mask.astype(bool))
        areas = []
        for i in range(1, num_features + 1):
            areas.append(int((labeled == i).sum()))
        areas_arr = np.array(areas) if areas else np.array([0])
        return {
            "n_components": num_features,
            "areas": areas,
            "mean_area": float(areas_arr.mean()),
            "std_area": float(areas_arr.std()),
            "max_area": int(areas_arr.max()),
            "min_area": int(areas_arr.min()),
            "total_pixels": int(mask.sum()),
        }


# ----------------------------------------------------------------------
# GAUSSIAN / MEDIAN FILTERS
# ----------------------------------------------------------------------


def apply_gaussian_filter(prob_map: np.ndarray, sigma: float = 0.5) -> np.ndarray:
    """Гауссово сглаживание вероятностной карты."""
    try:
        from scipy.ndimage import gaussian_filter

        return gaussian_filter(prob_map, sigma=sigma).astype(np.float32)
    except ImportError:
        logger.warning("scipy not available, skipping gaussian filter")
        return prob_map


def apply_median_filter(prob_map: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """Медианный фильтр вероятностной карты."""
    try:
        import cv2

        k = kernel_size if kernel_size % 2 == 1 else kernel_size + 1
        return cv2.medianBlur((prob_map * 255).astype(np.uint8), k).astype(np.float32) / 255
    except ImportError:
        try:
            from scipy.ndimage import median_filter

            return median_filter(prob_map, size=kernel_size).astype(np.float32)
        except ImportError:
            logger.warning("Neither cv2 nor scipy available, skipping median filter")
            return prob_map


# ----------------------------------------------------------------------
# BOUNDARY REFINEMENT
# ----------------------------------------------------------------------


def refine_boundaries(mask: np.ndarray, dilation_pixels: int = 2) -> np.ndarray:
    """Уточняет границы маски через дилатацию и эрозию."""
    try:
        import cv2

        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (2 * dilation_pixels + 1, 2 * dilation_pixels + 1),
        )
        dilated = cv2.dilate(mask.astype(np.uint8), kernel, iterations=1)
        eroded = cv2.erode(dilated, kernel, iterations=1)
        return eroded
    except ImportError:
        from scipy.ndimage import binary_dilation, binary_erosion

        struct = _create_structuring_element(2 * dilation_pixels + 1)
        dilated = binary_dilation(mask.astype(bool), structure=struct)
        eroded = binary_erosion(dilated, structure=struct)
        return eroded.astype(np.uint8)


# ----------------------------------------------------------------------
# CRF SMOOTHING (WRAPPER)
# ----------------------------------------------------------------------


def apply_crf_smoothing(
    prob_map: np.ndarray,
    rgb: np.ndarray | None = None,
    iterations: int = 10,
    pos_xy_std: int = 3,
    bi_xy_std: int = 80,
    bi_rgb_std: int = 13,
) -> np.ndarray:
    """CRF-сглаживание с использованием pydensecrf."""
    try:
        import pydensecrf.densecrf as dcrf

        H, W = prob_map.shape
        n_labels = 2

        unary = np.zeros((n_labels, H, W), dtype=np.float32)
        unary[1] = prob_map
        unary[0] = 1 - prob_map
        unary = -np.log(np.clip(unary, 1e-8, 1 - 1e-8))

        d = dcrf.DenseCRF2D(W, H, n_labels)
        d.setUnaryEnergy(unary)
        d.addPairwiseGaussian(sxy=pos_xy_std, compat=3)

        if rgb is not None:
            img = (rgb * 255).astype(np.uint8) if rgb.max() <= 1 else rgb.astype(np.uint8)
            d.addPairwiseBilateral(sxy=bi_xy_std, srgb=bi_rgb_std, rgbim=img, compat=10)

        Q = d.inference(iterations)
        return np.array(Q[1]).reshape(H, W).astype(np.float32)

    except ImportError:
        logger.warning("pydensecrf not available, skipping CRF smoothing")
        return prob_map


# ----------------------------------------------------------------------
# MAIN POSTPROCESSING PIPELINE
# ----------------------------------------------------------------------


def postprocess(
    prob_map: np.ndarray,
    mask: np.ndarray | None = None,
    rgb: np.ndarray | None = None,
    cfg: PostprocessConfig | None = None,
) -> PostprocessResult:
    """Полный пайплайн пост-обработки.

    Parameters
    ----------
    prob_map : np.ndarray
        Вероятностная карта (H, W) в диапазоне [0, 1].
    mask : np.ndarray, optional
        Бинарная маска. Если None — создаётся из prob_map по порогу 0.5.
    rgb : np.ndarray, optional
        RGB-снимок для CRF и визуализации.
    cfg : PostprocessConfig, optional
        Конфигурация. Если None — используются значения по умолчанию.

    Returns
    -------
    PostprocessResult
        Результат пост-обработки с метаданными.
    """
    if cfg is None:
        cfg = PostprocessConfig()

    errors = cfg.validate()
    if errors:
        raise ValueError(f"Invalid config: {errors}")

    if mask is None:
        mask = (prob_map > cfg.threshold if hasattr(cfg, "threshold") else prob_map > 0.5).astype(np.uint8)

    result = PostprocessResult(mask=mask.copy(), probability_map=prob_map.copy())

    stats_before = get_component_stats(mask)
    result.n_components_before = stats_before["n_components"]
    result.total_area_before = stats_before["total_pixels"]

    # 1. Гауссово сглаживание
    if cfg.apply_gaussian_filter and cfg.gaussian_sigma > 0:
        prob_map = apply_gaussian_filter(prob_map, cfg.gaussian_sigma)
        result.applied_operations.append(f"gaussian_filter(sigma={cfg.gaussian_sigma})")

    # 2. Медианный фильтр
    if cfg.apply_median_filter:
        prob_map = apply_median_filter(prob_map, cfg.median_kernel)
        result.applied_operations.append(f"median_filter(kernel={cfg.median_kernel})")

    # 3. Бинаризация после фильтрации
    mask = (prob_map > 0.5).astype(np.uint8)

    # 4. Морфология
    if cfg.morphological_op != "none":
        mask, op_name = apply_morphological_operation(mask, cfg)
        result.applied_operations.append(f"morph_{op_name}")

    # 5. Удаление малых компонент
    if cfg.remove_small_components:
        mask, n_removed, _ = remove_small_components(mask, cfg.min_component_area)
        result.removed_components = n_removed
        result.applied_operations.append(f"remove_small(area<{cfg.min_component_area})")

    # 6. Уточнение границ
    if cfg.boundary_refinement:
        mask = refine_boundaries(mask, cfg.boundary_dilation_pixels)
        result.applied_operations.append(f"boundary_refine(d={cfg.boundary_dilation_pixels})")

    # 7. CRF
    if cfg.use_crf:
        mask_crf = apply_crf_smoothing(
            prob_map,
            rgb,
            iterations=cfg.crf_iterations,
            pos_xy_std=cfg.crf_pos_xy_std,
            bi_xy_std=cfg.crf_bi_xy_std,
            bi_rgb_std=cfg.crf_bi_rgb_std,
        )
        mask = (mask_crf > 0.5).astype(np.uint8)
        result.applied_operations.append("crf_smoothing")

    # Статистика после
    stats_after = get_component_stats(mask)
    result.n_components_after = stats_after["n_components"]
    result.total_area_after = stats_after["total_pixels"]
    result.mask = mask
    result.probability_map = prob_map

    return result


# ----------------------------------------------------------------------
# BATCH POSTPROCESSING
# ----------------------------------------------------------------------


def postprocess_batch(
    prob_maps: list[np.ndarray],
    masks: list[np.ndarray] | None = None,
    rgb_images: list[np.ndarray] | None = None,
    cfg: PostprocessConfig | None = None,
) -> list[PostprocessResult]:
    """Пакетная пост-обработка."""
    n = len(prob_maps)
    if masks is not None and len(masks) != n:
        raise ValueError(f"Length mismatch: {n} prob_maps vs {len(masks)} masks")
    if rgb_images is not None and len(rgb_images) != n:
        raise ValueError(f"Length mismatch: {n} prob_maps vs {len(rgb_images)} rgb_images")

    results = []
    for i in range(n):
        mask = masks[i] if masks is not None else None
        rgb = rgb_images[i] if rgb_images is not None else None
        result = postprocess(prob_maps[i], mask=mask, rgb=rgb, cfg=cfg)
        results.append(result)

    return results


# ----------------------------------------------------------------------
# COMPARISON
# ----------------------------------------------------------------------


def compare_postprocessing_methods(
    prob_map: np.ndarray,
    ground_truth: np.ndarray | None = None,
    methods: list[PostprocessConfig] | None = None,
) -> dict[str, dict]:
    """Сравнивает разные методы пост-обработки.

    Parameters
    ----------
    prob_map : np.ndarray
        Вероятностная карта.
    ground_truth : np.ndarray, optional
        Истинная маска для оценки качества.
    methods : list of PostprocessConfig, optional
        Список конфигураций для сравнения.

    Returns
    -------
    dict
        Результаты для каждого метода.
    """
    if methods is None:
        methods = [
            PostprocessConfig(morphological_op="none"),
            PostprocessConfig(morphological_op="open_close"),
            PostprocessConfig(morphological_op="close_open"),
            PostprocessConfig(
                morphological_op="open_close",
                remove_small_components=True,
                min_component_area=50,
            ),
            PostprocessConfig(
                morphological_op="open_close",
                remove_small_components=True,
                min_component_area=100,
            ),
            PostprocessConfig(
                morphological_op="open_close",
                apply_gaussian_filter=True,
                gaussian_sigma=0.5,
            ),
        ]

    results = {}
    for i, method_cfg in enumerate(methods):
        res = postprocess(prob_map, cfg=method_cfg)
        label = f"method_{i}_{method_cfg.morphological_op}"
        entry: dict[str, Any] = {
            "applied_operations": res.applied_operations,
            "n_components_before": res.n_components_before,
            "n_components_after": res.n_components_after,
            "removed_components": res.removed_components,
            "total_area_after": res.total_area_after,
        }

        if ground_truth is not None:
            from .metrics import evaluate_segmentation

            metrics = evaluate_segmentation(ground_truth, res.mask)
            entry["metrics"] = metrics

        results[label] = entry

    return results
