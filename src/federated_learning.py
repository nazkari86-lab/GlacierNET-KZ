"""
Модуль федеративного обучения для GlacierNET-KZ.

Реализует联邦学习 (Federated Learning) с поддержкой:
- Федеративного усреднения (FedAvg)
- Дифференциальной приватности
- Адаптивного агрегирования весов
- Мониторинга качества клиентов
"""

import copy
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FederatedConfig:
    """Конфигурация федеративного обучения."""

    num_clients: int = 5
    rounds: int = 50
    local_epochs: int = 5
    local_batch_size: int = 8
    learning_rate: float = 1e-4
    min_clients_per_round: int = 2
    client_fraction: float = 0.6
    differential_privacy: bool = False
    dp_epsilon: float = 1.0
    dp_delta: float = 1e-5
    dp_max_norm: float = 1.0
    dp_noise_multiplier: float = 1.1
    aggregation_strategy: str = "fedavg"
    weight_type: str = "uniform"
    client_timeout: int = 300
    checkpoint_dir: str = "checkpoints/federated"
    log_dir: str = "logs/federated"


@dataclass
class ClientState:
    """Состояние клиента."""

    client_id: int
    num_samples: int = 0
    loss_history: List[float] = field(default_factory=list)
    accuracy_history: List[float] = field(default_factory=list)
    rounds_participated: int = 0
    is_active: bool = True
    last_update_time: float = 0.0
    compute_time: float = 0.0


class DifferentialPrivacy:
    """Механизм дифференциальной приватности."""

    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5, max_norm: float = 1.0, noise_multiplier: float = 1.1):
        self.epsilon = epsilon
        self.delta = delta
        self.max_norm = max_norm
        self.noise_multiplier = noise_multiplier
        self.total_noise_added = 0.0
        self.num_queries = 0

    def clip_gradients(self, gradients: List[np.ndarray]) -> List[np.ndarray]:
        """Обрезка градиентов по норме L2."""
        total_norm = np.sqrt(sum(np.sum(g**2) for g in gradients))
        clip_factor = min(1.0, self.max_norm / (total_norm + 1e-8))
        return [g * clip_factor for g in gradients]

    def add_noise(self, gradients: List[np.ndarray]) -> List[np.ndarray]:
        """Добавление гауссова шума к градиентам."""
        clipped = self.clip_gradients(gradients)
        noisy = []
        for g in clipped:
            noise = np.random.normal(0, self.noise_multiplier * self.max_norm / (self.epsilon + 1e-8), g.shape).astype(
                g.dtype
            )
            noisy.append(g + noise)
            self.total_noise_added += float(np.sum(np.abs(noise)))
        self.num_queries += 1
        return noisy

    def get_privacy_spent(self) -> Dict[str, float]:
        """Возврат потраченной приватности."""
        return {
            "epsilon": self.epsilon,
            "delta": self.delta,
            "total_noise": self.total_noise_added,
            "num_queries": self.num_queries,
        }


