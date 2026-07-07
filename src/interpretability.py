#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Интерпретируемость и объяснимость модели (Model Interpretability & Explainability).

Методы:
- Grad-CAM (activation-based heatmap)
- Attention rollout (для attention-based моделей)
- Occlusion sensitivity
- Shapley value approximation (через occlusion)
- Gradient-based saliency maps
- Integrated gradients
- Визуализация наложений (overlay) и отчёты

Два бэкенда: cv2 (приоритет) → scipy/ndimage (fallback),
как в losses.py и postprocessing.py.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

__all__ = [
    "compute_gradcam",
    "compute_attention_rollout",
    "compute_occlusion_sensitivity",
    "compute_saliency",
    "compute_integrated_gradients",
    "compute_shapley_values",
    "overlay_heatmap",
    "generate_explanation_report",
]


# ----------------------------------------------------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ----------------------------------------------------------------------


def _resize_heatmap(heatmap: np.ndarray, target_shape: tuple[int, int]) -> np.ndarray:
    """Изменяет размер heatmap до target_shape (H, W).

    Uses cv2 with INTER_LINEAR interpolation, falls back to simple
    numpy repeat/reshape when cv2 is unavailable.
    """
    try:
        import cv2

        return cv2.resize(heatmap, (target_shape[1], target_shape[0]), interpolation=cv2.INTER_LINEAR)
    except ImportError:
        from scipy.ndimage import zoom

        factors = (target_shape[0] / heatmap.shape[0], target_shape[1] / heatmap.shape[1])
        return zoom(heatmap, factors, order=1)


def _normalize_heatmap(heatmap: np.ndarray) -> np.ndarray:
    """Нормализует heatmap в диапазон [0, 1]."""
    hmin, hmax = heatmap.min(), heatmap.max()
    if hmax - hmin < 1e-10:
        return np.zeros_like(heatmap, dtype=np.float32)
    return ((heatmap - hmin) / (hmax - hmin)).astype(np.float32)


def _prepare_input(image: np.ndarray) -> np.ndarray:
    """Подготавливает входное изображение для forward pass.

    Принимает (H, W, C) или (H, W). Возвращает (1, H, W, C) float32.
    """
    img = image.astype(np.float32)
    if img.ndim == 2:
        img = img[..., np.newaxis]
    if img.ndim == 3:
        img = img[np.newaxis, ...]
    return img


def _get_output_shape(model) -> tuple[int, int]:
    """Возвращает (H, W) выходного тензора модели."""
    out_shape = model.output_shape
    if isinstance(out_shape, list):
        out_shape = out_shape[0]
    return int(out_shape[1]), int(out_shape[2])


def _resolve_target_class(model, class_index: int | None) -> int:
    """Определяет целевой класс (class_index или последний канал для бинарной)."""
    if class_index is not None:
        return class_index
    out_channels = model.output_shape[-1]
    return out_channels - 1


def _find_last_conv_layer(model, layer_name: str | None = None) -> str:
    """Находит имя последнего свёрточного слоя или возвращает указанный.

    Parameters
    ----------
    model : tf.keras.Model
        Модель для поиска.
    layer_name : str, optional
        Явное имя слоя. Если задано — проверяется и возвращается.

    Returns
    -------
    str
        Имя слоя.

    Raises
    ------
    ValueError
        Если слой не найден.
    """
    if layer_name is not None:
        try:
            _ = model.get_layer(layer_name)
            return layer_name
        except ValueError:
            raise ValueError(
                f"Layer '{layer_name}' not found in model. Available layers: {[l.name for l in model.layers]}"
            )

    conv_layers = [
        layer.name for layer in model.layers if "conv" in layer.name.lower() or "Conv2D" in layer.__class__.__name__
    ]
    if not conv_layers:
        raise ValueError("No convolutional layers found in model. Specify layer_name explicitly.")

    return conv_layers[-1]


# ----------------------------------------------------------------------
# GRAD-CAM
# ----------------------------------------------------------------------


