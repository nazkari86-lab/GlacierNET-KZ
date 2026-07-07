# data/rgi/

Контуры ледников (ground-truth маски). Источники:

1. **RGI 7.0, регион 13 (Central Asia)** — https://www.glims.org/RGI/rgi70_dl.html
   (NSIDC, DOI 10.5067/F6JMOVY5NAVZ, CC BY 4.0)
2. Либо экспорт из `notebooks/01_data_download.ipynb` через
   `ee.FeatureCollection('GLIMS/current')`, сохранённый как
   `rgi_study_area.shp` (+ .dbf, .shx, .prj).

Ожидаемое имя файла для `02_preprocessing.ipynb`: `rgi_study_area.shp`.

После загрузки откройте shapefile в QGIS, сверьте контуры с актуальными
снимками 2024 г. (особенно для ледника Туюксу) и при необходимости
скорректируйте границы вручную (Layer -> Toggle Editing -> Vertex Tool).
