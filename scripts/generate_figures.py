#!/usr/bin/env python3
"""Генерация всех фигур для статьи GlacierNET-KZ."""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from pathlib import Path
import json

from src.config import FIGURES_DIR, RESULTS_DIR, TABLES_DIR

FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# ── Стиль ──────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.1,
})

# ═══════════════════════════════════════════════════════════════════
# FIGURE 1: Trend + Forecast to 2050
# ═══════════════════════════════════════════════════════════════════
print("[1/4] Glacier trend + forecast …")
df = pd.read_csv(RESULTS_DIR / "tables" / "glacier_areas_all_years.csv")
df["method"] = df["method"].str.upper()

# Prefer RF for full time series, NDSI for recent years
rf = df[df["method"] == "RF"][["year", "area_km2"]].copy()
ndsi = df[df["method"] == "NDSI"][["year", "area_km2"]].copy()

years = rf["year"].values
areas = rf["area_km2"].values

# Linear fit
slope, intercept = np.polyfit(years, areas, 1)
r2 = 1 - np.sum((areas - (slope * years + intercept)) ** 2) / np.sum((areas - areas.mean()) ** 2)

# Forecast 2020-2050
forecast_years = np.arange(2020, 2051)
forecast_areas = slope * forecast_years + intercept

# 95% CI (using residual SE)
residuals = areas - (slope * years + intercept)
se = np.sqrt(np.sum(residuals**2) / (len(years) - 2))
t_val = 2.0  # approximate for 95% CI
x_mean = np.mean(years)
ss_x = np.sum((years - x_mean) ** 2)
ci = t_val * se * np.sqrt(1 + 1/len(years) + (forecast_years - x_mean)**2 / ss_x)

# ── Plot ──
fig, ax = plt.subplots(figsize=(8, 4.5))

# Observed
ax.plot(years, areas, "ko-", markersize=5, linewidth=1.2, label="Observed (RF)")

# NDSI overlay
if len(ndsi) > 0:
    ax.plot(ndsi["year"], ndsi["area_km2"], "s--", color="steelblue", markersize=4,
            linewidth=1, alpha=0.8, label="Observed (NDSI)")

# Regression line (observed range)
reg_x = np.linspace(years.min(), years.max(), 50)
ax.plot(reg_x, slope * reg_x + intercept, "r--", linewidth=1, alpha=0.6,
        label=f"Linear trend (slope={slope:.2f} km²/yr, R²={r2:.2f})")

# Forecast
ax.plot(forecast_years, forecast_areas, "r-", linewidth=1.5, label="Forecast (extrapolation)")
ax.fill_between(forecast_years, forecast_areas - ci, forecast_areas + ci,
                color="red", alpha=0.12, label="95% confidence")

# 2050 annotation
ax.axhline(y=forecast_areas[-1], color="gray", linestyle=":", linewidth=0.8, alpha=0.5)
ax.annotate(f"2050: {forecast_areas[-1]:.0f} km²",
            xy=(2050, forecast_areas[-1]), xytext=(2042, forecast_areas[-1] + 40),
            arrowprops=dict(arrowstyle="->", color="gray"), fontsize=9, color="gray")

ax.set_xlabel("Year")
ax.set_ylabel("Glacier area (km²)")
ax.set_title("Glacier Area Trend and Forecast — Ili Alatau (2000–2050)")
ax.legend(loc="upper right", framealpha=0.9)
ax.set_xlim(1998, 2052)
ax.set_ylim(200, max(areas.max(), forecast_areas.max()) + 50)
ax.xaxis.set_major_locator(MaxNLocator(integer=True))
ax.grid(True, alpha=0.3)

out = FIGURES_DIR / "glacier_trend_forecast.png"
fig.savefig(out)
plt.close(fig)
print(f"  → {out}")

# ═══════════════════════════════════════════════════════════════════
# FIGURE 2: Model Comparison Bar Chart
# ═══════════════════════════════════════════════════════════════════
print("[2/4] Model comparison …")
mc = pd.read_csv(RESULTS_DIR / "tables" / "model_comparison.csv")

models = mc["model"].tolist()
metrics = ["f1", "iou", "precision", "recall"]
metric_labels = ["F1-Score", "IoU", "Precision", "Recall"]
colors = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0"]

fig, ax = plt.subplots(figsize=(7, 4))
x = np.arange(len(models))
width = 0.18