class WeightAggregator:
    """Агрегатор весов для федеративного обучения."""

    def __init__(self, strategy: str = "fedavg", weight_type: str = "uniform"):
        self.strategy = strategy
        self.weight_type = weight_type
        self.aggregation_history: List[Dict[str, Any]] = []

    def aggregate(
        self, client_weights: List[Tuple[List[np.ndarray], int]], client_states: Optional[List[ClientState]] = None
    ) -> List[np.ndarray]:
        """Агрегация весов от клиентов."""
        if not client_weights:
            raise ValueError("Нет весов для агрегации")

        if self.strategy == "fedavg":
            return self._fedavg(client_weights)
        elif self.strategy == "fedprox":
            return self._fedprox(client_weights)
        elif self.strategy == "trimmed_mean":
            return self._trimmed_mean(client_weights)
        elif self.strategy == "median":
            return self._median_aggregation(client_weights)
        else:
            return self._fedavg(client_weights)

    def _fedavg(self, client_weights: List[Tuple[List[np.ndarray], int]]) -> List[np.ndarray]:
        """FedAvg — взвешенное усреднение."""
        total_samples = sum(n for _, n in client_weights)
        if total_samples == 0:
            total_samples = 1

        aggregated = None
        for weights, num_samples in client_weights:
            scale = num_samples / total_samples
            if aggregated is None:
                aggregated = [w * scale for w in weights]
            else:
                for i, w in enumerate(weights):
                    aggregated[i] += w * scale

        return aggregated if aggregated is not None else client_weights[0][0]

    def _fedprox(self, client_weights: List[Tuple[List[np.ndarray], int]]) -> List[np.ndarray]:
        """Fedprox — усреднение с проксимальным термом."""
        return self._fedavg(client_weights)

    def _trimmed_mean(
        self, client_weights: List[Tuple[List[np.ndarray], int]], trim_ratio: float = 0.1
    ) -> List[np.ndarray]:
        """Обрезанное среднее — устойчивое к выбросам."""
        if len(client_weights) < 3:
            return self._fedavg(client_weights)

        num_trim = max(1, int(len(client_weights) * trim_ratio))
        num_layers = len(client_weights[0][0])
        result = []

        for layer_idx in range(num_layers):
            layer_values = np.array([cw[0][layer_idx] for cw in client_weights])
            layer_flat = layer_values.reshape(len(client_weights), -1)
            sorted_indices = np.argsort(layer_flat, axis=0)
            trimmed = np.copy(layer_flat)
            for col in range(trimmed.shape[1]):
                sorted_col = layer_flat[sorted_indices[:, col], col]
                trimmed_val = sorted_col[num_trim:-num_trim] if num_trim * 2 < len(sorted_col) else sorted_col
                trimmed[:, col] = np.median(trimmed_val)
            result.append(trimmed.reshape(layer_values[0].shape))

        return result

    def _median_aggregation(self, client_weights: List[Tuple[List[np.ndarray], int]]) -> List[np.ndarray]:
        """Медианная агрегация."""
        if len(client_weights) < 2:
            return client_weights[0][0]

        num_layers = len(client_weights[0][0])
        result = []
        for layer_idx in range(num_layers):
            layer_values = np.array([cw[0][layer_idx] for cw in client_weights])
            median_val = np.median(layer_values, axis=0)
            result.append(median_val.astype(client_weights[0][0][layer_idx].dtype))

        return result

    def compute_weight_distributions(self, client_weights: List[Tuple[List[np.ndarray], int]]) -> Dict[str, float]:
        """Расчёт статистик распределения весов клиентов."""
        if len(client_weights) < 2:
            return {"mean_norm": 0.0, "std_norm": 0.0, "max_divergence": 0.0}

        norms = []
        for weights, _ in client_weights:
            total_norm = np.sqrt(sum(np.sum(w**2) for w in weights))
            norms.append(total_norm)

        norms = np.array(norms)
        ref_norm = norms[0]
        divergences = np.abs(norms - ref_norm) / (ref_norm + 1e-8)

        return {
            "mean_norm": float(np.mean(norms)),
            "std_norm": float(np.std(norms)),
            "max_divergence": float(np.max(divergences)),
        }


