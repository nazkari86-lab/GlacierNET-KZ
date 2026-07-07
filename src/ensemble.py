"""
Методы ансамблирования для семантической сегментации ледников.

Поддерживает:
- Взвешенное усреднение (weighted averaging)
- Мажоритарное голосование (majority voting)
- Stacking (meta-learner)
- Snap-shot ensemble
- TTA-enhanced ensemble
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

import numpy as np

from . import config

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# DATA CLASSES
# ----------------------------------------------------------------------


@dataclass
class EnsembleConfig:
    """Конфигурация ансамбля."""

    method: Literal["weighted", "voting", "stacking", "snapshot"] = "weighted"
    weights: list[float] | None = None
    threshold: float = 0.5
    n_models: int = 3
    use_tta: bool = True
    tta_transforms: list[str] = field(default_factory=lambda: ["original", "flip_lr", "flip_ud", "flip_both"])
    confidence_threshold: float = 0.6
    n_snapshots: int = 5
    snapshot_lr_range: tuple[float, float] = (1e-5, 1e-3)

    def validate(self) -> list[str]:
        errors = []
        if self.method not in ("weighted", "voting", "stacking", "snapshot"):
            errors.append(f"Unknown method: {self.method}")
        if self.weights is not None and self.method == "weighted":
            if len(self.weights) < 2:
                errors.append("weights must have at least 2 elements")
        if self.threshold < 0 or self.threshold > 1:
            errors.append(f"threshold={self.threshold} must be in [0, 1]")
        if self.n_models < 2:
            errors.append(f"n_models={self.n_models} must be >= 2")
        return errors


@dataclass
class EnsembleResult:
    """Результат ансамблирования."""

    probability_map: np.ndarray
    binary_mask: np.ndarray
    confidence_map: np.ndarray
    method: str
    n_models: int
    model_names: list[str]
    individual_predictions: list[np.ndarray] | None = None
    weights: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ----------------------------------------------------------------------
# WEIGHTED AVERAGING
# ----------------------------------------------------------------------


def weighted_average_ensemble(
    predictions: list[np.ndarray],
    weights: list[float] | None = None,
    threshold: float = 0.5,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Взвешенное усреднение вероятностных карт.

    Parameters
    ----------
    predictions : list of np.ndarray
        Список вероятностных карт (H, W) от разных моделей.
    weights : list of float, optional
        Веса моделей. Если None — равные веса.
    threshold : float
        Порог для бинаризации.

    Returns
    -------
    tuple of (prob_map, binary_mask, confidence_map)
    """
    if not predictions:
        raise ValueError("predictions list is empty")

    n = len(predictions)
    if weights is None:
        weights = [1.0 / n] * n
    else:
        total = sum(weights)
        if total <= 0:
            raise ValueError(f"Sum of weights must be positive, got {total}")
        weights = [w / total for w in weights]

    weighted_sum = np.zeros_like(predictions[0], dtype=np.float64)
    for pred, w in zip(predictions, weights):
        weighted_sum += pred * w

    prob_map = weighted_sum.astype(np.float32)
    binary_mask = (prob_map > threshold).astype(np.uint8)

    confidence_map = np.zeros_like(prob_map)
    for pred in predictions:
        confidence_map += np.abs(pred - prob_map)
    confidence_map = 1.0 - confidence_map / n
    confidence_map = np.clip(confidence_map, 0, 1)

    return prob_map, binary_mask, confidence_map


# ----------------------------------------------------------------------
# MAJORITY VOTING
# ----------------------------------------------------------------------


