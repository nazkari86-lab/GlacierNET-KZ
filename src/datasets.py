#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Управление датасетами и загрузка данных для GlacierNET-KZ.

Модуль обеспечивает обнаружение, регистрацию, разбиение, валидацию
и статистический анализ датасетов спутниковых снимков с масками
ледников. Поддерживает патчирование с перекрытием, аугментацию
и создание tf.data.Dataset для обучения.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from . import config

# ----------------------------------------------------------------------
# РЕЕСТР ДАТАСЕТОВ
# ----------------------------------------------------------------------

DATASET_REGISTRY: dict[str, dict[str, Any]] = {
    "glacierkz_sentinel2": {
        "name": "GlacierKZ Sentinel-2",
        "path": str(config.DATA_RAW_SENTINEL2),
        "years": config.YEARS_SENTINEL2,
        "bands": config.ALL_BAND_NAMES,
        "n_bands": config.N_CHANNELS,
        "resolution": config.EXPORT_SCALE_M,
        "description": (
            "Медианные летние композиты Sentinel-2 SR за 2015–2024 гг. "
            "Область: Заилийский и Джунгарский Алатау. "
            "11 каналов: 7 спектральных + 4 индекса."
        ),
    },
    "glacierkz_landsat": {
        "name": "GlacierKZ Landsat",
        "path": str(config.DATA_RAW_LANDSAT),
        "years": config.YEARS_LANDSAT,
        "bands": config.S2_BANDS + config.INDEX_NAMES,
        "n_bands": len(config.S2_BANDS + config.INDEX_NAMES),
        "resolution": config.EXPORT_SCALE_M,
        "description": (
            "Медианные летние композиты Landsat 7/8 SR за 2000–2013 гг. "
            "5 каналов (B2/B3/B4/B8/B11) + 4 индекса. "
            "B8A и B12 отсутствуют, заполняются NaN."
        ),
    },
    "glacierkz_patches": {
        "name": "GlacierKZ Patches",
        "path": str(config.DATA_PATCHES),
        "years": [2020],
        "bands": config.ALL_BAND_NAMES,
        "n_bands": config.N_CHANNELS,
        "resolution": config.EXPORT_SCALE_M,
        "description": (
            "Патчи 256×256 из предобработанных снимков за 2020 г. Используются для обучения U-Net и Attention U-Net."
        ),
    },
}


__all__ = [
    "DATASET_REGISTRY",
    "discover_datasets",
    "create_splits",
    "validate_dataset",
    "extract_patches",
    "compute_dataset_stats",
    "create_tf_dataset",
    "save_dataset_info",
    "load_config",
    "register_dataset",
    "list_datasets",
]


# ----------------------------------------------------------------------
# РЕГИСТРАЦИЯ И ПЕРЕЧИСЛЕНИЕ
# ----------------------------------------------------------------------


def register_dataset(name: str, path: str, **kwargs: Any) -> None:
    """Добавляет датасет в реестр.

    Parameters
    ----------
    name : str
        Уникальный ключ датасета (например ``'my_dataset'``).
    path : str
        Путь к корневой директории датасета.
    **kwargs
        Дополнительные поля: ``years``, ``bands``, ``resolution``,
        ``description`` и т.д.

    Raises
    ------
    ValueError
        Если датасет с таким именем уже зарегистрирован.
    """
    if name in DATASET_REGISTRY:
        raise ValueError(f"Датасет '{name}' уже зарегистрирован. Используйте другое имя или удалите существующий.")

    DATASET_REGISTRY[name] = {
        "name": name,
        "path": path,
        "years": kwargs.pop("years", []),
        "bands": kwargs.pop("bands", []),
        "n_bands": kwargs.pop("n_bands", len(kwargs.pop("bands", []))),
        "resolution": kwargs.pop("resolution", config.EXPORT_SCALE_M),
        "description": kwargs.pop("description", ""),
        **kwargs,
    }


def list_datasets() -> list[str]:
    """Возвращает список имён всех зарегистрированных датасетов.

    Returns
    -------
    list[str]
        Отсортированный список ключей датасетов.
    """
    return sorted(DATASET_REGISTRY.keys())


