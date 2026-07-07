"""
Графики и карты: RGB-композиты, маски, обучение, временной ряд и прогноз.
"""

from __future__ import annotations

import numpy as np

from . import config


def show_rgb(image: np.ndarray, ax=None, brightness: float = 3.0, title: str | None = None):
    """Отображает RGB-композит (B4, B3, B2) с усилением яркости."""
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots()

    rgb = image[:, :, config.RGB_INDICES]
    rgb = np.clip(rgb * brightness, 0, 1)
    ax.imshow(rgb)
    ax.axis("off")
    if title:
        ax.set_title(title)
    return ax


def show_mask(mask: np.ndarray, ax=None, title: str | None = None, cmap: str = "Blues"):
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots()

    ax.imshow(mask, cmap=cmap, vmin=0, vmax=1)
    ax.axis("off")
    if title:
        ax.set_title(title)
    return ax


def plot_training_curves(history, save_path=None):
    """Кривые loss и Dice coefficient (train/val)."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].plot(history.history["loss"], label="Train Loss")
    axes[0].plot(history.history["val_loss"], label="Val Loss")
    axes[0].set_title("Функция потерь")
    axes[0].set_xlabel("Эпоха")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(history.history["dice_coefficient"], label="Train Dice")
    axes[1].plot(history.history["val_dice_coefficient"], label="Val Dice")
    axes[1].set_title("Dice Coefficient")
    axes[1].set_xlabel("Эпоха")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150)
    return fig


def plot_prediction_grid(X, y_true, y_pred, n_examples=4, save_path=None, rng=None):
    """3xN сетка: снимок / истинная маска / предсказание."""
    import matplotlib.pyplot as plt

    if rng is None:
        rng = np.random.default_rng(config.RANDOM_SEED)

    fig, axes = plt.subplots(3, n_examples, figsize=(4 * n_examples, 12))
    if n_examples == 1:
        axes = axes.reshape(3, 1)

    for col in range(n_examples):
        idx = int(rng.integers(0, len(X)))
        show_rgb(X[idx], ax=axes[0, col], title=f"Снимок #{idx}")
        show_mask(y_true[idx], ax=axes[1, col], title="Истинная маска")
        show_mask(y_pred[idx], ax=axes[2, col], title="Предсказание U-Net")

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150)
    return fig


def plot_trend_forecast(
    years,
    areas,
    future_years,
    predicted,
    ci_lower,
    ci_upper,
    title="Изменение площади ледников Казахстана",
    save_path=None,
):
    """Финальный график: исторические данные + тренд + прогноз до 2050 с CI."""
    import matplotlib.pyplot as plt

    years = np.asarray(years, dtype=float)
    areas = np.asarray(areas, dtype=float)

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.scatter(years, areas, color="#1a6fad", s=80, zorder=5, label="Измеренная площадь (U-Net)")

    from scipy import stats

    slope, intercept, *_ = stats.linregress(years, areas)
    x_hist = np.linspace(years.min(), years.max(), 100)
    y_hist = slope * x_hist + intercept
    ax.plot(x_hist, y_hist, "--", color="#1a6fad", alpha=0.6, linewidth=1.5)

    ax.plot(future_years, predicted, "-", color="#d94f3c", linewidth=2, label="Прогноз")
    ax.fill_between(future_years, ci_lower, ci_upper, alpha=0.15, color="#d94f3c", label="95% доверительный интервал")

    last_year, last_area = years[-1], areas[-1]
    target_idx = -1
    ax.annotate(
        f"{last_area:.1f} км² ({int(last_year)})",
        xy=(last_year, last_area),
        xytext=(last_year - 4, last_area + 3),
        arrowprops=dict(arrowstyle="->"),
    )
    ax.annotate(
        f"~{predicted[target_idx]:.1f} км² ({int(future_years[target_idx])})",
        xy=(future_years[target_idx], predicted[target_idx]),
        xytext=(future_years[target_idx] - 5, predicted[target_idx] + 3),
        arrowprops=dict(arrowstyle="->"),
    )

    ax.axvline(x=last_year, color="gray", linestyle=":", alpha=0.5, linewidth=1)
    ax.set_xlabel("Год", fontsize=13)
    ax.set_ylabel("Площадь ледников (км²)", fontsize=13)
    ax.set_title(title, fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(years.min() - 1, future_years.max() + 2)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=200, bbox_inches="tight")
    return fig


def plot_model_comparison(df_results, metric="F1-score", save_path=None):
    """Столбчатая диаграмма сравнения методов (NDSI vs RF vs U-Net vs ...)."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(df_results["Метод"], df_results[metric], color="#1a6fad")
    ax.set_ylabel(metric)
    ax.set_title(f"Сравнение методов: {metric}")
    ax.set_ylim(0, 1)
    ax.grid(True, axis="y", alpha=0.3)
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150)
    return fig