def majority_voting_ensemble(
    predictions: list[np.ndarray],
    threshold: float = 0.5,
    min_votes: int | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Мажоритарное голосование: пиксель классифицируется как лёд,
    если более чем n/2 моделей предсказали лёд.

    Parameters
    ----------
    predictions : list of np.ndarray
        Вероятностные карты (H, W).
    threshold : float
        Порог для бинаризации каждой модели.
    min_votes : int, optional
        Минимальное количество голосов. Если None — majority (n/2).

    Returns
    -------
    tuple of (prob_map, binary_mask, confidence_map)
    """
    if not predictions:
        raise ValueError("predictions list is empty")

    n = len(predictions)
    binary_votes = np.stack([(p > threshold).astype(np.int32) for p in predictions], axis=0)
    vote_counts = binary_votes.sum(axis=0)

    if min_votes is None:
        min_votes = n // 2 + 1

    binary_mask = (vote_counts >= min_votes).astype(np.uint8)
    prob_map = vote_counts.astype(np.float32) / n
    confidence_map = np.abs(vote_counts / n - 0.5) * 2  # 0 at 50%, 1 at 0% or 100%
    confidence_map = np.clip(confidence_map, 0, 1)

    return prob_map, binary_mask, confidence_map


# ----------------------------------------------------------------------
# STACKING (META-LEARNER)
# ----------------------------------------------------------------------


def stacking_ensemble(
    predictions: list[np.ndarray],
    ground_truth: np.ndarray | None = None,
    meta_learner: str = "logistic",
    threshold: float = 0.5,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Stacking: обучает мета-модель на предсказаниях базовых моделей.

    Parameters
    ----------
    predictions : list of np.ndarray
        Вероятностные карты (H, W) от базовых моделей.
    ground_truth : np.ndarray, optional
        Истинная маска для обучения мета-learner. Если None — используется
        simple average как fallback.
    meta_learner : str
        Тип мета-learner: 'logistic', 'rf', 'gbm'.
    threshold : float
        Порог для бинаризации.

    Returns
    -------
    tuple of (prob_map, binary_mask, confidence_map)
    """
    if not predictions:
        raise ValueError("predictions list is empty")

    H, W = predictions[0].shape
    n_models = len(predictions)

    X_meta = np.stack(predictions, axis=-1).reshape(-1, n_models)

    if ground_truth is not None and meta_learner in ("logistic", "rf", "gbm"):
        y_meta = ground_truth.flatten()
        X_meta_train = X_meta
        y_meta_train = y_meta

        if meta_learner == "logistic":
            from sklearn.linear_model import LogisticRegression

            meta_model = LogisticRegression(max_iter=1000, random_state=config.RANDOM_SEED)
        elif meta_learner == "rf":
            from sklearn.ensemble import RandomForestClassifier

            meta_model = RandomForestClassifier(
                n_estimators=100, max_depth=5, random_state=config.RANDOM_SEED, n_jobs=-1
            )
        else:
            from sklearn.ensemble import GradientBoostingClassifier

            meta_model = GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=config.RANDOM_SEED)

        meta_model.fit(X_meta_train, y_meta_train)
        prob_flat = meta_model.predict_proba(X_meta)[:, 1]
        prob_map = prob_flat.reshape(H, W).astype(np.float32)
    else:
        prob_map = np.mean(predictions, axis=0).astype(np.float32)

    binary_mask = (prob_map > threshold).astype(np.uint8)

    confidence_map = np.zeros_like(prob_map)
    for pred in predictions:
        confidence_map += np.abs(pred - prob_map)
    confidence_map = 1.0 - confidence_map / n_models
    confidence_map = np.clip(confidence_map, 0, 1)

    return prob_map, binary_mask, confidence_map


# ----------------------------------------------------------------------
# SNAPSHOT ENSEMBLE
# ----------------------------------------------------------------------


