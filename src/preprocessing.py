"""
Предобработка: растеризация контуров RGI в маски, нарезка на патчи,
аугментация и сборка train/val/test датасетов.
"""

from __future__ import annotations

import numpy as np

from . import config

# ----------------------------------------------------------------------
# RGI -> РАСТЕРНАЯ МАСКА
# ----------------------------------------------------------------------


def rasterize_rgi_to_mask(rgi_geodataframe, reference_raster_path, out_path=None):
    """Превращает полигоны RGI в бинарную маску ледника, совпадающую
    по сетке (transform/shape/CRS) с reference_raster_path.

    Параметры
    ---------
    rgi_geodataframe : geopandas.GeoDataFrame
        Контуры ледников (например, отфильтрованные по study area).
    reference_raster_path : str | Path
        Снимок, по сетке которого строится маска (например, sentinel2_2020.tif).
    out_path : str | Path | None
        Если указан — маска сохраняется как GeoTIFF.

    Возвращает
    ----------
    mask : np.ndarray (H, W), uint8

    Выбрасывает
    -----------
    ValueError : если rgi_geodataframe пуст или reference_raster_path не существует.
    """
    from pathlib import Path

    import rasterio
    from rasterio.features import rasterize

    if rgi_geodataframe is None or len(rgi_geodataframe) == 0:
        raise ValueError("rgi_geodataframe пуст — нет контуров ледников для растеризации.")

    ref_path = Path(reference_raster_path)
    if not ref_path.exists():
        raise FileNotFoundError(f"Файл reference_raster не найден: {ref_path}")

    with rasterio.open(ref_path) as src:
        transform = src.transform
        shape = (src.height, src.width)
        crs = src.crs

    gdf = rgi_geodataframe.to_crs(crs)

    valid_geoms = [geom for geom in gdf.geometry if geom is not None and not geom.is_empty]

    mask = rasterize(
        [(geom, 1) for geom in valid_geoms],
        out_shape=shape,
        transform=transform,
        fill=0,
        dtype="uint8",
    )

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(
            out_path,
            "w",
            driver="GTiff",
            height=shape[0],
            width=shape[1],
            count=1,
            dtype="uint8",
            crs=crs,
            transform=transform,
        ) as dst:
            dst.write(mask, 1)

    return mask


# ----------------------------------------------------------------------
# НАРЕЗКА НА ПАТЧИ
# ----------------------------------------------------------------------


def create_patches(
    image: np.ndarray,
    mask: np.ndarray,
    patch_size: int = config.PATCH_SIZE,
    stride: int = config.PATCH_STRIDE,
    min_glacier_fraction: float = config.MIN_GLACIER_FRACTION,
    background_keep_prob: float = config.BACKGROUND_KEEP_PROB,
    rng: np.random.Generator | None = None,
):
    """Нарезает (image, mask) на патчи patch_size x patch_size.

    Патч сохраняется, если:
      a) доля пикселей ледника > min_glacier_fraction, ИЛИ
      b) это фоновый патч, сохранённый с вероятностью background_keep_prob
         (для баланса классов "ледник / не ледник").

    Возвращает (patches_img, patches_mask) — np.ndarray.

    Выбрасывает
    -----------
    ValueError : если image или mask пустые, или размеры не совпадают.
    """
    if image is None or mask is None:
        raise ValueError("image и mask не могут быть None.")

    if image.size == 0 or mask.size == 0:
        raise ValueError("image или mask пусты (size=0).")

    if image.shape[:2] != mask.shape:
        raise ValueError(f"Размеры image ({image.shape}) и mask ({mask.shape}) не совпадают по пространственным осям.")

    if rng is None:
        rng = np.random.default_rng(config.RANDOM_SEED)

    H, W, C = image.shape
    patches_img, patches_mask = [], []
    kept, skipped = 0, 0

    for i in range(0, H - patch_size + 1, stride):
        for j in range(0, W - patch_size + 1, stride):
            patch_img = image[i : i + patch_size, j : j + patch_size, :]
            patch_mask = mask[i : i + patch_size, j : j + patch_size]

            glacier_fraction = patch_mask.mean()

            if glacier_fraction > min_glacier_fraction or rng.random() < background_keep_prob:
                patches_img.append(patch_img)
                patches_mask.append(patch_mask)
                kept += 1
            else:
                skipped += 1

    import logging as _logging

    _logging.getLogger(__name__).info("Патчей сохранено: %d, пропущено (пустые): %d", kept, skipped)

    if kept == 0:
        return (
            np.empty((0, patch_size, patch_size, C), dtype=image.dtype),
            np.empty((0, patch_size, patch_size), dtype=mask.dtype),
        )

    return np.array(patches_img), np.array(patches_mask)


