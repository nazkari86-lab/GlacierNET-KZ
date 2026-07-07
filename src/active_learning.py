# -*- coding: utf-8 -*-
"""Active learning loop for glacier image annotation.

Implements uncertainty sampling, query strategies, and an interactive
annotation interface to maximize model performance with minimal labeling.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

__all__ = [
    "QueryStrategy",
    "ActiveLearningConfig",
    "uncertainty_sampling",
    "margin_sampling",
    "entropy_sampling",
    "query_by_committee",
    "density_weighted_sampling",
    "expected_gradient_length",
    "ActiveLearningLoop",
    "AnnotationBudget",
]


# ---------------------------------------------------------------------------
# Enums & Configuration
# ---------------------------------------------------------------------------


class QueryStrategy(str, Enum):
    UNCERTAINTY = "uncertainty"
    MARGIN = "margin"
    ENTROPY = "entropy"
    RANDOM = "random"
    COMMITTEE = "committee"
    DENSITY = "density"
    EGL = "expected_gradient_length"


@dataclass
class ActiveLearningConfig:
    """Configuration for active learning loop."""

    strategy: QueryStrategy = QueryStrategy.UNCERTAINTY
    initial_labeled: int = 50
    query_batch_size: int = 20
    max_iterations: int = 50
    stopping_criterion: float = 0.95
    num_committee: int = 5
    diversity_weight: float = 0.5
    temperature: float = 1.0
    min_confidence: float = 0.0
    use_calibration: bool = True

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.initial_labeled < 1:
            errors.append("initial_labeled must be >= 1")
        if self.query_batch_size < 1:
            errors.append("query_batch_size must be >= 1")
        return errors


@dataclass
class AnnotationBudget:
    """Tracks annotation budget and progress."""

    total_budget: int
    used: int = 0
    cost_per_sample: float = 1.0

    @property
    def remaining(self) -> int:
        return max(0, self.total_budget - self.used)

    @property
    def utilization(self) -> float:
        return self.used / max(self.total_budget, 1)

    def can_annotate(self, n: int = 1) -> bool:
        return self.remaining >= n

    def consume(self, n: int = 1) -> bool:
        if not self.can_annotate(n):
            return False
        self.used += n
        return True


# ---------------------------------------------------------------------------
# Query Strategies
# ---------------------------------------------------------------------------


def uncertainty_sampling(predictions: np.ndarray, n_instances: int) -> np.ndarray:
    """Select samples with highest uncertainty (lowest max probability).

    Args:
        predictions: Model predictions of shape (N, num_classes) as probabilities.
        n_instances: Number of instances to query.

    Returns:
        Indices of selected instances.
    """
    if len(predictions) == 0:
        return np.array([], dtype=int)

    max_probs = np.max(predictions, axis=-1)
    uncertainties = 1.0 - max_probs
    selected = np.argsort(uncertainties)[-n_instances:]
    return selected.astype(int)


def margin_sampling(predictions: np.ndarray, n_instances: int) -> np.ndarray:
    """Select samples with smallest margin between top-2 predictions.

    Args:
        predictions: Model predictions of shape (N, num_classes).
        n_instances: Number of instances to query.

    Returns:
        Indices of selected instances.
    """
    if len(predictions) == 0:
        return np.array([], dtype=int)

    sorted_probs = np.sort(predictions, axis=-1)[:, ::-1]
    margins = sorted_probs[:, 0] - sorted_probs[:, 1]
    selected = np.argsort(margins)[:n_instances]
    return selected.astype(int)


def entropy_sampling(predictions: np.ndarray, n_instances: int) -> np.ndarray:
    """Select samples with highest prediction entropy.

    Args:
        predictions: Model predictions of shape (N, num_classes).
        n_instances: Number of instances to query.

    Returns:
        Indices of selected instances.
    """
    if len(predictions) == 0:
        return np.array([], dtype=int)

    eps = 1e-10
    entropy = -np.sum(predictions * np.log(predictions + eps), axis=-1)
    selected = np.argsort(entropy)[-n_instances:]
    return selected.astype(int)


def query_by_committee(committee_predictions: list[np.ndarray], n_instances: int) -> np.ndarray:
    """Select samples with highest disagreement among committee members.

    Uses vote entropy to measure disagreement.

    Args:
        committee_predictions: List of prediction arrays, each (N, num_classes).
        n_instances: Number of instances to query.

    Returns:
        Indices of selected instances.
    """
    if not committee_predictions or len(committee_predictions[0]) == 0:
        return np.array([], dtype=int)

    n_samples = len(committee_predictions[0])
    n_classes = committee_predictions[0].shape[-1]

    # Get hard predictions from each committee member
    votes = np.stack([np.argmax(p, axis=-1) for p in committee_predictions], axis=0)

    # Vote entropy for each sample
    vote_entropies = np.zeros(n_samples)
    n_members = len(committee_predictions)

    for i in range(n_samples):
        sample_votes = votes[:, i]
        for c in range(n_classes):
            vote_count = np.sum(sample_votes == c)
            if vote_count > 0:
                prob = vote_count / n_members
                vote_entropies[i] -= prob * np.log(prob + 1e-10)

    selected = np.argsort(vote_entropies)[-n_instances:]
    return selected.astype(int)


def density_weighted_sampling(
    predictions: np.ndarray,
    features: np.ndarray,
    n_instances: int,
    diversity_weight: float = 0.5,
) -> np.ndarray:
    """Density-weighted uncertainty sampling.

    Balances model uncertainty with feature-space density to avoid
    selecting isolated outliers.

    Args:
        predictions: Model predictions (N, num_classes).
        features: Feature vectors (N, D) for density estimation.
        n_instances: Number of instances to query.
        diversity_weight: Weight for diversity component (0-1).

    Returns:
        Indices of selected instances.
    """
    if len(predictions) == 0:
        return np.array([], dtype=int)

    # Uncertainty component
    max_probs = np.max(predictions, axis=-1)
    uncertainty = 1.0 - max_probs

    # Density component: inverse of mean distance to k nearest neighbors
    k = min(5, len(features))
    from scipy.spatial.distance import cdist

    dists = cdist(features, features)
    np.fill_diagonal(dists, np.inf)
    knn_dists = np.sort(dists, axis=1)[:, :k]
    mean_dist = knn_dists.mean(axis=1)
    density = 1.0 / (mean_dist + 1e-10)
    density = density / density.max()

    # Combined score
    score = (1 - diversity_weight) * uncertainty + diversity_weight * density
    selected = np.argsort(score)[-n_instances:]
    return selected.astype(int)


def expected_gradient_length(
    model,
    unlabeled_data: np.ndarray,
    n_instances: int,
    num_classes: int = 2,
) -> np.ndarray:
    """Select samples that would cause the largest gradient update.

    Approximates Expected Gradient Length (EGL) by computing gradient
    magnitude for each possible label assignment.

    Args:
        model: Trained Keras model.
        unlabeled_data: Unlabeled data array (N, H, W, C) or (N, D).
        n_instances: Number of instances to query.
        num_classes: Number of possible classes.

    Returns:
        Indices of selected instances.
    """
    import tensorflow as tf

    n_samples = len(unlabeled_data)
    egl_scores = np.zeros(n_samples)

    data_tensor = tf.constant(unlabeled_data, dtype=tf.float32)

    for i in range(n_samples):
        sample = data_tensor[i : i + 1]
        max_grad_norm = 0.0

        for c in range(num_classes):
            label = tf.constant([c], dtype=tf.int32)

            with tf.GradientTape() as tape:
                logits = model(sample, training=False)
                loss = tf.nn.sparse_softmax_cross_entropy_with_logits(label, logits)

            grads = tape.gradient(loss, model.trainable_variables)
            grad_norm = sum(tf.reduce_sum(g**2) for g in grads if g is not None)
            grad_norm = float(tf.sqrt(grad_norm))
            max_grad_norm = max(max_grad_norm, grad_norm)

        egl_scores[i] = max_grad_norm

    selected = np.argsort(egl_scores)[-n_instances:]
    return selected.astype(int)


# ---------------------------------------------------------------------------
# Active Learning Loop
# ---------------------------------------------------------------------------


class ActiveLearningLoop:
    """Manages the active learning cycle: train → query → annotate → update.

    This class orchestrates the iterative process of selecting the most
    informative samples for annotation, training the model, and evaluating
    performance improvements.
    """

    def __init__(self, config: ActiveLearningConfig, budget: AnnotationBudget | None = None):
        self.config = config
        self.budget = budget or AnnotationBudget(total_budget=1000)
        self.iteration = 0
        self.history: list[dict[str, Any]] = []
        self.labeled_indices: list[int] = []
        self.labels: dict[int, int] = {}

    def initialize_labeled_set(self, n_samples: int, rng: np.random.Generator | None = None) -> np.ndarray:
        """Randomly select initial labeled samples.

        Args:
            n_samples: Total number of available samples.
            rng: Random number generator.

        Returns:
            Boolean mask of initially labeled samples.
        """
        if rng is None:
            rng = np.random.default_rng(42)

        n_init = min(self.config.initial_labeled, n_samples)
        initial = rng.choice(n_samples, size=n_init, replace=False)
        self.labeled_indices = initial.tolist()
        self.budget.consume(n_init)

        mask = np.zeros(n_samples, dtype=bool)
        mask[initial] = True
        logger.info("Initialized with %d labeled samples", n_init)
        return mask

    def query(self, predictions: np.ndarray, n_instances: int | None = None) -> np.ndarray:
        """Select next batch of samples to annotate using the configured strategy.

        Args:
            predictions: Model predictions for all unlabeled samples.
            n_instances: Override batch size.

        Returns:
            Indices of samples to annotate (relative to unlabeled pool).
        """
        if n_instances is None:
            n_instances = min(self.config.query_batch_size, self.budget.remaining)

        if n_instances <= 0:
            logger.warning("No budget remaining for queries")
            return np.array([], dtype=int)

        if self.config.strategy == QueryStrategy.UNCERTAINTY:
            indices = uncertainty_sampling(predictions, n_instances)
        elif self.config.strategy == QueryStrategy.MARGIN:
            indices = margin_sampling(predictions, n_instances)
        elif self.config.strategy == QueryStrategy.ENTROPY:
            indices = entropy_sampling(predictions, n_instances)
        elif self.config.strategy == QueryStrategy.COMMITTEE:
            # committee predictions should be passed as predictions list
            indices = uncertainty_sampling(predictions, n_instances)
        elif self.config.strategy == QueryStrategy.RANDOM:
            indices = np.random.choice(len(predictions), size=min(n_instances, len(predictions)), replace=False)
        else:
            indices = uncertainty_sampling(predictions, n_instances)

        self.budget.consume(len(indices))
        logger.info(
            "Iteration %d: queried %d samples (strategy=%s, budget remaining=%d)",
            self.iteration,
            len(indices),
            self.config.strategy.value,
            self.budget.remaining,
        )
        return indices

    def query_with_features(
        self,
        predictions: np.ndarray,
        features: np.ndarray,
        n_instances: int | None = None,
    ) -> np.ndarray:
        """Query with density-weighted strategy using feature vectors.

        Args:
            predictions: Model predictions (N, num_classes).
            features: Feature vectors (N, D).
            n_instances: Override batch size.

        Returns:
            Selected indices.
        """
        if n_instances is None:
            n_instances = min(self.config.query_batch_size, self.budget.remaining)

        indices = density_weighted_sampling(
            predictions,
            features,
            n_instances,
            self.config.diversity_weight,
        )
        self.budget.consume(len(indices))
        return indices

    def record_labels(self, indices: np.ndarray, labels: np.ndarray) -> None:
        """Record annotations for queried samples.

        Args:
            indices: Global indices of annotated samples.
            labels: Corresponding labels.
        """
        for idx, label in zip(indices, labels):
            self.labels[int(idx)] = int(label)
            if int(idx) not in self.labeled_indices:
                self.labeled_indices.append(int(idx))

    def should_stop(self, current_metric: float) -> bool:
        """Check stopping criterion.

        Args:
            current_metric: Current model performance metric.

        Returns:
            True if training should stop.
        """
        if self.iteration >= self.config.max_iterations:
            logger.info("Stopping: max iterations reached")
            return True
        if current_metric >= self.config.stopping_criterion:
            logger.info("Stopping: metric %.4f >= criterion %.4f", current_metric, self.config.stopping_criterion)
            return True
        if self.budget.remaining <= 0:
            logger.info("Stopping: budget exhausted")
            return True
        return False

    def step(self, current_metric: float) -> dict[str, Any]:
        """Advance one iteration, recording metrics.

        Args:
            current_metric: Current model performance.

        Returns:
            Step summary dictionary.
        """
        self.iteration += 1
        record = {
            "iteration": self.iteration,
            "metric": current_metric,
            "labeled_count": len(self.labeled_indices),
            "budget_remaining": self.budget.remaining,
            "should_stop": self.should_stop(current_metric),
        }
        self.history.append(record)
        return record

    def get_labeled_mask(self, total_samples: int) -> np.ndarray:
        """Get boolean mask of labeled samples.

        Args:
            total_samples: Total number of samples in the dataset.

        Returns:
            Boolean mask of shape (total_samples,).
        """
        mask = np.zeros(total_samples, dtype=bool)
        valid_indices = [i for i in self.labeled_indices if i < total_samples]
        mask[valid_indices] = True
        return mask

    def summary(self) -> dict[str, Any]:
        """Return summary of the active learning session."""
        return {
            "total_iterations": self.iteration,
            "total_labeled": len(self.labeled_indices),
            "budget_used": self.budget.used,
            "budget_remaining": self.budget.remaining,
            "strategy": self.config.strategy.value,
            "history": self.history,
        }