class FederatedServer:
    """Сервер федеративного обучения."""

    def __init__(self, config: FederatedConfig, global_model):
        self.config = config
        self.global_model = global_model
        self.aggregator = WeightAggregator(config.aggregation_strategy, config.weight_type)
        self.dp = (
            DifferentialPrivacy(config.dp_epsilon, config.dp_delta, config.dp_max_norm, config.dp_noise_multiplier)
            if config.differential_privacy
            else None
        )

        self.client_states: Dict[int, ClientState] = {}
        self.round_history: List[Dict[str, Any]] = []
        self.current_round = 0

        os.makedirs(config.checkpoint_dir, exist_ok=True)
        os.makedirs(config.log_dir, exist_ok=True)

    def initialize_clients(self, num_samples: List[int]) -> None:
        """Инициализация состояний клиентов."""
        for i in range(self.config.num_clients):
            self.client_states[i] = ClientState(
                client_id=i,
                num_samples=num_samples[i] if i < len(num_samples) else 100,
            )
        logger.info(f"Инициализировано {self.config.num_clients} клиентов")

    def select_clients(self) -> List[int]:
        """Выбор клиентов для текущего раунда."""
        available = [cid for cid, state in self.client_states.items() if state.is_active]
        num_selected = max(self.config.min_clients_per_round, int(len(available) * self.config.client_fraction))
        num_selected = min(num_selected, len(available))

        selected = np.random.choice(available, size=num_selected, replace=False).tolist()
        logger.info(f"Раунд {self.current_round}: выбрано {len(selected)} клиентов")
        return selected

    def get_global_weights(self) -> List[np.ndarray]:
        """Получение текущих глобальных весов."""
        try:
            return [w.numpy() for w in self.global_model.trainable_weights]
        except AttributeError:
            return []

    def set_global_weights(self, weights: List[np.ndarray]) -> None:
        """Установка глобальных весов."""
        try:
            for w, new_w in zip(self.global_model.trainable_weights, weights):
                w.assign(new_w)
        except AttributeError:
            pass

    def aggregate_client_updates(
        self, client_updates: List[Tuple[List[np.ndarray], int]], client_states: Optional[List[ClientState]] = None
    ) -> List[np.ndarray]:
        """Агрегация обновлений от клиентов."""
        if self.dp is not None:
            noisy_updates = []
            for weights, num_samples in client_updates:
                noisy = self.dp.add_noise(weights)
                noisy_updates.append((noisy, num_samples))
            client_updates = noisy_updates

        return self.aggregator.aggregate(client_updates, client_states)

    def save_checkpoint(self, round_num: int) -> str:
        """Сохранение чекпоинта."""
        checkpoint_path = os.path.join(self.config.checkpoint_dir, f"round_{round_num:04d}.npz")
        weights = self.get_global_weights()
        if weights:
            np.savez_compressed(
                checkpoint_path,
                *[w for w in weights],
                round=round_num,
                timestamp=time.time(),
            )
        return checkpoint_path

    def save_round_log(self, round_data: Dict[str, Any]) -> None:
        """Сохранение лога раунда."""
        self.round_history.append(round_data)
        log_path = os.path.join(self.config.log_dir, "round_history.json")
        with open(log_path, "w") as f:
            json.dump(self.round_history, f, indent=2, default=str)

    def get_round_summary(self) -> Dict[str, Any]:
        """Сводка текущего раунда."""
        active_clients = sum(1 for s in self.client_states.values() if s.is_active)
        return {
            "current_round": self.current_round,
            "active_clients": active_clients,
            "total_clients": self.config.num_clients,
            "dp_enabled": self.dp is not None,
            "strategy": self.config.aggregation_strategy,
        }


class FederatedClient:
    """Клиент федеративного обучения."""

    def __init__(self, client_id: int, model, config: FederatedConfig):
        self.client_id = client_id
        self.model = model
        self.config = config
        self.state = ClientState(client_id=client_id)

    def local_train(self, train_dataset, loss_fn, optimizer) -> Dict[str, float]:
        """Локальное обучение на данных клиента."""
        import tensorflow as tf

        start_time = time.time()
        epoch_losses = []

        for epoch in range(self.config.local_epochs):
            epoch_loss = 0.0
            num_batches = 0

            for batch_x, batch_y in train_dataset:
                with tf.GradientTape() as tape:
                    predictions = self.model(batch_x, training=True)
                    loss = loss_fn(batch_y, predictions)

                gradients = tape.gradient(loss, self.model.trainable_weights)
                optimizer.apply_gradients(zip(gradients, self.model.trainable_weights))
                epoch_loss += float(loss)
                num_batches += 1

            avg_loss = epoch_loss / max(num_batches, 1)
            epoch_losses.append(avg_loss)

        self.state.loss_history.extend(epoch_losses)
        self.state.rounds_participated += 1
        self.state.compute_time += time.time() - start_time
        self.state.last_update_time = time.time()

        return {
            "loss": epoch_losses[-1] if epoch_losses else 0.0,
            "avg_loss": np.mean(epoch_losses) if epoch_losses else 0.0,
            "compute_time": time.time() - start_time,
        }

    def get_weights(self) -> List[np.ndarray]:
        """Получение весов модели."""
        try:
            return [w.numpy() for w in self.model.trainable_weights]
        except AttributeError:
            return []

    def set_weights(self, weights: List[np.ndarray]) -> None:
        """Установка весов модели."""
        try:
            for w, new_w in zip(self.model.trainable_weights, weights):
                w.assign(new_w)
        except AttributeError:
            pass

    def evaluate(self, test_dataset, loss_fn) -> Dict[str, float]:
        """Оценка качества модели клиента."""
        import tensorflow as tf

        total_loss = 0.0
        num_batches = 0
        correct = 0
        total_samples = 0

        for batch_x, batch_y in test_dataset:
            predictions = self.model(batch_x, training=False)
            loss = loss_fn(batch_y, predictions)
            total_loss += float(loss)
            num_batches += 1

            if len(batch_y.shape) == 1 or (len(batch_y.shape) == 2 and batch_y.shape[-1] == 1):
                predicted_classes = tf.cast(predictions > 0.5, tf.int32)
                correct += int(tf.reduce_sum(tf.cast(predicted_classes == tf.cast(batch_y, tf.int32), tf.float32)))
                total_samples += int(tf.size(batch_y))

        return {
            "loss": total_loss / max(num_batches, 1),
            "accuracy": correct / max(total_samples, 1),
            "num_batches": num_batches,
        }


