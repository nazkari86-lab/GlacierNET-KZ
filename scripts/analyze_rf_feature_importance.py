#!/usr/bin/env python3
"""Export Random Forest feature importance from the trained local baseline."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402


def build_feature_rows(feature_names: list[str], importances) -> list[dict[str, float | int | str]]:
    if len(feature_names) != len(importances):
        raise ValueError(
            f"Feature-name count ({len(feature_names)}) does not match importance count ({len(importances)})"
        )
    ordered = sorted(zip(feature_names, importances), key=lambda item: float(item[1]), reverse=True)
    return [
        {
            "rank": rank,
            "feature": name,
            "importance": float(importance),
            "importance_percent": float(importance) * 100.0,
        }
        for rank, (name, importance) in enumerate(ordered, start=1)
    ]


def save_plot(rows: list[dict[str, float | int | str]], output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = [str(row["feature"]) for row in rows][::-1]
    values = [float(row["importance_percent"]) for row in rows][::-1]
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.barh(names, values, color="#0f766e")
    ax.set_xlabel("Permutation-free tree importance (%)")
    ax.set_title("Random Forest feature importance")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=config.MODELS_DIR / "random_forest.pkl")
    parser.add_argument("--table", type=Path, default=config.TABLES_DIR / "random_forest_feature_importance.csv")
    parser.add_argument("--figure", type=Path, default=config.FIGURES_DIR / "random_forest_feature_importance.png")
    parser.add_argument("--summary", type=Path, default=config.RESULTS_DIR / "random_forest_feature_importance.json")
    args = parser.parse_args()

    import joblib

    model_path = args.model.resolve()
    if not model_path.exists():
        raise FileNotFoundError(f"Missing Random Forest model: {model_path}")
    model = joblib.load(model_path)
    if not hasattr(model, "feature_importances_"):
        raise TypeError(f"Model has no feature_importances_: {type(model).__name__}")

    rows = build_feature_rows(config.ALL_BAND_NAMES, model.feature_importances_)
    args.table.parent.mkdir(parents=True, exist_ok=True)
    with args.table.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["rank", "feature", "importance", "importance_percent"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    args.figure.parent.mkdir(parents=True, exist_ok=True)
    save_plot(rows, args.figure)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model_file": str(model_path.relative_to(ROOT)),
        "n_features": len(rows),
        "top_feature": rows[0],
        "table": str(args.table.resolve().relative_to(ROOT)),
        "figure": str(args.figure.resolve().relative_to(ROOT)),
        "caveat": "Impurity-based importance is descriptive for this trained baseline and is not causal evidence.",
    }
    args.summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {args.table}")
    print(f"Wrote {args.figure}")
    print(f"Top feature: {rows[0]['feature']} ({rows[0]['importance_percent']:.2f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