def compute_gradcam(
    model,
    image: np.ndarray,
    layer_name: str | None = None,
    class_index: int | None = None,
) -> np.ndarray:
    """Вычисляет Grad-CAM heatmap.

    Gradient-weighted Class Activation Mapping (Selvaraju et al., 2017).
    Показывает, какие области изображения наиболее важны для предсказания
    указанного класса.

    Parameters
    ----------
    model : tf.keras.Model
        Обученная модель (например, U-Net или Attention U-Net).
    image : np.ndarray
        Входное изображение формы (H, W, C) или (H, W).
        Значения в диапазоне [0, 1] или [0, 255].
    layer_name : str, optional
        Имя свёрточного слоя для извлечения активаций.
        Если None — берётся последний Conv2D слой.
    class_index : int, optional
        Индекс класса для визуализации. Для бинарной сегментации
        по умолчанию используется канал 1 (foreground).
        Если None — определяется автоматически.

    Returns
    -------
    np.ndarray
        Heatmap формы (H_out, W_out) с значениями в [0, 1].

    Raises
    ------
    ValueError
        Если слой не найден или входное изображение некорректно.

    Examples
    --------
    >>> model = build_attention_unet((256, 256, 11))
    >>> image = np.random.rand(256, 256, 11).astype(np.float32)
    >>> heatmap = compute_gradcam(model, image, class_index=1)
    """
    import tensorflow as tf

    if image.ndim < 2 or image.ndim > 4:
        raise ValueError(f"Image must be 2D, 3D, or 4D, got {image.ndim}D")

    target_class = _resolve_target_class(model, class_index)
    conv_layer_name = _find_last_conv_layer(model, layer_name)

    conv_layer = model.get_layer(conv_layer_name)
    grad_model = tf.keras.Model(
        inputs=[model.inputs],
        outputs=[conv_layer.output, model.output],
    )

    x = tf.cast(_prepare_input(image), tf.float32)

    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(x, training=False)
        if predictions.shape[-1] == 1:
            target = predictions[..., target_class] if predictions.shape[-1] > 1 else predictions[..., 0]
        else:
            target = predictions[..., target_class]

    grads = tape.gradient(target, conv_outputs)
    if grads is None:
        logger.warning("Gradients are None for layer '%s'. Returning zero heatmap.", conv_layer_name)
        h, w = _get_output_shape(model)
        return np.zeros((h, w), dtype=np.float32)

    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
    conv_outputs_val = conv_outputs[0]

    weighted = conv_outputs_val * pooled_grads
    heatmap = tf.reduce_mean(weighted, axis=-1).numpy()

    heatmap = np.maximum(heatmap, 0)
    heatmap = _normalize_heatmap(heatmap)

    target_shape = _get_output_shape(model)
    heatmap = _resize_heatmap(heatmap, target_shape)

    return heatmap


# ----------------------------------------------------------------------
# ATTENTION ROLLOUT
# ----------------------------------------------------------------------


def compute_attention_rollout(model, image: np.ndarray) -> np.ndarray:
    """Вычисляет attention rollout для моделей с attention gates.

    Attention rollout (Abnar & Zuidema, 2020) агрегирует attention веса
    через все уровни decoder'а, показывая cumulative attention.

    Parameters
    ----------
    model : tf.keras.Model
        Модель с attention gate слоями (Attention U-Net).
    image : np.ndarray
        Входное изображение формы (H, W, C).

    Returns
    -------
    np.ndarray
        Attention map формы (H, W) с значениями в [0, 1].

    Notes
    -----
    Если модель не содержит attention gate слоев — используется
    fallback: среднее абсолютных градиентов по каналам.
    """
    import tensorflow as tf

    x = tf.cast(_prepare_input(image), tf.float32)

    attention_layers = [layer for layer in model.layers if "attention" in layer.name.lower()]

    if attention_layers:
        intermediate_outputs = []
        for layer in attention_layers:
            intermediate_outputs.append(layer.output)

        intermediate_model = tf.keras.Model(
            inputs=model.inputs,
            outputs=[out for out in intermediate_outputs],
        )
        attentions = intermediate_model(x, training=False)

        if not isinstance(attentions, list):
            attentions = [attentions]

        result = np.ones(attentions[0].shape[1:3], dtype=np.float32)

        for att in attentions:
            att_val = att[0].numpy()
            if att_val.ndim == 4:
                att_val = att_val[..., 0]
            elif att_val.ndim == 3:
                att_val = np.mean(att_val, axis=-1)

            att_norm = _normalize_heatmap(att_val)
            result = result * att_norm

        result = _normalize_heatmap(result)
        target_shape = _get_output_shape(model)
        return _resize_heatmap(result, target_shape)

    logger.info("No attention layers found. Using gradient-based fallback.")
    return _gradient_based_attention(model, image)


