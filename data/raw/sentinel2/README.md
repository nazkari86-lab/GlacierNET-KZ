# data/raw/sentinel2/

Сюда кладутся файлы `sentinel2_<year>.tif` (например, `sentinel2_2024.tif`)
для годов из `src/config.py:YEARS_SENTINEL2` (2015–2024).

Получаются через `notebooks/01_data_download.ipynb` или
`scripts/download_all_missing.py`:
1. Экспорт в Google Drive (папка `GlacierKZ`).
2. Скачивание `.tif` файлов из Drive в эту папку.

Допустимы два формата:
- 7-канальный compact GeoTIFF: `B2,B3,B4,B8,B8A,B11,B12`;
- 11-канальный GeoTIFF: `B2,B3,B4,B8,B8A,B11,B12,NDSI,NDWI,BSI,EVI`.

`src.data_loader.load_image()` приводит оба формата к 11 каналам: для compact
файлов NDSI/NDWI/BSI/EVI вычисляются локально.

Все файлы должны иметь CRS=`EPSG:32642`, 10 м/пиксель и быть обрезаны по
`STUDY_AREA_BBOX`.

Примечание: `sentinel2_2015.tif`, если присутствует, является fallback
композитом Sentinel-2 TOA за доступные сцены конца 2015 года. Летних L2A/SR
сцен 2015 для текущего bbox в GEE нет.
