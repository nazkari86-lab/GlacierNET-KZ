#!/usr/bin/env python3
"""Подготовка данных WGMS FoG для валидации ледника Туюксу.

WGMS Fluctuations of Glaciers (FoG) не доступен через публичный API — базу
нужно скачать вручную (~868 МБ) и распаковать локально.

Шаги:
  1. Скачать FoG: https://doi.org/10.5904/wgms-fog-2026-02-10
  2. Распаковать архив (CSV внутри, структура зависит от версии FoG)
  3. Запустить этот скрипт с путём к CSV или использовать шаблон вручную

Выход:
  - ``data/wgms/tuyuksu_areas.csv`` — year, area_km2
  - ``data/wgms/tuyuksu_areas.json`` — словарь для ``notebooks/05_temporal_analysis.ipynb``

Интеграция в notebook 05:
  ```python
  import json
  from pathlib import Path
  wgms_path = Path("../data/wgms/tuyuksu_areas.json")
  wgms_areas_km2 = json.loads(wgms_path.read_text()) if wgms_path.exists() else {}
  wgms_areas_km2 = {int(k): v for k, v in wgms_areas_km2.items()}
  ```

Альтернатива без полной базы FoG:
  - FoG Browser → Tuyuksu: https://wgms.ch/products_ref_glaciers/tuyuksuyskiy/
  - Экспорт CSV → ``python scripts/wgms_setup.py --manual-csv path/to/export.csv``
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_WGMS = ROOT / "data" / "wgms"
OUTPUT_CSV = DATA_WGMS / "tuyuksu_areas.csv"
OUTPUT_JSON = DATA_WGMS / "tuyuksu_areas.json"

# WGMS reference glacier IDs (см. docs/GITHUB_ISSUES.md, paper/methodology.md)
TUYUKSU_WGMS_IDS = {"817", "11160", "33843"}
TUYUKSU_NAME_FRAGMENTS = ("tuyuksu", "tuyuksuyskiy", "туюксу")


def _normalize_year(value: str) -> int | None:
    value = value.strip()
    if not value:
        return None
    try:
        y = int(float(value))
    except ValueError:
        return None
    if 1900 <= y <= 2100:
        return y
    return None


def _normalize_area(value: str) -> float | None:
    value = value.strip().replace(",", ".")
    if not value:
        return None
    try:
        area = float(value)
    except ValueError:
        return None
    if area <= 0:
        return None
    # WGMS FoG state.csv stores area in m²; convert to km²
    if area > 100:
        area /= 1_000_000.0
    return area


def _year_from_date(value: str) -> int | None:
    value = value.strip()
    if len(value) >= 4 and value[:4].isdigit():
        return _normalize_year(value[:4])
    return None


def _row_matches_tuyuksu(row: dict[str, str], id_columns: list[str], name_columns: list[str]) -> bool:
    for col in id_columns:
        val = row.get(col, "").strip()
        if val in TUYUKSU_WGMS_IDS:
            return True
    blob = " ".join(row.get(c, "") for c in name_columns).lower()
    return any(fragment in blob for fragment in TUYUKSU_NAME_FRAGMENTS)


def parse_fog_csv(path: Path) -> dict[int, float]:
    """Извлекает год → площадь (км²) для Туюксу из CSV FoG или экспорта браузера."""
    areas: dict[int, float] = {}
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"Пустой CSV: {path}")

        fields = [c.lower() for c in reader.fieldnames]
        field_map = {c.lower(): c for c in reader.fieldnames}

        id_cols = [field_map[f] for f in fields if f in ("glacier_id", "wgms_id")]
        if not id_cols:
            id_cols = [field_map[f] for f in fields if "glacier" in f and "id" in f]
        name_cols = [field_map[f] for f in fields if "name" in f and "glacier" in f]
        if not name_cols:
            name_cols = [field_map[f] for f in fields if f == "glacier_name"]
        year_cols = [field_map[f] for f in fields if f in ("year", "survey_year", "reference_year", "start_year", "date")]
        area_cols = [
            field_map[f]
            for f in fields
            if f == "area" or ("area" in f and ("km" in f or f.endswith("_km2") or "square" in f))
        ]
        if not area_cols:
            area_cols = [field_map[f] for f in fields if "area" in f and "unc" not in f]

        for row in reader:
            row_l = {k.lower(): v for k, v in row.items()}
            if id_cols or name_cols:
                if not _row_matches_tuyuksu(row_l, [c.lower() for c in id_cols], [c.lower() for c in name_cols]):
                    continue

            year = None
            for col in year_cols:
                raw = row.get(col, "")
                year = _year_from_date(raw) if col.lower() == "date" else _normalize_year(raw)
                if year:
                    break
            if year is None:
                for col in row:
                    if "year" in col.lower():
                        year = _normalize_year(row[col])
                        if year:
                            break
            if year is None:
                continue

            area = None
            for col in area_cols:
                area = _normalize_area(row.get(col, ""))
                if area:
                    break
            if area is None:
                continue

            areas[year] = area

    return areas


def write_outputs(areas: dict[int, float]) -> None:
    DATA_WGMS.mkdir(parents=True, exist_ok=True)
    sorted_items = sorted(areas.items())

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["year", "area_km2", "glacier", "wgms_id", "source"])
        for year, area in sorted_items:
            writer.writerow([year, f"{area:.4f}", "Tuyuksu", "817", "WGMS FoG"])

    OUTPUT_JSON.write_text(json.dumps({str(y): a for y, a in sorted_items}, indent=2), encoding="utf-8")
    print(f"Записано {len(sorted_items)} лет → {OUTPUT_CSV}")
    print(f"JSON для notebook 05 → {OUTPUT_JSON}")


def print_integration_hint() -> None:
    print(
        """
