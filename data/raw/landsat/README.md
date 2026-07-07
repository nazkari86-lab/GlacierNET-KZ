# data/raw/landsat/

Сюда кладутся файлы `landsat_<year>.tif` для годов из
`src/config.py:YEARS_LANDSAT` (2000, 2003, 2005, 2008, 2010, 2013).

Получаются через `notebooks/01_data_download.ipynb` (`data_loader.get_landsat`).
Каналы переименованы в общую схему B2/B3/B4/B8/B11 и масштабированы к 0..10000,
как Sentinel-2, для совместимости с `src/data_loader.load_image`.

B8A и B12 у Landsat нет — индекс EVI считается с приближениями
(см. `data_loader.add_indices`), а классификация старых лет в
`05_temporal_analysis.ipynb` использует NDSI-пороговый метод, а не U-Net
(модель обучена на 11-канальных Sentinel-2 патчах).
