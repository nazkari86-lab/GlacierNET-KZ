# Обзор литературы — GlacierNET-KZ

Скомпилировано из исследовательской базы проекта. Используется для
раздела "Обзор литературы" научной работы и технической документации проекта.

---

## 1. Обязательные источники (читать первыми)

| Источник | Год | Что взять |
|---|---|---|
| Maslov et al., *Globally Scalable Glacier Mapping by Deep Learning Matches Expert Delineation Accuracy*, Nature Communications, DOI 10.1038/s41467-024-54956-x | 2025 | SOTA-модель GlaViTU (CNN+Transformer), IoU>0.85 глобально. Использовать как сравнение SOTA vs локальная U-Net. Код: github.com/konstantin-a-maslov/towards_global_glacier_mapping |
| Bolch, *Climate Change and Glacier Retreat in Northern Tien Shan (Kazakhstan/Kyrgyzstan) Using Remote Sensing Data*, Global and Planetary Change, DOI 10.1016/j.gloplacha.2006.07.009 | 2007 | Историческая точка отсчёта: 0.757%/год (1955–2008). Сравнить с нашим темпом 2015–2024. |
| Shahgedanova et al., *Assessment of Changes in Mass Balance of the Tuyuksu Group of Glaciers...*, Frontiers in Earth Science, DOI 10.3389/feart.2020.00259 | 2020 | Ground-truth по Туюксу 1958–2016, контакт с КазНУ. |
| *Satellite Based Deep Learning Approaches for Detecting Environmental Disasters Across Kazakhstan*, Discover Applied Sciences, Springer, DOI 10.1007/s42452-025-08133-4 | 2025 | Прямая цитата о научном пробеле — ключевая для обоснования новизны. |
| *Measuring Glacier Changes in the Tianshan Mountains Over the Past 20 Years Using Google Earth Engine and Machine Learning*, Journal of Geographical Sciences, DOI 10.1007/s11442-023-2160-4 | 2023 | Прямой baseline: Random Forest, темп ускорился 0.87%/год -> 1.49%/год. |
| *Multi-Sensor Deep Learning for Glacier Mapping* (обзор), arXiv:2409.12034 | 2024 | Мегаобзор методов, датасетов, сравнение архитектур. |

---

## 2. Дополнительные источники

| Источник | Год | Назначение |
|---|---|---|
| Baraka, Akera, Aryal, Bengio et al., *Machine Learning for Glacier Monitoring in the Hindu Kush Himalaya*, NeurIPS 2020 CCAI Workshop, arXiv:2012.05013 | 2020 | Методология U-Net + открытый датасет HKH (7095 патчей 512x512). github.com/krisrs1128/glacier_mapping |
| Robbins, Breininger, Jiang et al., *Segmentation of Glacier Area Using U-Net through Landsat Satellite Imagery...*, J. Marine Sci. Eng., DOI 10.3390/jmse12101788 | 2024 | Методология перевода площади пикселей в км², мультивременной анализ. |
| Peng et al., *Spatiotemporal Reconstruction of Annual Glacier Mass Balance in Central Asia (2000–2020) Using Machine Learning*, JGR Atmospheres, DOI 10.1029/2024JD043191 | 2025 | XGBoost baseline, ERA5 признаки, контакт Central-Asian Regional Glaciological Centre (Алматы). |
| *Glacier Change Threatens Central Asia's Water Towers*, PMC | 2024-2025 | Цифры для введения (см. ниже). |
| *Semantic Segmentation of Glaciological Features... with SAM*, J. Glaciology | 2023 | SAM zero-shot baseline (опционально, идея B). |
| Bolibar, Rabatel et al., *Nonlinear Sensitivity of Glacier Mass Balance to Future Climate Change Unveiled by Deep Learning*, Nature Communications, DOI 10.1038/s41467-022-28033-0 | 2022 | Методология прогноза до 2100 (адаптировать до 2050). |

---

## 3. Датасеты

- **RGI 7.0** (NSIDC, DOI 10.5067/F6JMOVY5NAVZ) — контуры ледников, регион 13 (Central Asia). Ground-truth маски.
- **WGMS Fluctuations of Glaciers DB — Tuyuksu** (wgms.ch/products_ref_glaciers/tuyuksuyskiy) — данные с 1957 г., независимая валидация.
- **GlaViTU Benchmark Dataset** (Maslov et al. 2025) — глобальный, включает Центральную Азию, для transfer learning.
- **HKH Glacier Mapping Dataset** (Baraka et al.) — 7095 патчей Landsat 7, для предобучения.
- **Copernicus Sentinel-2 L2A** (`COPERNICUS/S2_SR_HARMONIZED` в GEE) — основные данные, 10м/пиксель.
- **ERA5** (Copernicus C3S) — климатические признаки (опционально).

---

## 4. Ключевые цифры для введения

- Казахстан потерял **~17%** площади ледников за последние 50 лет (UNEP/UN).
- Ледники Заилийского Алатау потеряли **49%** объёма с середины XX века.
- **97.52%** ледников Тянь-Шаня демонстрируют отступание.
- Скорость таяния в Тянь-Шане в **4 раза** выше среднемирового показателя.
- Ледники дают **80%** речного стока Центральной Азии; от него зависят **80 млн человек**.
- Площадь ледников Восточного Тянь-Шаня: -10.59% (1990–2000), -12.80% (2000–2015).
- Темп отступания Северного Тянь-Шаня ускорился с **0.87%/год до 1.49%/год** (Springer 2023).
- Темп отступания (Bolch 2007): 0.757%/год средний за 1955–2008.

---

## 5. Научные пробелы / ниша проекта

1. Нет специализированной DL-модели для ледников Казахстана (Тянь-Шань + Джунгарский Алатау), валидированной на полевых данных.
2. Нет количественного сравнения ML-предсказаний площади с данными WGMS Туюксу.
3. Нет мультитемпорального DL-анализа 2015–2024 для конкретных казахстанских ледников (существующие работы — максимум до 2020).
4. Нет сравнения GlaViTU (глобальная SOTA) vs локально обученная модель на данных Казахстана.
5. Нет прогноза до 2050 для конкретных ледников Заилийского Алатау с привязкой к водоснабжению Алматы.

---

## 6. Ограничения методов (для раздела "Обсуждение")

1. Нет специализированных моделей для ледников Казахстана (GlaViTU — глобальная).
2. Debris-covered glaciers: IoU < 0.75 у всех существующих методов.
3. Облачность Sentinel-2 в горах > 80% зимой -> решение: летние медианные композиты (июль-сентябрь).
4. Смешанные пиксели на границах ледника (10м/пиксель) -> систематическая ошибка.
5. Малый обучающий датасет в Казахстане -> transfer learning от GlaViTU/HKH + аугментация.
6. Временное смещение: маски RGI ~2000 г. vs снимки других лет.

---

## 7. Типичные ошибки (чек-лист для самопроверки)

- [ ] Строгое разделение train/val/test, метрики только на test
- [ ] Сравнение минимум с 2-3 методами (NDSI + RF + U-Net, желательно + GlaViTU/SAM)
- [ ] Class imbalance учтён (Dice/Focal loss, class_weight)
- [ ] Площадь в км², не в пикселях
- [ ] p-value для тренда указан
- [ ] Cloud masking упомянут как этап предобработки
- [ ] Прогноз с доверительным интервалом (95% CI)

---

## 8. Структура научной работы

См. `paper/draft_outline.md`.
