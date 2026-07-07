"""
Центральная конфигурация проекта GlacierNET-KZ.

Все остальные модули и ноутбуки импортируют константы отсюда, чтобы
не дублировать настройки (область интереса, годы, каналы, индексы).
"""

from pathlib import Path

# ----------------------------------------------------------------------
# ПУТИ
# ----------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_RAW_SENTINEL2 = PROJECT_ROOT / "data" / "raw" / "sentinel2"
DATA_RAW_LANDSAT = PROJECT_ROOT / "data" / "raw" / "landsat"
DATA_RGI = PROJECT_ROOT / "data" / "rgi"
DATA_MASKS = PROJECT_ROOT / "data" / "processed" / "masks"
DATA_PATCHES = PROJECT_ROOT / "data" / "processed" / "patches"

MODELS_DIR = PROJECT_ROOT / "models"
RESULTS_DIR = PROJECT_ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
TABLES_DIR = RESULTS_DIR / "tables"
MASKS_PRED_DIR = RESULTS_DIR / "masks"

# ----------------------------------------------------------------------
# ОБЛАСТЬ ИССЛЕДОВАНИЯ
# ----------------------------------------------------------------------
# Заилийский Алатау, бассейн рек Малая и Большая Алматинка.
# Покрывает ледники Туюксу, Богдановича, Тогузак, Городецкого и др.
STUDY_AREA_BBOX = (76.5, 42.8, 77.5, 43.2)  # (min_lon, min_lat, max_lon, max_lat)

# Координаты целевых ледников (центроиды, для справки/QGIS).
GLACIERS = {
    "tuyuksu": {
        "name_en": "Tuyuksu Glacier",
        "name_ru": "Горный Туюксу",
        "range": "Заилийский Алатау",
        "lon": 77.0784,
        "lat": 43.0506,
        "rgi_id": "RGI2000-v7.0-G-13-33843",
        "priority": 1,
        "notes": "WGMS reference glacier, наблюдения с 1957 г.",
    },
    "bogdanovich": {
        "name_en": "Bogdanovich Glacier",
        "name_ru": "Богдановича",
        "range": "Заилийский Алатау",
        "lon": 77.0539,
        "lat": 43.0394,
        "rgi_id": "RGI2000-v7.0-G-13-33845",
        "priority": 2,
        "notes": "Крупный ледник, хорошо изучен",
    },
    # Mutny glacier: EXCLUDED until RGI 7.0 coordinates are confirmed.
    # Do NOT use in analysis — produces wrong masks.
    # To add: look up RGI 7.0 region 13 (Central Asia) for "Mutny" or "Мутный"
    # and set lon/lat + rgi_id from the official dataset.
    # "mutny": {
    #     "name_en": "Mutny Glacier",
    #     "name_ru": "Мутный",
    #     "range": "Джунгарский Алатау",
    #     "lon": ???,   # NEEDS RGI 7.0 lookup
    #     "lat": ???,
    #     "rgi_id": None,
    #     "priority": 3,
    # },
}

# ----------------------------------------------------------------------
# ВРЕМЕННЫЕ РЯДЫ
# ----------------------------------------------------------------------
YEARS_SENTINEL2 = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]
YEARS_LANDSAT = [2000, 2003, 2005, 2008, 2010, 2013]

SUMMER_START_MONTH_DAY = "07-01"
SUMMER_END_MONTH_DAY = "09-30"

# ----------------------------------------------------------------------
# СПЕКТРАЛЬНЫЕ КАНАЛЫ И ИНДЕКСЫ
# ----------------------------------------------------------------------
# Порядок каналов фиксирован во всём пайплайне (GEE export -> rasterio -> модель).
S2_BANDS = ["B2", "B3", "B4", "B8", "B8A", "B11", "B12"]
INDEX_NAMES = ["NDSI", "NDWI", "BSI", "EVI"]
ALL_BAND_NAMES = S2_BANDS + INDEX_NAMES  # 11 каналов всего

# Индексы (0-based) внутри ALL_BAND_NAMES, чтобы избежать ошибок
BAND_INDEX = {name: i for i, name in enumerate(ALL_BAND_NAMES)}
N_CHANNELS = len(ALL_BAND_NAMES)

# Для визуализации RGB (B4=red, B3=green, B2=blue)
RGB_INDICES = [BAND_INDEX["B4"], BAND_INDEX["B3"], BAND_INDEX["B2"]]

# Спутниковые значения отражения Sentinel-2 SR: 0..~10000 (uint16) -> [0, 1]
S2_SCALE = 10000.0

# CRS для экспорта (UTM зона 42N покрывает Заилийский и Джунгарский Алатау)
EXPORT_CRS = "EPSG:32642"
EXPORT_SCALE_M = 10  # метров/пиксель