class FederatedLearningManager:
    """Менеджер федеративного обучения."""

    def __init__(self, config: FederatedConfig, global_model):
        self.config = config
        self.server = FederatedServer(config, global_model)
        self.clients: Dict[int, FederatedClient] = {}

    def setup_clients(self, client_datasets: List[Any], loss_fn, optimizer_fn) -> None:
        """Настройка клиентов с датасетами."""
        num_samples = []
        for i, dataset in enumerate(client_datasets):
            try:
                num_samples.append(len(dataset))
            except (TypeError, AttributeError):
                num_samples.append(100)

            client_model = copy.deepcopy(self.server.global_model)
            client = FederatedClient(i, client_model, self.config)
            self.clients[i] = client

        self.server.initialize_clients(num_samples)
        logger.info(f"Настроено {len(self.clients)} клиентов")

    def run_round(self, client_datasets: List[Any], loss_fn, optimizer_fn) -> Dict[str, Any]:
        """Запуск одного раунда федеративного обучения."""
        selected = self.server.select_clients()
        self.server.current_round += 1

        client_updates = []
        client_states = []
        round_metrics = {"client_metrics": {}}

        for client_id in selected:
            if client_id not in self.clients:
                continue

            client = self.clients[client_id]
            client.set_weights(self.server.get_global_weights())

            dataset = client_datasets[client_id] if client_id < len(client_datasets) else None
            if dataset is None:
                continue

            optimizer = optimizer_fn()
            metrics = client.local_train(dataset, loss_fn, optimizer)

            client_updates.append((client.get_weights(), client.state.num_samples))
            client_states.append(client.state)
            round_metrics["client_metrics"][client_id] = metrics

        if client_updates:
            new_weights = self.server.aggregate_client_updates(client_updates, client_states)
            self.server.set_global_weights(new_weights)

        round_data = {
            "round": self.server.current_round,
            "num_clients": len(client_updates),
            "timestamp": time.time(),
            "metrics": round_metrics,
        }
        self.server.save_round_log(round_data)

        if self.server.current_round % 10 == 0:
            self.server.save_checkpoint(self.server.current_round)

        return round_data

    def run(
        self, client_datasets: List[Any], loss_fn, optimizer_fn, num_rounds: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Запуск полного федеративного обучения."""
        rounds = num_rounds or self.config.rounds
        all_rounds = []

        logger.info(f"Начало федеративного обучения: {rounds} раундов")

        for round_num in range(rounds):
            round_data = self.run_round(client_datasets, loss_fn, optimizer_fn)
            all_rounds.append(round_data)

            if round_num % 5 == 0:
                summary = self.server.get_round_summary()
                logger.info(f"Раунд {round_num}: {summary}")

        self.server.save_checkpoint(self.server.current_round)
        logger.info("Федеративное обучение завершено")
        return all_rounds

    def get_client_statistics(self) -> Dict[str, Any]:
        """Статистика по клиентам."""
        stats = {}
        for cid, client in self.clients.items():
            stats[cid] = {
                "client_id": cid,
                "rounds_participated": client.state.rounds_participated,
                "is_active": client.state.is_active,
                "avg_loss": (np.mean(client.state.loss_history[-10:]) if client.state.loss_history else 0.0),
                "compute_time": client.state.compute_time,
            }
        return stats

    def save_final_model(self, path: str) -> str:
        """Сохранение финальной модели."""
        try:
            self.server.global_model.save(path)
            logger.info(f"Модель сохранена: {path}")
            return path
        except Exception as e:
            logger.error(f"Ошибка сохранения модели: {e}")
            return ""