def _gradient_based_attention(model, image: np.ndarray) -> np.ndarray:
    """Fallback: gradient-based attention через grad-cam на всех conv слоях."""

    conv_layers = [
        layer.name for layer in model.layers if "conv" in layer.name.lower() or "Conv2D" in layer.__class__.__name__
    ]

    if not conv_layers:
        h, w = _get_output_shape(model)
        return np.zeros((h, w), dtype=np.float32)

    accumulated = np.zeros((1, *_get_output_shape(model)), dtype=np.float32)

    for layer_name in conv_layers[:3]:
        try:
            hm = compute_gradcam(model, image, layer_name=layer_name)
            accumulated[0] += hm
        except Exception:
            continue

    accumulated /= max(len(conv_layers[:3]), 1)
    return _normalize_heatmap(accumulated[0])


# ----------------------------------------------------------------------
# OCCLUSION SENSITIVITY
# ----------------------------------------------------------------------


def compute_occlusion_sensitivity(
    model,
    image: np.ndarray,
    patch_size: int = 16,
    class_index: int | None = None,
) -> np.ndarray:
    """Вычисляет карту чувствительности к окклюзии.

    Показывает, насколько сильно каждый регион влияет на предсказание:
    закрывает патчи и измеряет падение уверенности.

    Parameters
    ----------
    model : tf.keras.Model
        Обученная модель.
    image : np.ndarray
        Входное изображение формы (H, W, C).
    patch_size : int
        Размер блока окклюзии в пикселях. По умолчанию 16.
    class_index : int, optional
        Индекс класса. Если None — определяется автоматически.

    Returns
    -------
    np.ndarray
        Карта чувствительности формы (H, W) с значениями в [0, 1].
        Высокие значения = регион важен для предсказания.

    Notes
    -----
    Вычислительно дорого для больших изображений. Рекомендуется
    patch_size >= 8.
    """

    H, W = image.shape[:2]
    target_class = _resolve_target_class(model, class_index)

    x_batch = _prepare_input(image)
    base_pred = model(x_batch, training=False).numpy()
    if base_pred.shape[-1] == 1:
        base_score = float(base_pred[0, ..., 0].mean())
    else:
        base_score = float(base_pred[0, ..., target_class].mean())

    sensitivity = np.zeros((H, W), dtype=np.float32)
    count_map = np.zeros((H, W), dtype=np.float32)

    occ_image = image.copy().astype(np.float32)

    for i in range(0, H, patch_size):
        for j in range(0, W, patch_size):
            occ_image[i : i + patch_size, j : j + patch_size, :] = 0.0

            occ_batch = occ_image[np.newaxis, ...].astype(np.float32)
            occ_pred = model(occ_batch, training=False).numpy()

            if occ_pred.shape[-1] == 1:
                occ_score = float(occ_pred[0, ..., 0].mean())
            else:
                occ_score = float(occ_pred[0, ..., target_class].mean())

            drop = base_score - occ_score

            sensitivity[i : i + patch_size, j : j + patch_size] += drop
            count_map[i : i + patch_size, j : j + patch_size] += 1

            occ_image[i : i + patch_size, j : j + patch_size, :] = image[i : i + patch_size, j : j + patch_size, :]

    count_map = np.maximum(count_map, 1)
    sensitivity /= count_map

    return _normalize_heatmap(sensitivity)


# ----------------------------------------------------------------------
# GRADIENT-BASED SALIENCY
# ----------------------------------------------------------------------


def compute_saliency(
    model,
    image: np.ndarray,
    class_index: int | None = None,
) -> np.ndarray:
    """Вычисляет gradient-based saliency map.

    Saliency = |d输出/d输入| (Simonyan et al., 2013).
    Показывает, какие пиксели входного изображения наиболее чувствительны
    к изменениям.

    Parameters
    ----------
    model : tf.keras.Model
        Обученная модель.
    image : np.ndarray
        Входное изображение формы (H, W, C).
    class_index : int, optional
        Индекс класса. Если None — определяется автоматически.

    Returns
    -------
    np.ndarray
        Saliency map формы (H, W) с значениями в [0, 1].

    Notes
    -----
    Метод чувствителен к шуму. Для более стабильных результатов
    рекомендуется integrated_gradients().
    """
    import tensorflow as tf

    target_class = _resolve_target_class(model, class_index)
    x = tf.Variable(_prepare_input(image), dtype=tf.float32)

    with tf.GradientTape() as tape:
        predictions = model(x, training=False)
        if predictions.shape[-1] == 1:
            target = predictions[..., 0]
        else:
            target = predictions[..., target_class]

    grads = tape.gradient(target, x)
    if grads is None:
        h, w = _get_output_shape(model)
        return np.zeros((h, w), dtype=np.float32)

    grads_val = grads[0].numpy()
    saliency = np.max(np.abs(grads_val), axis=-1)

    return _normalize_heatmap(saliency)