def snapshot_ensemble_predict(
    models: list[Any],
    image: np.ndarray,
    patch_size: int = config.PATCH_SIZE,
    threshold: float = 0.5,
    use_tta: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Snap-shot ensemble: усредняет предсказания из разных точек
    обучения (snapshots).

    Parameters
    ----------
    models : list
        Список обученных моделей (Keras Model).
    image : np.ndarray
        Входной снимок (H, W, C).
    patch_size : int
        Размер патча для скользящего окна.
    threshold : float
        Порог для бинаризации.
    use_tta : bool
        Применять ли TTA для каждой модели.

    Returns
    -------
    tuple of (prob_map, binary_mask, confidence_map)
    """
    if not models:
        raise ValueError("models list is empty")

    predictions = []
    for model in models:
        if use_tta:
            from .models import tta_predict

            prob, _ = tta_predict(model, image, threshold=threshold)
        else:
            from .models import predict_full_image

            prob, _ = predict_full_image(image, model, patch_size=patch_size, threshold=0.5)
        predictions.append(prob)

    return weighted_average_ensemble(predictions, threshold=threshold)


# ----------------------------------------------------------------------
# TTA-ENHANCED ENSEMBLE
# ----------------------------------------------------------------------


def tta_ensemble_predict(
    model: Any,
    image: np.ndarray,
    threshold: float = 0.5,
    transforms: list[str] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """TTA-ensemble: создаёт ансамбль из одного модели через
    различные аугментации.

    Parameters
    ----------
    model : Keras Model
        Обученная модель.
    image : np.ndarray
        Входной снимок (H, W, C).
    threshold : float
        Порог для бинаризации.
    transforms : list of str
        Типы трансформаций: 'original', 'flip_lr', 'flip_ud',
        'flip_both', 'rot90', 'rot180', 'rot270'.

    Returns
    -------
    tuple of (prob_map, binary_mask, confidence_map)
    """
    if transforms is None:
        transforms = ["original", "flip_lr", "flip_ud", "flip_both"]

    predictions = []
    for t in transforms:
        transformed, inverse_fn = _apply_transform(image, t)
        batch = transformed[np.newaxis, ...].astype(np.float32)
        pred = model.predict(batch, verbose=0)[0, ..., 0]
        pred = inverse_fn(pred)
        predictions.append(pred)

    return weighted_average_ensemble(predictions, threshold=threshold)


def _apply_transform(image: np.ndarray, transform: str) -> tuple[np.ndarray, Callable[[np.ndarray], np.ndarray]]:
    """Применяет трансформацию и возвращает (transformed, inverse_fn)."""
    if transform == "original":
        return image, lambda x: x
    elif transform == "flip_lr":
        return np.fliplr(image), lambda x: np.fliplr(x)
    elif transform == "flip_ud":
        return np.flipud(image), lambda x: np.flipud(x)
    elif transform == "flip_both":
        return np.flipud(np.fliplr(image)), lambda x: np.flipud(np.fliplr(x))
    elif transform == "rot90":
        return np.rot90(image, 1), lambda x: np.rot90(x, -1)
    elif transform == "rot180":
        return np.rot90(image, 2), lambda x: np.rot90(x, -2)
    elif transform == "rot270":
        return np.rot90(image, 3), lambda x: np.rot90(x, -3)
    else:
        raise ValueError(f"Unknown transform: {transform}")


# ----------------------------------------------------------------------
# ENSEMBLE ORCHESTRATOR
# ----------------------------------------------------------------------


class EnsemblePredictor:
    """Оркестратор ансамблирования: загружает модели, применяет метод,
    возвращает результат."""

    def __init__(self, cfg: EnsembleConfig | None = None):
        self.cfg = cfg or EnsembleConfig()
        errors = self.cfg.validate()
        if errors:
            raise ValueError(f"Invalid config: {errors}")
        self._models: list[Any] = []
        self._model_names: list[str] = []

    def add_model(self, model: Any, name: str = "") -> None:
        self._models.append(model)
        self._model_names.append(name or f"model_{len(self._models)}")

    def predict(
        self,
        image: np.ndarray,
        patch_size: int = config.PATCH_SIZE,
    ) -> EnsembleResult:
        """Запускает ансамблевое предсказание."""
        if not self._models:
            raise RuntimeError("No models loaded. Call add_model() first.")

        if self.cfg.method == "weighted":
            predictions = self._predict_all(image, patch_size)
            prob, binary, conf = weighted_average_ensemble(
                predictions, weights=self.cfg.weights, threshold=self.cfg.threshold
            )
        elif self.cfg.method == "voting":
            predictions = self._predict_all(image, patch_size)
            prob, binary, conf = majority_voting_ensemble(predictions, threshold=self.cfg.threshold)
        elif self.cfg.method == "stacking":
            predictions = self._predict_all(image, patch_size)
            prob, binary, conf = stacking_ensemble(predictions, threshold=self.cfg.threshold)
        elif self.cfg.method == "snapshot":
            prob, binary, conf = snapshot_ensemble_predict(
                self._models, image, patch_size=patch_size, threshold=self.cfg.threshold, use_tta=self.cfg.use_tta
            )
        else:
            raise ValueError(f"Unknown method: {self.cfg.method}")

        return EnsembleResult(
            probability_map=prob,
            binary_mask=binary,
            confidence_map=conf,
            method=self.cfg.method,
            n_models=len(self._models),
            model_names=list(self._model_names),
            weights=self.cfg.weights,
        )

    def _predict_all(self, image: np.ndarray, patch_size: int) -> list[np.ndarray]:
        """Получает предсказания от всех моделей."""
        predictions = []
        for model in self._models:
            if self.cfg.use_tta:
                from .models import tta_predict

                prob, _ = tta_predict(model, image, threshold=0.5)
            else:
                from .models import predict_full_image

                prob, _ = predict_full_image(image, model, patch_size=patch_size, threshold=0.5)
            predictions.append(prob)
        return predictions

    def save_config(self, path: str | Path) -> None:
        """Сохраняет конфигурацию ансамбля."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "method": self.cfg.method,
            "weights": self.cfg.weights,
            "threshold": self.cfg.threshold,
            "n_models": self.cfg.n_models,
            "use_tta": self.cfg.use_tta,
            "model_names": self._model_names,
        }
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load_config(cls, path: str | Path) -> "EnsemblePredictor":
        """Загружает конфигурацию ансамбля."""
        data = json.loads(Path(path).read_text())
        cfg = EnsembleConfig(
            method=data.get("method", "weighted"),
            weights=data.get("weights"),
            threshold=data.get("threshold", 0.5),
            n_models=data.get("n_models", 3),
            use_tta=data.get("use_tta", True),
        )
        return cls(cfg)