def load_config(dataset_name: str) -> dict[str, Any]:
    """Загружает конфигурацию датасета из реестра.

    Parameters
    ----------
    dataset_name : str
        Имя датасета в ``DATASET_REGISTRY``.

    Returns
    -------
    dict[str, Any]
        Копия конфигурации датасета.

    Raises
    ------
    KeyError
        Если датасет не найден в реестре.
    """
    if dataset_name not in DATASET_REGISTRY:
        available = ", ".join(sorted(DATASET_REGISTRY.keys()))
        raise KeyError(f"Датасет '{dataset_name}' не найден. Доступные: {available}")
    return dict(DATASET_REGISTRY[dataset_name])


# ----------------------------------------------------------------------
# ОБНАРУЖЕНИЕ ДАТАСЕТОВ
# ----------------------------------------------------------------------


def _compute_file_hash(filepath: str | Path, chunk_size: int = 8192) -> str:
    """Вычисляет SHA-256 хеш файла."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()


def _get_file_metadata(filepath: Path) -> dict[str, Any]:
    """Извлекает метаданные для одного растрового файла."""
    stat = filepath.stat()
    meta: dict[str, Any] = {
        "path": str(filepath),
        "filename": filepath.name,
        "size_bytes": stat.st_size,
        "extension": filepath.suffix.lower(),
    }

    if filepath.suffix.lower() == ".npy":
        try:
            arr = np.load(filepath, mmap_mode="r")
            meta["shape"] = list(arr.shape)
            meta["dtype"] = str(arr.dtype)
            meta["ndim"] = arr.ndim
        except Exception as exc:
            meta["load_error"] = str(exc)
    elif filepath.suffix.lower() in (".tif", ".tiff"):
        try:
            import rasterio

            with rasterio.open(filepath) as src:
                meta["shape"] = [src.height, src.width]
                meta["n_bands"] = src.count
                meta["dtype"] = str(src.dtypes[0]) if src.dtypes else "unknown"
                meta["crs"] = str(src.crs) if src.crs else None
                meta["transform"] = list(src.transform) if src.transform else None
                meta["ndim"] = 2 if src.count == 1 else 3
        except Exception as exc:
            meta["load_error"] = str(exc)

    return meta


def discover_datasets(root_dir: str) -> list[dict[str, Any]]:
    """Сканирует директорию на наличие .npy/.tif файлов и строит метаданные.

    Parameters
    ----------
    root_dir : str
        Путь к корневой директории для сканирования.

    Returns
    -------
    list[dict]
        Список метаданных найденных файлов. Каждый элемент содержит
        ``path``, ``filename``, ``size_bytes``, ``shape`` и другие поля.

    Raises
    ------
    FileNotFoundError
        Если ``root_dir`` не существует.
    NotADirectoryError
        Если ``root_dir`` не является директорией.
    """
    root = Path(root_dir)
    if not root.exists():
        raise FileNotFoundError(f"Директория не найдена: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Не является директорией: {root}")

    extensions = {".npy", ".tif", ".tiff"}
    datasets: list[dict[str, Any]] = []

    for filepath in sorted(root.rglob("*")):
        if filepath.is_file() and filepath.suffix.lower() in extensions:
            meta = _get_file_metadata(filepath)
            meta["hash"] = _compute_file_hash(filepath)
            datasets.append(meta)

    return datasets


# ----------------------------------------------------------------------
# РАЗБИЕНИЕ НА ВЫБОРКИ
# ----------------------------------------------------------------------


def create_splits(
    images: np.ndarray | list,
    masks: np.ndarray | list,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> dict[str, np.ndarray]:
    """Разбивает данные на train/val/test индексы.

    Parameters
    ----------
    images : np.ndarray | list
        Массив изображений формы ``(N, H, W, C)`` или список.
    masks : np.ndarray | list
        Массив масок формы ``(N, H, W)`` или ``(N, H, W, 1)``.
    train_ratio : float
        Доля обучающей выборки.
    val_ratio : float
        Доля валидационной выборки.
    test_ratio : float
        Доля тестовой выборки.
    seed : int
        Случайный зерно для воспроизводимости.

    Returns
    -------
    dict[str, np.ndarray]
        Словарь с ключами ``'train'``, ``'val'``, ``'test'`` —
        массивы индексов.

    Raises
    ------
    ValueError
        Если сумма долей не равна 1.0 или длины images/masks различны.
    """
    n_images = len(images)
    n_masks = len(masks)

    if n_images != n_masks:
        raise ValueError(f"Количество изображений ({n_images}) не совпадает с количеством масок ({n_masks})")

    ratios_sum = train_ratio + val_ratio + test_ratio
    if abs(ratios_sum - 1.0) > 1e-6:
        raise ValueError(f"Сумма долей = {ratios_sum:.4f}, ожидается 1.0")

    rng = np.random.default_rng(seed)
    indices = rng.permutation(n_images)

    train_end = int(n_images * train_ratio)
    val_end = train_end + int(n_images * val_ratio)

    return {
        "train": indices[:train_end],
        "val": indices[train_end:val_end],
        "test": indices[val_end:],
    }


# ----------------------------------------------------------------------
# ВАЛИДАЦИЯ ДАТАСЕТОВ
# ----------------------------------------------------------------------


def validate_dataset(dataset_dir: str) -> dict[str, Any]:
    """Проверяет целостность файлов, размерности и статистику nodata.

    Parameters
    ----------
    dataset_dir : str
        Путь к директории датасета.

    Returns
    -------
    dict
        Результаты валидации:
        - ``total_files``: общее количество файлов
        - ``valid_files``: количество файлов без ошибок
        - ``errors``: список ошибок
        - ``shapes``: словарь форм (shape -> количество)
        - ``dtypes``: словарь типов (dtype -> количество)
        - ``nodata_stats``: статистика nodata по файлам
        - ``extensions``: распределение по расширениям
    """
    root = Path(dataset_dir)
    result: dict[str, Any] = {
        "total_files": 0,
        "valid_files": 0,
        "errors": [],
        "shapes": {},
        "dtypes": {},
        "nodata_stats": [],
        "extensions": {},
    }

    if not root.exists():
        result["errors"].append(f"Директория не найдена: {root}")
        return result

    extensions = {".npy", ".tif", ".tiff"}
    for filepath in sorted(root.rglob("*")):
        if not filepath.is_file():
            continue
        if filepath.suffix.lower() not in extensions:
            continue

        result["total_files"] += 1
        ext = filepath.suffix.lower()
        result["extensions"][ext] = result["extensions"].get(ext, 0) + 1

        try:
            if ext == ".npy":
                arr = np.load(str(filepath))
                shape_key = str(arr.shape)
                dtype_key = str(arr.dtype)
            elif ext in (".tif", ".tiff"):
                import rasterio

                with rasterio.open(filepath) as src:
                    arr = src.read()
                    shape_key = str(arr.shape)
                    dtype_key = str(arr.dtypes[0]) if src.dtypes else "unknown"
            else:
                continue

            result["shapes"][shape_key] = result["shapes"].get(shape_key, 0) + 1
            result["dtypes"][dtype_key] = result["dtypes"].get(dtype_key, 0) + 1

            total = arr.size
            nodata_count = int(np.sum(np.isnan(arr)) + np.sum(np.isinf(arr)))
            if arr.dtype.kind in ("i", "u", "b"):
                nodata_count += int(np.sum(arr == 0))

            nodata_ratio = nodata_count / total if total > 0 else 0.0
            result["nodata_stats"].append(
                {
                    "file": filepath.name,
                    "nodata_count": nodata_count,
                    "total_pixels": total,
                    "nodata_ratio": round(nodata_ratio, 6),
                }
            )

            result["valid_files"] += 1

        except Exception as exc:
            result["errors"].append(f"{filepath.name}: {exc}")

    return result


# ----------------------------------------------------------------------
# ИЗВЛЕЧЕНИЕ ПАТЧЕЙ
# ----------------------------------------------------------------------


def extract_patches(
    image: np.ndarray,
    mask: np.ndarray,
    patch_size: int = 256,
    overlap: float = 0.5,
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Извлекает перекрывающиеся патчи из изображения и маски.

    Parameters
    ----------
    image : np.ndarray
        Изображение формы ``(H, W, C)``.
    mask : np.ndarray
        Маска формы ``(H, W)`` или ``(H, W, 1)``.
    patch_size : int
        Размер патча (пикселей по стороне).
    overlap : float
        Коэффициент перекрытия (0.0–0.9). Шаг ``= patch_size * (1 - overlap)``.

    Returns
    -------
    tuple[list[np.ndarray], list[np.ndarray]]
        ``(patches_images, patches_masks)`` — списки патчей.

    Raises
    ------
    ValueError
        Если ``patch_size`` больше размера изображения или ``overlap``
        вне диапазона [0, 1).
    """
    if not 0.0 <= overlap < 1.0:
        raise ValueError(f"overlap={overlap}, ожидается [0.0, 1.0)")
    if patch_size > min(image.shape[0], image.shape[1]):
        raise ValueError(f"patch_size={patch_size} больше размера изображения ({image.shape[0]}×{image.shape[1]})")

    step = int(patch_size * (1.0 - overlap))
    if step < 1:
        step = 1

    if mask.ndim == 3:
        mask = mask[..., 0]

    h, w = image.shape[:2]
    patches_img: list[np.ndarray] = []
    patches_msk: list[np.ndarray] = []

    for y in range(0, h - patch_size + 1, step):
        for x in range(0, w - patch_size + 1, step):
            patch_img = image[y : y + patch_size, x : x + patch_size].copy()
            patch_msk = mask[y : y + patch_size, x : x + patch_size].copy()
            patches_img.append(patch_img)
            patches_msk.append(patch_msk)

    return patches_img, patches_msk