# ----------------------------------------------------------------------
# ПАТЧИ
# ----------------------------------------------------------------------
PATCH_SIZE = 256
PATCH_STRIDE = 128
MIN_GLACIER_FRACTION = 0.01  # патч с ледником сохраняется, если доля пикселей > 1%
BACKGROUND_KEEP_PROB = 0.30  # вероятность сохранить "пустой" патч (для баланса фона)

RANDOM_SEED = 42

# ----------------------------------------------------------------------
# ОБУЧЕНИЕ
# ----------------------------------------------------------------------
TRAIN_FRACTION = 0.70
VAL_FRACTION = 0.15
TEST_FRACTION = 0.15

UNET_FILTERS = [32, 64, 128, 256]
BATCH_SIZE = 8
EPOCHS = 100
LEARNING_RATE = 1e-4

# Архитектура модели: 'unet' | 'attention_unet' | 'unet_plus_plus'
# Единственный управляющий параметр — USE_ATTENTION и отдельный флаг удалены.
MODEL_NAME: str = "attention_unet"
USE_DEEP_SUPERVISION = False  # пока отключено — упрощает загрузку модели

# Снижение LR при плато
LR_PATIENCE = 8
LR_FACTOR = 0.5
MIN_LR = 1e-6

# Early stopping
EARLY_STOP_PATIENCE = 15

# Focal Loss (альтернатива BCE+Dice)
FOCAL_LOSS_ALPHA = 0.25
FOCAL_LOSS_GAMMA = 2.0

# TTA (Test Time Augmentation)
TTA_ENABLED = True
TTA_FLIP_LR = True
TTA_FLIP_UD = True

# Ensemble
ENSEMBLE_NDSI = True
ENSEMBLE_RF = True

# CRF post-processing
CRF_ENABLED = False  # требует pydensecrf
CRF_ITERATIONS = 10
CRF_POS_XY_STD = 3
CRF_BI_XY_STD = 80
CRF_BI_RGB_STD = 13

NDSI_THRESHOLDS = [0.3, 0.4, 0.5, 0.6]
BEST_NDSI_THRESHOLD = 0.4  # обновляется по результатам 03_baseline_models


# ----------------------------------------------------------------------
# ВАЛИДАЦИЯ
# ----------------------------------------------------------------------


_VALID_MODEL_NAMES = {"unet", "attention_unet", "unet_plus_plus"}


def validate_config() -> list[str]:
    """Проверяет консистентность значений и возвращает список ошибок.

    Вызывать в начале ``train.py`` или ``03_baseline_models.ipynb``.

    Возвращает
    ----------
    list[str]
        Список описаний ошибок. Пустой список = всё корректно.
    """
    errors: list[str] = []

    if MODEL_NAME is not None and MODEL_NAME not in _VALID_MODEL_NAMES:
        errors.append(f"MODEL_NAME={MODEL_NAME!r} не найден. Доступные: {sorted(_VALID_MODEL_NAMES)}")

    splits_sum = TRAIN_FRACTION + VAL_FRACTION + TEST_FRACTION
    if abs(splits_sum - 1.0) > 1e-6:
        errors.append(f"Сумма долей выборок = {splits_sum}, ожидается 1.0")

    if BATCH_SIZE < 1:
        errors.append(f"BATCH_SIZE={BATCH_SIZE}, ожидается >= 1")

    if EPOCHS < 1:
        errors.append(f"EPOCHS={EPOCHS}, ожидается >= 1")

    if LEARNING_RATE <= 0 or LEARNING_RATE > 1:
        errors.append(f"LEARNING_RATE={LEARNING_RATE}, ожидается (0, 1]")

    if PATCH_SIZE < 32:
        errors.append(f"PATCH_SIZE={PATCH_SIZE}, ожидается >= 32")

    if not UNET_FILTERS or not all(f > 0 for f in UNET_FILTERS):
        errors.append(f"UNET_FILTERS={UNET_FILTERS}, ожидается список положительных int")

    if N_CHANNELS != len(ALL_BAND_NAMES):
        errors.append(f"N_CHANNELS={N_CHANNELS} != len(ALL_BAND_NAMES)={len(ALL_BAND_NAMES)}")

    for year_list, label in [
        (YEARS_SENTINEL2, "YEARS_SENTINEL2"),
        (YEARS_LANDSAT, "YEARS_LANDSAT"),
    ]:
        if not isinstance(year_list, list) or not all(isinstance(y, int) and 1990 <= y <= 2100 for y in year_list):
            errors.append(f"{label} содержит некорректные значения: {year_list}")

    return errors