# ----------------------------------------------------------------------
# INTEGRATED GRADIENTS
# ----------------------------------------------------------------------


def compute_integrated_gradients(
    model,
    image: np.ndarray,
    steps: int = 50,
    class_index: int | None = None,
) -> np.ndarray:
    """Вычисляет Integrated Gradients (Sundararajan et al., 2017).

    Аппроксимация интеграла градиентов от базового (нулевого)
    изображения до целевого. Более стабильны и объяснимы, чем
    простые градиенты.

    Parameters
    ----------
    model : tf.keras.Model
        Обученная модель.
    image : np.ndarray
        Входное изображение формы (H, W, C).
    steps : int
        Количество шагов интерполяции. Больше = точнее, но медленнее.
        По умолчанию 50.
    class_index : int, optional
        Индекс класса. Если None — определяется автоматически.

    Returns
    -------
    np.ndarray
        Integrated gradients map формы (H, W) с значениями в [0, 1].

    References
    ----------
    Sundararajan, M., Taly, A., & Yan, Q. (2017).
    Axiomatic Attribution for Deep Networks. ICML 2017.
    """
    import tensorflow as tf

    target_class = _resolve_target_class(model, class_index)
    x = tf.cast(_prepare_input(image), tf.float32)
    baseline = tf.zeros_like(x)

    alphas = tf.linspace(0.0, 1.0, steps + 1)
    alphas = alphas[:, tf.newaxis, tf.newaxis, tf.newaxis, tf.newaxis]

    interpolated = baseline + alphas * (x - baseline)

    with tf.GradientTape() as tape:
        tape.watch(interpolated)
        predictions = model(interpolated, training=False)
        if predictions.shape[-1] == 1:
            targets = predictions[..., 0]
        else:
            targets = predictions[..., target_class]

    grads = tape.gradient(targets, interpolated)
    if grads is None:
        h, w = _get_output_shape(model)
        return np.zeros((h, w), dtype=np.float32)

    avg_grads = tf.reduce_mean(grads, axis=0)[0]
    integrated_grads = (x[0] - baseline[0]) * avg_grads
    ig_map = tf.reduce_max(tf.abs(integrated_grads), axis=-1).numpy()

    return _normalize_heatmap(ig_map)


# ----------------------------------------------------------------------
# SHAPLEY VALUE APPROXIMATION
# ----------------------------------------------------------------------