# ----------------------------------------------------------------------
# СТАТИСТИКА ДАТАСЕТОВ
# ----------------------------------------------------------------------


def compute_dataset_stats(images_dir: str) -> dict[str, Any]:
    """Вычисляет статистику (mean, std, min, max, nodata_ratio) по каналам.

    Сканирует все .npy и .tif файлы в директории и агрегирует
    статистику по каждому каналу.

    Parameters
    ----------
    images_dir : str
        Путь к директории с изображениями.

    Returns
    -------
    dict
        ``per_band``: список статистик по каналам ``[mean, std, min, max, nodata_ratio]``.
        ``total_files``: количество обработанных файлов.
        ``total_pixels``: общее количество пикселей.
        ``band_names``: список имён каналов (из конфига или ``['band_0', ...]``).
    """
    root = Path(images_dir)
    extensions = {".npy", ".tif", ".tiff"}

    all_bands: list[list[float]] | None = None
    total_files = 0
    total_pixels = 0

    for filepath in sorted(root.rglob("*")):
        if not filepath.is_file():
            continue
        if filepath.suffix.lower() not in extensions:
            continue

        try:
            if filepath.suffix.lower() == ".npy":
                arr = np.load(str(filepath)).astype(np.float32)
                if arr.ndim == 2:
                    arr = arr[..., np.newaxis]
            else:
                import rasterio

                with rasterio.open(filepath) as src:
                    arr = src.read().astype(np.float32)
                    arr = np.moveaxis(arr, 0, -1)

        except Exception:
            continue

        n_bands = arr.shape[-1]
        if all_bands is None:
            all_bands = [[] for _ in range(n_bands)]

        pixels_per_band = arr.shape[0] * arr.shape[1]
        total_pixels += pixels_per_band
        total_files += 1

        for b in range(n_bands):
            band_data = arr[..., b].ravel()
            valid = band_data[np.isfinite(band_data)]

            band_stats = {
                "mean": float(np.mean(valid)) if len(valid) > 0 else 0.0,
                "std": float(np.std(valid)) if len(valid) > 0 else 0.0,
                "min": float(np.min(valid)) if len(valid) > 0 else 0.0,
                "max": float(np.max(valid)) if len(valid) > 0 else 0.0,
                "nodata_ratio": float(1.0 - len(valid) / len(band_data)) if len(band_data) > 0 else 1.0,
            }
            all_bands[b].append(band_stats)

    per_band: list[dict[str, float]] = []
    if all_bands:
        for b, band_list in enumerate(all_bands):
            if not band_list:
                per_band.append({"mean": 0, "std": 0, "min": 0, "max": 0, "nodata_ratio": 1})
                continue

            agg = {
                "mean": float(np.mean([s["mean"] for s in band_list])),
                "std": float(np.mean([s["std"] for s in band_list])),
                "min": float(np.min([s["min"] for s in band_list])),
                "max": float(np.max([s["max"] for s in band_list])),
                "nodata_ratio": float(np.mean([s["nodata_ratio"] for s in band_list])),
            }
            per_band.append(agg)

    band_names = list(config.ALL_BAND_NAMES) if per_band else []
    if len(band_names) < len(per_band):
        band_names += [f"band_{i}" for i in range(len(band_names), len(per_band))]

    return {
        "per_band": per_band,
        "band_names": band_names[: len(per_band)],
        "total_files": total_files,
        "total_pixels": total_pixels,
    }


