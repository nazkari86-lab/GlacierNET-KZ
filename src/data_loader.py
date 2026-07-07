"""
Загрузка спутниковых снимков (Sentinel-2 / Landsat) через Google Earth Engine
и чтение растровых файлов с диска (rasterio).

ВНИМАНИЕ: функции get_sentinel2 / get_landsat / export_year требуют
рабочей аутентификации Earth Engine (`earthengine authenticate`) и
выполняются ТОЛЬКО локально — в облачной песочнице сети GEE нет.
"""

from __future__ import annotations

import numpy as np

from . import config

# ----------------------------------------------------------------------
# GOOGLE EARTH ENGINE — СКАЧИВАНИЕ
# ----------------------------------------------------------------------


def get_sentinel2(year: int, aoi, max_cloud: int = 15):
    """Медианный летний композит Sentinel-2 SR за июль-сентябрь.

    Параметры
    ---------
    year : int
    aoi : ee.Geometry
    max_cloud : int
        Порог CLOUDY_PIXEL_PERCENTAGE. Если снимков нет — повтор с 30%.

    Возвращает
    ----------
    ee.Image | None — None, если ни одного снимка не найдено.
    """
    import ee

    date_start = f"{year}-{config.SUMMER_START_MONTH_DAY}"
    date_end = f"{year}-{config.SUMMER_END_MONTH_DAY}"

    def _collection(cloud_threshold):
        return (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(aoi)
            .filterDate(date_start, date_end)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_threshold))
        )

    collection = _collection(max_cloud)
    count = collection.size().getInfo()
    print(f"{year}: найдено {count} снимков с облачностью <{max_cloud}%")

    if count == 0:
        print("  Нет снимков! Пробуем с облачностью <30%...")
        collection = _collection(30)
        count = collection.size().getInfo()
        if count == 0:
            print(f"  {year}: снимков нет даже при 30% — пропускаем.")
            return None

    image = collection.select(config.S2_BANDS).median().clip(aoi).clamp(0, config.S2_SCALE).toUint16()
    return image


def get_landsat(year: int, aoi, max_cloud: int = 20):
    """Медианный летний композит Landsat (5/7/8 SR) за июль-сентябрь.

    Для совместимости с индексами выбираются и переименовываются каналы
    в общую схему B2/B3/B4/B8/B11 (Landsat не имеет B8A/B12 -> заполняются NaN
    на этапе предобработки или исключаются из индексов для старых лет).
    """
    import ee

    date_start = f"{year}-{config.SUMMER_START_MONTH_DAY}"
    date_end = f"{year}-{config.SUMMER_END_MONTH_DAY}"

    if year >= 2013:
        collection_id = "LANDSAT/LC08/C02/T1_L2"
        band_map = {"SR_B2": "B2", "SR_B3": "B3", "SR_B4": "B4", "SR_B5": "B8", "SR_B6": "B11"}
    else:
        collection_id = "LANDSAT/LE07/C02/T1_L2"
        band_map = {"SR_B1": "B2", "SR_B2": "B3", "SR_B3": "B4", "SR_B4": "B8", "SR_B5": "B11"}

    collection = (
        ee.ImageCollection(collection_id)
        .filterBounds(aoi)
        .filterDate(date_start, date_end)
        .filter(ee.Filter.lt("CLOUD_COVER", max_cloud))
    )

    count = collection.size().getInfo()
    print(f"{year} (Landsat): найдено {count} снимков")
    if count == 0:
        print(f"  {year}: снимков Landsat нет — пропускаем.")
        return None

    image = collection.select(list(band_map.keys()), list(band_map.values())).median().clip(aoi)
    image = image.multiply(0.0000275).add(-0.2).multiply(config.S2_SCALE)
    return image


def add_indices(image):
    """Добавляет NDSI, NDWI, BSI, EVI к изображению ee.Image.

    Порядок добавляемых каналов соответствует config.INDEX_NAMES.
    """
    ndsi = image.normalizedDifference(["B3", "B11"]).rename("NDSI")
    ndwi = image.normalizedDifference(["B8", "B11"]).rename("NDWI")

    bsi = image.expression(
        "((SWIR + RED) - (NIR + BLUE)) / ((SWIR + RED) + (NIR + BLUE))",
        {
            "SWIR": image.select("B11"),
            "RED": image.select("B4"),
            "NIR": image.select("B8"),
            "BLUE": image.select("B2"),
        },
    ).rename("BSI")

    evi = image.expression(
        "2.5 * (NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1)",
        {
            "NIR": image.select("B8"),
            "RED": image.select("B4"),
            "BLUE": image.select("B2"),
        },
    ).rename("EVI")

    # Earth Engine refuses Drive exports when bands have mixed numeric types.
    # Cast every band to Float32 so the export schema is uniform.
    return image.toFloat().addBands([ndsi, ndwi, bsi, evi])