def compute_shapley_values(
    model,
    image: np.ndarray,
    patch_size: int = 16,
    class_index: int | None = None,
    n_permutations: int = 10,
) -> np.ndarray:
    """Аппроксимация Shapley values через permutation-based occlusion.

    Shapley values (Shapley, 1953) — теоретически обоснованная мера
    вклада каждого признака. Полный расчёт экспоненциально дорог,
    поэтому используется приближение через случайные перестановки.

    Parameters
    ----------
    model : tf.keras.Model
        Обученная модель.
    image : np.ndarray
        Входное изображение формы (H, W, C).
    patch_size : int
        Размер блока. По умолчанию 16.
    class_index : int, optional
        Индекс класса. Если None — определяется автоматически.
    n_permutations : int
        Количество случайных перестановок. Больше = точнее.
        По умолчанию 10.

    Returns
    -------
    np.ndarray
        Shapley value map формы (H, W) с значениями в [0, 1].

    Notes
    -----
    Метод медленный для больших изображений. Для скрининга
    рекомендуется compute_occlusion_sensitivity().
    """

    H, W = image.shape[:2]
    target_class = _resolve_target_class(model, class_index)

    n_patches_h = int(np.ceil(H / patch_size))
    n_patches_w = int(np.ceil(W / patch_size))
    n_patches = n_patches_h * n_patches_w

    patch_indices = []
    for pi in range(n_patches_h):
        for pj in range(n_patches_w):
            patch_indices.append((pi, pj))

    x_base = _prepare_input(image)
    base_pred = model(x_base, training=False).numpy()
    if base_pred.shape[-1] == 1:
        base_score = float(base_pred[0, ..., 0].mean())
    else:
        base_score = float(base_pred[0, ..., target_class].mean())

    shapley_map = np.zeros((H, W), dtype=np.float32)
    count_map = np.zeros((H, W), dtype=np.float32)

    rng = np.random.default_rng(42)

    for _ in range(n_permutations):
        perm = list(range(n_patches))
        rng.shuffle(perm)

        current_image = np.zeros_like(image, dtype=np.float32)

        for idx in perm:
            pi, pj = patch_indices[idx]
            i0 = pi * patch_size
            j0 = pj * patch_size
            i1 = min(i0 + patch_size, H)
            j1 = min(j0 + patch_size, W)

            current_image[i0:i1, j0:j1, :] = image[i0:i1, j0:j1, :]

            pred_after = model(current_image[np.newaxis, ...], training=False).numpy()
            if pred_after.shape[-1] == 1:
                score_after = float(pred_after[0, ..., 0].mean())
            else:
                score_after = float(pred_after[0, ..., target_class].mean())

            marginal = score_after - base_score
            shapley_map[i0:i1, j0:j1] += marginal
            count_map[i0:i1, j0:j1] += 1

    count_map = np.maximum(count_map, 1)
    shapley_map /= count_map

    return _normalize_heatmap(shapley_map)


# ----------------------------------------------------------------------
# OVERLAY HEATMAP
# ----------------------------------------------------------------------


def overlay_heatmap(
    heatmap: np.ndarray,
    image: np.ndarray,
    alpha: float = 0.4,
) -> np.ndarray:
    """Накладывает heatmap на изображение.

    Parameters
    ----------
    heatmap : np.ndarray
        Heatmap формы (H, W) с значениями в [0, 1].
    image : np.ndarray
        Изображение формы (H, W, C) или (H, W).
        Для RGB-визуализации используются каналы B4, B3, B2.
    alpha : float
        Прозрачность heatmap. 0.0 = только изображение,
        1.0 = только heatmap. По умолчанию 0.4.

    Returns
    -------
    np.ndarray
        RGB-изображение формы (H, W, 3) с наложенной heatmap.
        Значения в диапазоне [0, 1].

    Notes
    -----
    Heatmap автоматически масштабируется до размера изображения.
    Цветовая карта: синий (низкая важность) → жёлтый → красный (высокая).
    """
    try:
        import cv2

        heatmap_resized = cv2.resize(
            heatmap,
            (image.shape[1], image.shape[0]),
            interpolation=cv2.INTER_LINEAR,
        )
    except ImportError:
        from scipy.ndimage import zoom

        factors = (image.shape[0] / heatmap.shape[0], image.shape[1] / heatmap.shape[1])
        heatmap_resized = zoom(heatmap, factors, order=1)

    heatmap_resized = _normalize_heatmap(heatmap_resized)

    if image.ndim == 2:
        rgb_base = np.stack([image, image, image], axis=-1)
    elif image.shape[-1] == 1:
        rgb_base = np.concatenate([image, image, image], axis=-1)
    elif image.shape[-1] >= 3:
        rgb_base = image[:, :, :3].copy()
    else:
        rgb_base = np.concatenate([image, image, image], axis=-1)

    rgb_base = np.clip(rgb_base, 0, 1)

    heatmap_color = _apply_colormap(heatmap_resized)

    blended = (1 - alpha) * rgb_base + alpha * heatmap_color
    return np.clip(blended, 0, 1).astype(np.float32)