Дальше в notebooks/05_temporal_analysis.ipynb (ячейка WGMS):

    import json
    from pathlib import Path
    from src import metrics

    wgms_path = Path("../data/wgms/tuyuksu_areas.json")
    wgms_areas_km2 = {int(k): v for k, v in json.loads(wgms_path.read_text()).items()}

    # Площади U-Net/RF для Туюксу — субдискретизация маски по bbox config.GLACIERS["tuyuksu"]
    # predicted_areas_km2 = {...}  # год → км² только для ледника Туюксу

    rmse, years, diffs = metrics.rmse_against_wgms(predicted_areas_km2, wgms_areas_km2)
    print(f"RMSE: {rmse:.3f} km² over {len(years)} years")

Полная инструкция: docs/wgms_validation.md
"""
    )


def write_template() -> None:
    """Минимальный шаблон для ручного заполнения из FoG Browser."""
    template = {
        "2016": 2.35,
        "2017": 2.33,
        "2018": 2.32,
        "2019": 2.31,
        "2020": 2.30,
    }
    DATA_WGMS.mkdir(parents=True, exist_ok=True)
    tpl_path = DATA_WGMS / "tuyuksu_areas.template.json"
    tpl_path.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
    readme = DATA_WGMS / "README.txt"
    readme.write_text(
        "Замените значения в tuyuksu_areas.template.json данными с wgms.ch\n"
        "и сохраните как tuyuksu_areas.json\n",
        encoding="utf-8",
    )
    print(f"Шаблон (значения-примеры!) → {tpl_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Подготовка WGMS данных для Туюксу")
    parser.add_argument("--fog-csv", type=Path, help="Путь к CSV из архива WGMS FoG")
    parser.add_argument("--manual-csv", type=Path, help="Экспорт из FoG Browser (year, area_km2)")
    parser.add_argument("--template", action="store_true", help="Создать tuyuksu_areas.template.json")
    args = parser.parse_args()

    if args.template:
        write_template()
        print_integration_hint()
        return

    source = args.fog_csv or args.manual_csv
    if not source:
        print(__doc__)
        print("\nИспользование:")
        print("  python scripts/wgms_setup.py --fog-csv /path/to/fog_measurements.csv")
        print("  python scripts/wgms_setup.py --manual-csv /path/to/tuyuksu_export.csv")
        print("  python scripts/wgms_setup.py --template")
        print("\nFoG download: https://doi.org/10.5904/wgms-fog-2026-02-10")
        sys.exit(0)

    if not source.exists():
        print(f"Файл не найден: {source}", file=sys.stderr)
        sys.exit(1)

    areas = parse_fog_csv(source)
    if not areas:
        print(
            "Не удалось извлечь площади Туюксу. Проверьте колонки CSV "
            "(year, area_km2, glacier_id/name) или используйте --manual-csv с экспортом браузера.",
            file=sys.stderr,
        )
        sys.exit(1)

    write_outputs(areas)
    print_integration_hint()


if __name__ == "__main__":
    main()