# ----------------------------------------------------------------------
# ANSEMBLE WEIGHT OPTIMIZATION
# ----------------------------------------------------------------------


def optimize_ensemble_weights(
    predictions: list[np.ndarray],
    ground_truth: np.ndarray,
    metric: str = "f1",
) -> list[float]:
    """Оптимизирует веса ансамбля по валидационным данным.

    Parameters
    ----------
    predictions : list of np.ndarray
        Вероятностные карты от базовых моделей.
    ground_truth : np.ndarray
        Истинная маска.
    metric : str
        Метрика для оптимизации: 'f1', 'iou', 'precision', 'recall'.

    Returns
    -------
    list of float
        Оптимизированные веса (нормализованные).
    """
    from scipy.optimize import minimize

    if not predictions:
        raise ValueError("predictions list is empty")

    n = len(predictions)
    y_true = ground_truth.flatten()

    def objective(w):
        w_normalized = np.abs(w) / (np.abs(w).sum() + 1e-8)
        stacked = np.stack(predictions, axis=-1)  # (H, W, n)
        # w_normalized shape (n,) → (1, 1, n) to broadcast over (H, W, n)
        weighted = (stacked * w_normalized[np.newaxis, np.newaxis, :]).sum(axis=-1)
        y_pred = (weighted > 0.5).astype(int).flatten()

        if metric == "f1":
            from sklearn.metrics import f1_score

            return -f1_score(y_true, y_pred, zero_division=0)
        elif metric == "iou":
            from sklearn.metrics import jaccard_score

            return -jaccard_score(y_true, y_pred, zero_division=0)
        elif metric == "precision":
            from sklearn.metrics import precision_score

            return -precision_score(y_true, y_pred, zero_division=0)
        elif metric == "recall":
            from sklearn.metrics import recall_score

            return -recall_score(y_true, y_pred, zero_division=0)
        else:
            raise ValueError(f"Unknown metric: {metric}")

    w0 = np.ones(n) / n
    result = minimize(objective, w0, method="Nelder-Mead", options={"maxiter": 1000})
    w_opt = np.abs(result.x) / (np.abs(result.x).sum() + 1e-8)
    return w_opt.tolist()


# ----------------------------------------------------------------------
# MODEL DIVERSITY ANALYSIS
# ----------------------------------------------------------------------


def compute_prediction_diversity(
    predictions: list[np.ndarray],
) -> dict[str, float]:
    """Вычисляет метрики разнообразия предсказаний ансамбля.

    Parameters
    ----------
    predictions : list of np.ndarray
        Вероятностные карты от разных моделей.

    Returns
    -------
    dict
        Метрики: mean_disagreement, max_disagreement, entropy,
        correlation_matrix.
    """
    if len(predictions) < 2:
        raise ValueError("Need at least 2 predictions for diversity analysis")

    n = len(predictions)
    stacked = np.stack(predictions, axis=0)

    disagreement = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            diff = np.abs(predictions[i] - predictions[j]).mean()
            disagreement[i, j] = diff
            disagreement[j, i] = diff

    mean_disagreement = float(disagreement[disagreement > 0].mean())
    max_disagreement = float(disagreement.max())

    mean_prob = stacked.mean(axis=0)
    entropy = -np.where(mean_prob > 0, mean_prob * np.log(mean_prob + 1e-10), 0) - np.where(
        mean_prob < 1, (1 - mean_prob) * np.log(1 - mean_prob + 1e-10), 0
    )
    mean_entropy = float(entropy.mean())

    corr = np.corrcoef(stacked.reshape(n, -1))
    off_diag = corr[np.triu_indices(n, k=1)]
    mean_correlation = float(off_diag.mean()) if len(off_diag) > 0 else 0.0

    return {
        "mean_disagreement": mean_disagreement,
        "max_disagreement": max_disagreement,
        "mean_entropy": mean_entropy,
        "mean_correlation": mean_correlation,
        "n_models": n,
    }