# ----------------------------------------------------------------------
# TF DATASET
# ----------------------------------------------------------------------


def create_tf_dataset(
    images: np.ndarray,
    masks: np.ndarray,
    batch_size: int = 8,
    augment: bool = False,
    shuffle: bool = True,
):
    """Создаёт ``tf.data.Dataset`` для обучения.

    Parameters
    ----------
    images : np.ndarray
        Массив изображений ``(N, H, W, C)``, float32.
    masks : np.ndarray
        Массив масок ``(N, H, W)`` или ``(N, H, W, 1)``, float32/int.
    batch_size : int
        Размер батча.
    augment : bool
        Включить аугментацию (отражения, повороты).
    shuffle : bool
        Перемешивать данные.

    Returns
    -------
    tf.data.Dataset
        Датасет ``(image, mask)``.
    """
    import tensorflow as tf

    if masks.ndim == 3:
        masks = masks[..., np.newaxis]

    images = images.astype(np.float32)
    masks = masks.astype(np.float32)

    dataset = tf.data.Dataset.from_tensor_slices((images, masks))

    if shuffle:
        dataset = dataset.shuffle(buffer_size=min(len(images), 1000), seed=config.RANDOM_SEED)

    if augment:

        def _augment(image: tf.Tensor, mask: tf.Tensor) -> tuple[tf.Tensor, tf.Tensor]:
            if tf.random.uniform(()) > 0.5:
                image = tf.image.flip_left_right(image)
                mask = tf.image.flip_left_right(mask)
            if tf.random.uniform(()) > 0.5:
                image = tf.image.flip_up_down(image)
                mask = tf.image.flip_up_down(mask)
            k = tf.random.uniform(shape=(), minval=0, maxval=4, dtype=tf.int32)
            image = tf.image.rot90(image, k)
            mask = tf.image.rot90(mask, k)
            return image, mask

        dataset = dataset.map(_augment, num_parallel_calls=tf.data.AUTOTUNE)

    dataset = dataset.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    return dataset


# ----------------------------------------------------------------------
# СОХРАНЕНИЕ МЕТАДАННЫХ
# ----------------------------------------------------------------------


def save_dataset_info(dataset_dir: str, output_path: str) -> None:
    """Сохраняет метаданные датасета в JSON-файл.

    Parameters
    ----------
    dataset_dir : str
        Путь к директории датасета.
    output_path : str
        Путь для сохранения JSON-файла.

    Notes
    -----
    Файл содержит: ``discovered_files``, ``validation``, ``stats``,
    ``config_path``, ``config``.
    """
    root = Path(dataset_dir)
    info: dict[str, Any] = {
        "dataset_dir": str(root.resolve()),
        "discovered_files": discover_datasets(dataset_dir),
        "validation": validate_dataset(dataset_dir),
        "config_path": None,
        "config": None,
    }

    matched_name = None
    for name, cfg in DATASET_REGISTRY.items():
        if str(root.resolve()) == str(Path(cfg["path"]).resolve()):
            matched_name = name
            break

    if matched_name:
        info["config_path"] = matched_name
        info["config"] = DATASET_REGISTRY[matched_name]

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2, default=str)

    print(f"Метаданные датасета сохранены: {output}")