def _apply_colormap(heatmap: np.ndarray) -> np.ndarray:
    """Применяет цветовую карту (blue → yellow → red) к heatmap.

    Parameters
    ----------
    heatmap : np.ndarray
        Heatmap формы (H, W) в [0, 1].

    Returns
    -------
    np.ndarray
        RGB-изображение формы (H, W, 3).
    """
    try:
        import cv2

        heatmap_uint8 = (heatmap * 255).astype(np.uint8)
        colored = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
        return (colored[..., ::-1] / 255.0).astype(np.float32)
    except ImportError:
        pass

    h, w = heatmap.shape
    colored = np.zeros((h, w, 3), dtype=np.float32)

    low = heatmap <= 0.25
    mid_low = (heatmap > 0.25) & (heatmap <= 0.5)
    mid_high = (heatmap > 0.5) & (heatmap <= 0.75)
    high = heatmap > 0.75

    t = np.clip(heatmap / 0.25, 0, 1)
    colored[low, 0] = 0
    colored[low, 1] = t[low] * 0.5
    colored[low, 2] = 1.0

    t = np.clip((heatmap - 0.25) / 0.25, 0, 1)
    colored[mid_low, 0] = 0
    colored[mid_low, 1] = 0.5 + t[mid_low] * 0.5
    colored[mid_low, 2] = 1.0 - t[mid_low]

    t = np.clip((heatmap - 0.5) / 0.25, 0, 1)
    colored[mid_high, 0] = t[mid_high]
    colored[mid_high, 1] = 1.0
    colored[mid_high, 2] = 0

    t = np.clip((heatmap - 0.75) / 0.25, 0, 1)
    colored[high, 0] = 1.0
    colored[high, 1] = 1.0 - t[high]
    colored[high, 2] = 0

    return colored


# ----------------------------------------------------------------------
# EXPLANATION REPORT
# ----------------------------------------------------------------------


def generate_explanation_report(
    model,
    image: np.ndarray,
    layer_name: str | None = None,
    methods: list[str] | None = None,
    patch_size: int = 16,
) -> dict[str, Any]:
    """Генерирует полный отчёт объяснимости модели.

    Запускает все (или указанные) методы интерпретации и
    возвращает словарь с heatmap'ами и метаданными.

    Parameters
    ----------
    model : tf.keras.Model
        Обученная модель.
    image : np.ndarray
        Входное изображение формы (H, W, C).
    layer_name : str, optional
        Имя слоя для Grad-CAM. Если None — определяется автоматически.
    methods : list[str], optional
        Список методов для запуска. Доступные:
        "gradcam", "attention_rollout", "occlusion", "saliency",
        "integrated_gradients", "shapley".
        Если None — запускаются все методы.
    patch_size : int
        Размер блока для occlusion/shapley. По умолчанию 16.

    Returns
    -------
    dict
        Словарь с ключами:
        - "gradcam": np.ndarray — Grad-CAM heatmap
        - "attention_rollout": np.ndarray — Attention rollout map
        - "occlusion": np.ndarray — Occlusion sensitivity map
        - "saliency": np.ndarray — Gradient saliency map
        - "integrated_gradients": np.ndarray — Integrated gradients map
        - "shapley": np.ndarray — Shapley value map
        - "overlay": np.ndarray — RGB overlay с Grad-CAM
        - "metadata": dict — информация о модели и изображении

    Examples
    --------
    >>> report = generate_explanation_report(model, image)
    >>> overlay = report["overlay"]
    """
    available_methods = {
        "gradcam",
        "attention_rollout",
        "occlusion",
        "saliency",
        "integrated_gradients",
        "shapley",
    }

    if methods is None:
        methods_to_run = list(available_methods)
    else:
        methods_to_run = [m for m in methods if m in available_methods]

    report: dict[str, Any] = {}

    for method in methods_to_run:
        try:
            if method == "gradcam":
                report["gradcam"] = compute_gradcam(model, image, layer_name=layer_name)
            elif method == "attention_rollout":
                report["attention_rollout"] = compute_attention_rollout(model, image)
            elif method == "occlusion":
                report["occlusion"] = compute_occlusion_sensitivity(model, image, patch_size=patch_size)
            elif method == "saliency":
                report["saliency"] = compute_saliency(model, image)
            elif method == "integrated_gradients":
                report["integrated_gradients"] = compute_integrated_gradients(model, image)
            elif method == "shapley":
                report["shapley"] = compute_shapley_values(model, image, patch_size=patch_size)
        except Exception as e:
            logger.warning("Method '%s' failed: %s", method, e)
            report[method] = None

    if "gradcam" in report and report["gradcam"] is not None:
        report["overlay"] = overlay_heatmap(report["gradcam"], image)
    else:
        report["overlay"] = None

    report["metadata"] = {
        "model_name": model.name if hasattr(model, "name") else "unknown",
        "input_shape": list(image.shape),
        "output_shape": list(model.output_shape),
        "layer_used": layer_name or "auto",
        "methods_run": methods_to_run,
        "methods_succeeded": [m for m in methods_to_run if report.get(m) is not None],
    }

    return report
