"""GlacierNET-KZ — пакет исходного кода проекта.

Lazy imports: submodules are only loaded when accessed, avoiding expensive
TensorFlow/cv2 imports at package level. This keeps test collection fast and
allows importing lightweight modules (config, metrics, etc.) without a GPU stack.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

_SUBMODULES = [
    "active_learning",
    "anomaly",
    "augmentation",
    "benchmarking",
    "callbacks",
    "clustering",
    "config",
    "data_loader",
    "datasets",
    "diffusion_model",
    "distributed_training",
    "domain_adaptation",
    "ensemble",
    "evaluation",
    "experiment_tracking",
    "feature_engineering",
    "federated_learning",
    "graph_neural_network",
    "hyperparameter_tuning",
    "interpretability",
    "losses",
    "metrics",
    "model_compression",
    "models",
    "multi_task_learning",
    "neural_architecture_search",
    "postprocessing",
    "preprocessing",
    "reporting",
    "schedulers",
    "segmentation_models",
    "self_supervised",
    "spectral",
    "time_series",
    "train",
    "uncertainty",
    "visualization",
    "vision_transformer",
]

__all__ = list(_SUBMODULES)


def __getattr__(name: str) -> object:
    if name in _SUBMODULES:
        mod = importlib.import_module(f".{name}", __name__)
        globals()[name] = mod
        return mod
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:
    # Static analysers see the concrete modules for type checking only.
    from . import (  # noqa: F401
        active_learning,
        anomaly,
        augmentation,
        benchmarking,
        callbacks,
        clustering,
        config,
        data_loader,
        datasets,
        diffusion_model,
        distributed_training,
        domain_adaptation,
        ensemble,
        evaluation,
        experiment_tracking,
        feature_engineering,
        federated_learning,
        graph_neural_network,
        hyperparameter_tuning,
        interpretability,
        losses,
        metrics,
        model_compression,
        models,
        multi_task_learning,
        neural_architecture_search,
        postprocessing,
        preprocessing,
        reporting,
        schedulers,
        segmentation_models,
        self_supervised,
        spectral,
        time_series,
        train,
        uncertainty,
        vision_transformer,
        visualization,
    )