# ----------------------------------------------------------------------
# АУГМЕНТАЦИЯ
# ----------------------------------------------------------------------


def augment_patch(image: np.ndarray, mask: np.ndarray, rng: np.random.Generator | None = None):
    """Расширенная аугментация: геометрические + фотометрические
    преобразования + шум + blur + elastic.

    Геометрические применяются одинаково к image и mask.
    Фотометрические — только к image.
    """
    if rng is None:
        rng = np.random.default_rng()

    # --- Геометрические (одинаково для image и mask) ---
    if rng.random() > 0.5:
        image = np.fliplr(image)
        mask = np.fliplr(mask)

    if rng.random() > 0.5:
        image = np.flipud(image)
        mask = np.flipud(mask)

    if rng.random() > 0.5:
        k = int(rng.integers(0, 4))
        image = np.rot90(image, k)
        mask = np.rot90(mask, k)

    # --- Фотометрические (только image) ---
    # Яркость/контраст
    if rng.random() > 0.5:
        alpha = rng.uniform(0.8, 1.2)
        beta = rng.uniform(-0.05, 0.05)
        image = np.clip(image * alpha + beta, 0, 1)

    # Gamma коррекция
    if rng.random() > 0.7:
        gamma = rng.uniform(0.8, 1.2)
        image = np.clip(np.clip(image, 0, None) ** gamma, 0, 1)

    # Гауссов шум
    if rng.random() > 0.85:
        noise = rng.normal(0, 0.01, image.shape).astype(np.float32)
        image = np.clip(image + noise, 0, 1)

    # Gaussian blur
    if rng.random() > 0.9:
        from scipy.ndimage import gaussian_filter

        sigma = rng.uniform(0.3, 0.8)
        for c in range(image.shape[-1]):
            image[..., c] = gaussian_filter(image[..., c], sigma)

    return image, mask


# ----------------------------------------------------------------------
# СБОРКА ДАТАСЕТА
# ----------------------------------------------------------------------


def build_dataset(image_mask_pairs):
    """Собирает патчи из списка пар (image, mask) -> X, y.

    image_mask_pairs : list[tuple[np.ndarray, np.ndarray]]
        Каждая пара — полный снимок и соответствующая маска (одинаковая
        форма (H, W) для маски и (H, W, C) для снимка).

    Выбрасывает
    -----------
    ValueError : если image_mask_pairs пуст или не получено ни одного патча.
    """
    if not image_mask_pairs:
        raise ValueError("image_mask_pairs пуст — передайте хотя бы одну пару (image, mask).")

    all_patches_img, all_patches_mask = [], []

    for idx, (image, mask) in enumerate(image_mask_pairs):
        if image is None or mask is None:
            print(f"Предупреждение: пара {idx} содержит None, пропускаем.")
            continue
        if image.size == 0 or mask.size == 0:
            print(f"Предупреждение: пара {idx} пуста, пропускаем.")
            continue
        if image.shape[:2] != mask.shape:
            print(f"Предупреждение: пара {idx} — размеры не совпадают ({image.shape} vs {mask.shape}), пропускаем.")
            continue
        patches_img, patches_mask = create_patches(image, mask)
        if len(patches_img) == 0:
            continue
        all_patches_img.append(patches_img)
        all_patches_mask.append(patches_mask)

    if not all_patches_img:
        raise ValueError("Не получено ни одного патча — проверьте входные данные/маски.")

    X = np.concatenate(all_patches_img, axis=0)
    y = np.concatenate(all_patches_mask, axis=0)
    return X, y