def export_year_to_drive(image, year: int, aoi, prefix: str = "sentinel2", folder: str = "GlacierKZ"):
    """Запускает задачу экспорта композита в Google Drive.

    Если image is None — год пропускается без ошибки.
    """
    import ee

    if image is None:
        print(f"  {prefix}_{year}: изображение пустое — пропускаем.")
        return None

    try:
        task = ee.batch.Export.image.toDrive(
            image=image,
            description=f"{prefix}_{year}",
            folder=folder,
            fileNamePrefix=f"{prefix}_{year}",
            region=aoi,
            scale=config.EXPORT_SCALE_M,
            crs=config.EXPORT_CRS,
            maxPixels=1e13,
        )
        task.start()
        print(f"  Задача {prefix}_{year} отправлена в GEE.")
        return task
    except ee.EEException as e:
        print(f"  Ошибка GEE при экспорте {prefix}_{year}: {e}")
        return None


# ----------------------------------------------------------------------
# ЧТЕНИЕ С ДИСКА (rasterio)
# ----------------------------------------------------------------------


def load_image(filepath) -> np.ndarray:
    """Загружает мультиспектральный GeoTIFF и нормализует в [0, 1].

    Возвращает массив формы (H, W, C), float32.

    Первые каналы Sentinel-2/Landsat reflectance хранятся в шкале 0..10000 и
    нормализуются в [0, 1]. Если GeoTIFF содержит только 7 Sentinel-2 bands,
    NDSI/NDWI/BSI/EVI вычисляются локально и добавляются до 11 каналов.
    Если индексы уже есть в файле, они остаются в своей естественной шкале
    (примерно -1..1), поэтому не делятся на S2_SCALE.
    """
    import rasterio

    with rasterio.open(filepath) as src:
        img = src.read()  # (C, H, W)
        img = np.moveaxis(img, 0, -1).astype(np.float32)  # (H, W, C)

    n_reflectance = min(len(config.S2_BANDS), img.shape[-1])
    img[..., :n_reflectance] = np.clip(img[..., :n_reflectance] / config.S2_SCALE, 0.0, 1.0)
    if img.shape[-1] > n_reflectance:
        img[..., n_reflectance:] = np.clip(img[..., n_reflectance:], -1.0, 1.0)
    img = np.nan_to_num(img, nan=0.0, posinf=1.0, neginf=0.0)
    if img.shape[-1] == len(config.S2_BANDS):
        img = _append_sentinel2_indices(img)
    return img


def _safe_normalized_difference(a, b, eps=1e-8):
    return (a - b) / (a + b + eps)


def _append_sentinel2_indices(img: np.ndarray) -> np.ndarray:
    """Добавляет NDSI, NDWI, BSI, EVI к нормализованному 7-band Sentinel-2."""
    b2 = img[..., config.BAND_INDEX["B2"]]
    b3 = img[..., config.BAND_INDEX["B3"]]
    b4 = img[..., config.BAND_INDEX["B4"]]
    b8 = img[..., config.BAND_INDEX["B8"]]
    b11 = img[..., config.BAND_INDEX["B11"]]

    ndsi = _safe_normalized_difference(b3, b11)
    ndwi = _safe_normalized_difference(b8, b11)
    bsi = _safe_normalized_difference(b11 + b4, b8 + b2)
    evi = 2.5 * (b8 - b4) / (b8 + 6.0 * b4 - 7.5 * b2 + 1.0 + 1e-8)

    indices = np.stack([ndsi, ndwi, bsi, evi], axis=-1).astype(np.float32)
    indices = np.clip(indices, -1.0, 1.0)
    return np.concatenate([img, indices], axis=-1).astype(np.float32)


def load_mask(filepath) -> np.ndarray:
    """Загружает бинарную маску ледника (0/1), форма (H, W), uint8."""
    import rasterio

    with rasterio.open(filepath) as src:
        mask = src.read(1)
    return mask.astype(np.uint8)


def read_raster_meta(filepath):
    """Возвращает (transform, crs, shape, pixel_area_m2) для GeoTIFF."""
    import rasterio

    with rasterio.open(filepath) as src:
        transform = src.transform
        crs = src.crs
        shape = (src.height, src.width)
        pixel_area_m2 = abs(src.res[0] * src.res[1])
    return transform, crs, shape, pixel_area_m2
