# WGMS-валидация (ледник Туюксу)

Независимая проверка спутниковых оценок площади против наземных измерений
[WGMS Fluctuations of Glaciers](https://wgms.ch/) для reference glacier **Горный Туюксу**.

## Зачем отдельная подготовка

- Полная база FoG (~868 МБ) **не скачивается через API** — только ручная загрузка по DOI.
- Наш пайплайн (`05_temporal_analysis.ipynb`) считает площадь **всего bbox** Заилийского Алатау (~450 км²),
  тогда как WGMS отслеживает **отдельный ледник** Туюксу (~2.3 км²).
- Функция `src/metrics.rmse_against_wgms()` готова; нужны два словаря `year → area_km2` в одних единицах.

## Шаг 1 — Скачать данные WGMS

1. Перейти на [WGMS FoG download](https://doi.org/10.5904/wgms-fog-2026-02-10) (актуальная версия FoG).
2. Скачать архив (~868 МБ), распаковать локально.
3. Найти CSV с измерениями (имя файла зависит от версии FoG, обычно `*_measurements*.csv`).

**Быстрая альтернатива (без полной базы):**

- [FoG Browser — Tuyuksuyskiy](https://wgms.ch/products_ref_glaciers/tuyuksuyskiy/) → Download Data → CSV.

## Шаг 2 — Подготовить файлы проекта

Из корня репозитория:

```bash
# Из полного архива FoG
python scripts/wgms_setup.py --fog-csv /path/to/fog_measurements.csv

# Или из экспорта браузера
python scripts/wgms_setup.py --manual-csv /path/to/tuyuksu_export.csv

# Шаблон для ручного заполнения
python scripts/wgms_setup.py --template
```

Результат:

| Файл | Назначение |
|------|------------|
| `data/wgms/tuyuksu_areas.csv` | Таблица year, area_km2 |
| `data/wgms/tuyuksu_areas.json` | Словарь для notebook 05 |

WGMS ID Туюксу: **817** (также встречается 11160 в methodology.md).

## Шаг 3 — Интеграция в `05_temporal_analysis.ipynb`

Замените пустой словарь в ячейке «WGMS-валидация»:

```python
import json
from pathlib import Path
from src import config, metrics

wgms_path = config.PROJECT_ROOT / "data" / "wgms" / "tuyuksu_areas.json"
if wgms_path.exists():
    wgms_areas_km2 = {int(k): v for k, v in json.loads(wgms_path.read_text()).items()}
else:
    wgms_areas_km2 = {}

# predicted_areas_km2 — площади Туюксу из ваших масок (не весь bbox!)
# См. config.GLACIERS["tuyuksu"] для координат / RGI ID RGI2000-v7.0-G-13-33843
predicted_areas_km2 = {
    # 2016: 2.40,
    # 2020: 2.28,
}

if wgms_areas_km2 and predicted_areas_km2:
    rmse, common_years, diffs = metrics.rmse_against_wgms(predicted_areas_km2, wgms_areas_km2)
    print(f"RMSE против WGMS ({len(common_years)} лет): {rmse:.4f} km²")
```

### Субдискретизация до Туюксу

Предсказания из notebook 05 по умолчанию — **вся область исследования**. Для корректного RMSE:

1. Обрезать маску по полигону RGI Туюксу (`data/rgi/`, ID `RGI2000-v7.0-G-13-33843`), или
2. Использовать bbox вокруг `config.GLACIERS["tuyuksu"]` (lon 77.0784, lat 43.0506).

## Шаг 4 — Визуализация и статья

После расчёта RMSE:

- Сохранить график сравнения в `results/figures/wgms_validation.png`
- Заполнить раздел **4.6 WGMS-валидация** в `paper/draft_outline.md`

Критерии приёмки (из `docs/GITHUB_ISSUES.md`):

- RMSE < 0.5 km² для пересекающихся лет
- Bias < 10% от средней площади ледника
- Документировано в статье

## Ссылки

- `src/metrics.py` — `rmse_against_wgms()`
- `scripts/wgms_setup.py` — парсинг CSV и генерация JSON
- `docs/contacts_and_partnerships.md` — контакт WGMS
- Khromova et al. (2019) — опубликованный ряд площадей Туюксу (fallback без FoG)