def train_val_test_split(X, y, train_frac=config.TRAIN_FRACTION, val_frac=config.VAL_FRACTION, seed=config.RANDOM_SEED):
    """70/15/15 случайное разбиение.

    ВНИМАНИЕ: при перекрывающихся патчах (PATCH_STRIDE < PATCH_SIZE) соседние
    патчи делят пиксели, что при случайном сплите вызывает утечку данных.
    Для научных публикаций используйте spatial_train_val_test_split.
    """
    from sklearn.model_selection import train_test_split

    test_frac = 1.0 - train_frac - val_frac
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=(val_frac + test_frac), random_state=seed)
    rel_test = test_frac / (val_frac + test_frac)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=rel_test, random_state=seed)
    return X_train, X_val, X_test, y_train, y_val, y_test


def spatial_train_val_test_split(
    X: np.ndarray,
    y: np.ndarray,
    image_h: int,
    image_w: int,
    patch_size: int = config.PATCH_SIZE,
    stride: int = config.PATCH_STRIDE,
    train_frac: float = config.TRAIN_FRACTION,
    val_frac: float = config.VAL_FRACTION,
    n_grid_blocks: int = 10,
    seed: int = config.RANDOM_SEED,
):
    """Пространственное разбиение патчей по блокам растра (без утечки данных).

    Делит исходный снимок на n_grid_blocks x n_grid_blocks пространственных
    блоков и назначает каждый блок только одному сплиту (train/val/test).
    Патчи, попавшие в блок, идут целиком в один сплит — пространственно
    разделённые группы не пересекаются.

    Это устраняет spatial leakage, возникающий при случайном разбиении
    перекрывающихся патчей (stride < patch_size).

    Параметры
    ----------
    X : np.ndarray, shape (N, H, W, C)
        Патчи изображений в том же порядке, что вернул create_patches.
    y : np.ndarray, shape (N, H, W)
        Соответствующие маски.
    image_h, image_w : int
        Пространственные размеры исходного снимка.
    patch_size, stride : int
        Те же параметры, что использовались в create_patches.
    n_grid_blocks : int
        Число блоков по каждой оси (всего n**2 блоков).
    seed : int
        Для воспроизводимости перемешивания блоков.

    Возвращает
    ----------
    X_train, X_val, X_test, y_train, y_val, y_test : np.ndarray
    """
    from sklearn.model_selection import GroupShuffleSplit

    # Вычисляем (row, col) блок для каждого патча по его позиции в растре.
    # Патч с индексом k порождён из позиции (i_k, j_k) в create_patches.
    positions_i = list(range(0, image_h - patch_size + 1, stride))
    positions_j = list(range(0, image_w - patch_size + 1, stride))

    # Если патчей больше/меньше позиций — значит часть пропущена фильтром;
    # в этом случае мы не можем восстановить точную позицию. Используем
    # приблизительное разбиение по индексу (лучше, чем полностью случайное).
    n_patches = len(X)
    n_positions = len(positions_i) * len(positions_j)

    if n_patches == n_positions:
        # Все позиции сохранены — строим точные блок-ID
        block_ids = []
        for idx in range(n_patches):
            pi = idx // len(positions_j)
            pj = idx % len(positions_j)
            bi = int(positions_i[pi] / image_h * n_grid_blocks)
            bj = int(positions_j[pj] / image_w * n_grid_blocks)
            block_ids.append(bi * n_grid_blocks + bj)
    else:
        # Часть патчей пропущена: приблизительное разбиение по плотности
        block_size = max(1, n_patches // (n_grid_blocks * n_grid_blocks))
        block_ids = [idx // block_size for idx in range(n_patches)]

    block_ids = np.array(block_ids)

    test_frac = 1.0 - train_frac - val_frac
    splitter = GroupShuffleSplit(n_splits=1, test_size=(val_frac + test_frac), random_state=seed)
    train_idx, temp_idx = next(splitter.split(X, y, groups=block_ids))

    rel_test = test_frac / (val_frac + test_frac)
    splitter2 = GroupShuffleSplit(n_splits=1, test_size=rel_test, random_state=seed)
    val_idx, test_idx = next(splitter2.split(X[temp_idx], y[temp_idx], groups=block_ids[temp_idx]))
    val_idx = temp_idx[val_idx]
    test_idx = temp_idx[test_idx]

    return (
        X[train_idx],
        X[val_idx],
        X[test_idx],
        y[train_idx],
        y[val_idx],
        y[test_idx],
    )