for i, (metric, label, color) in enumerate(zip(metrics, metric_labels, colors)):
    vals = [mc[mc["model"] == m][metric].values[0] for m in models]
    bars = ax.bar(x + i * width, vals, width, label=label, color=color, alpha=0.85)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                f"{v:.3f}", ha="center", va="bottom", fontsize=7)

ax.set_xticks(x + width * 1.5)
ax.set_xticklabels(
    [m.replace(" (", "\n(").replace("U-Net", "U-Net") for m in models],
    fontsize=7,
)
ax.set_ylabel("Score")
ax.set_ylim(0.70, 0.98)
ax.set_title("Model Performance Comparison on 2020 Test Set")
ax.legend(loc="lower right", ncol=4, fontsize=8)
ax.grid(axis="y", alpha=0.3)

out = FIGURES_DIR / "model_comparison.png"
fig.savefig(out)
plt.close(fig)
print(f"  → {out}")

# ═══════════════════════════════════════════════════════════════════
# FIGURE 3: Training Curves
# ═══════════════════════════════════════════════════════════════════
print("[3/4] Training curves …")
tl = pd.read_csv(RESULTS_DIR / "training_log.csv")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.5))

# Loss
ax1.plot(tl["epoch"], tl["loss"], "b-", linewidth=1.2, label="Train loss")
ax1.plot(tl["epoch"], tl["val_loss"], "r--", linewidth=1.2, label="Val loss")
ax1.set_xlabel("Epoch")
ax1.set_ylabel("Loss")
ax1.set_title("Training and Validation Loss")
ax1.legend()
ax1.grid(True, alpha=0.3)

# Dice + IoU
ax2.plot(tl["epoch"], tl["dice_coefficient"], "g-", linewidth=1.2, label="Train Dice")
ax2.plot(tl["epoch"], tl["val_dice_coefficient"], "g--", linewidth=1.2, label="Val Dice")
ax2.plot(tl["epoch"], tl["binary_io_u"], "m-", linewidth=1.2, label="Train IoU")
ax2.plot(tl["epoch"], tl["val_binary_io_u"], "m--", linewidth=1.2, label="Val IoU")
ax2.set_xlabel("Epoch")
ax2.set_ylabel("Score")
ax2.set_title("Dice Coefficient and IoU")
ax2.legend()
ax2.grid(True, alpha=0.3)

fig.suptitle("Attention U-Net Training Curves (22 epochs)", fontsize=11, y=1.02)
fig.tight_layout()

out = FIGURES_DIR / "training_curves.png"
fig.savefig(out)
plt.close(fig)
print(f"  → {out}")

# ═══════════════════════════════════════════════════════════════════
# FIGURE 4: Glacier Maps Mosaic (RF masks)
# ═══════════════════════════════════════════════════════════════════
print("[4/4] Glacier maps mosaic …")
try:
    import rasterio
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False
    print("  ⚠ rasterio not available, skipping maps mosaic")

if HAS_RASTERIO:
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(["#2d2d2d", "#00bcd4"])  # dark=non-glacier, cyan=glacier

    # Available years with RF masks (use absolute path)
    pred_dir = Path(__file__).resolve().parent.parent / "predictions"
    years_with_rf = sorted([
        int(p.parent.name) for p in pred_dir.glob("*/rf_mask.tif")
    ])

    n = len(years_with_rf)
    if n == 0:
        print("  ⚠ No rf_mask.tif in predictions/ (run predict.py --save), skipping mosaic")
    else:
        cols = 4
        rows = (n + cols - 1) // cols
        fig, axes = plt.subplots(rows, cols, figsize=(12, rows * 3))
        if rows == 1:
            axes = np.array([axes])
        axes = axes.flatten()

        for i, year in enumerate(years_with_rf):
            path = pred_dir / str(year) / "rf_mask.tif"
            with rasterio.open(path) as src:
                mask = src.read(1)
            ax = axes[i]
            ax.imshow(mask, cmap=cmap, vmin=0, vmax=1)
            ax.set_title(str(year), fontsize=10, fontweight="bold")
            ax.axis("off")

        for j in range(n, len(axes)):
            axes[j].axis("off")

        fig.suptitle("Glacier Classification Maps (Random Forest) — Ili Alatau", fontsize=12, y=0.98)
        fig.tight_layout(rect=[0, 0, 1, 0.96])

        out = FIGURES_DIR / "glacier_maps_by_year.png"
        fig.savefig(out, facecolor="white")
        plt.close(fig)
        print(f"  → {out}")

print("\n✅ All figures saved to:", FIGURES_DIR)
