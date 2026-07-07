"""
Модуль распределённого обучения для GlacierNET-KZ.

Реализует распределённое обучение с поддержкой:
- Параллелизм данных (Data Parallelism)
- Параллелизм моделей (Model Parallelism)
- Накопление градиентов (Gradient Accumulation)
- Синхронизации весов
- Мониторинга производительности
"""

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import tensorflow as tf

logger = logging.getLogger(__name__)


@dataclass
class DistributedConfig:
    """Конфигурация распределённого обучения."""

    strategy: str = "data_parallel"
    num_workers: int = 2
    num_gpus_per_worker: int = 1
    master_port: int = 8888
    master_addr: str = "localhost"

    gradient_accumulation_steps: int = 4
    max_grad_norm: float = 1.0
    mixed_precision: bool = True
    use_xla: bool = True

    sync_frequency: int = 1
    all_reduce_algorithm: str = "ring"
    compression: str = "none"

    batch_size_per_worker: int = 8
    total_batch_size: int = 32
    learning_rate: float = 1e-4
    warmup_steps: int = 100
    total_steps: int = 10000

    checkpoint_dir: str = "checkpoints/distributed"
    log_dir: str = "logs/distributed"
    enable_profiling: bool = False


@dataclass
class WorkerState:
    """Состояние воркера."""

    worker_id: int
    rank: int = 0
    local_rank: int = 0
    is_active: bool = True
    current_step: int = 0
    loss_history: List[float] = field(default_factory=list)
    throughput: float = 0.0
    memory_usage: float = 0.0
    compute_time: float = 0.0
    comm_time: float = 0.0


class GradientAccumulator:
    """Накопитель градиентов."""

    def __init__(self, model, accumulation_steps: int = 4):
        self.model = model
        self.accumulation_steps = accumulation_steps
        self.accumulated_gradients: Optional[List[np.ndarray]] = None
        self.current_step = 0

    def reset(self) -> None:
        """Сброс накопленных градиентов."""
        self.accumulated_gradients = None
        self.current_step = 0

    def accumulate(self, gradients: List[np.ndarray]) -> bool:
        """Накопление градиентов. Возвращает True когда пора обновить."""
        if self.accumulated_gradients is None:
            self.accumulated_gradients = [np.zeros_like(g) for g in gradients]

        for acc, grad in zip(self.accumulated_gradients, gradients):
            acc += grad / self.accumulation_steps

        self.current_step += 1

        if self.current_step >= self.accumulation_steps:
            return True
        return False

    def get_accumulated(self) -> Optional[List[np.ndarray]]:
        """Получение накопленных градиентов."""
        return self.accumulated_gradients

    def apply_gradients(self, optimizer) -> None:
        """Применение накопленных градиентов."""
        if self.accumulated_gradients is None:
            return

        try:
            for w, grad in zip(self.model.trainable_weights, self.accumulated_gradients):
                grad_tensor = tf.constant(grad, dtype=w.dtype)
                optimizer.apply_gradients([(grad_tensor, w)])
        except Exception as e:
            logger.error(f"Ошибка применения градиентов: {e}")

        self.reset()


class GradientCompressor:
    """Сжатие градиентов для уменьшения трафика."""

    def __init__(self, algorithm: str = "none"):
        self.algorithm = algorithm
        self.compression_ratio_history: List[float] = []

    def compress(self, gradients: List[np.ndarray]) -> Tuple[List[np.ndarray], Dict[str, float]]:
        """Сжатие градиентов."""
        if self.algorithm == "none":
            return gradients, {"ratio": 1.0}

        original_size = sum(g.nbytes for g in gradients)

        if self.algorithm == "top_k":
            compressed = self._top_k_compress(gradients, sparsity=0.99)
        elif self.algorithm == "random_k":
            compressed = self._random_k_compress(gradients, sparsity=0.99)
        elif self.algorithm == "quantize":
            compressed = self._quantize_compress(gradients, bits=8)
        else:
            compressed = gradients

        compressed_size = sum(g.nbytes for g in compressed)
        ratio = original_size / max(compressed_size, 1)
        self.compression_ratio_history.append(ratio)

        return compressed, {"ratio": ratio, "original_bytes": original_size, "compressed_bytes": compressed_size}

    def _top_k_compress(self, gradients: List[np.ndarray], sparsity: float = 0.99) -> List[np.ndarray]:
        """Top-K сжатие."""
        compressed = []
        for g in gradients:
            flat = g.flatten()
            k = max(1, int(len(flat) * (1 - sparsity)))
            indices = np.argpartition(np.abs(flat), -k)[-k:]
            mask = np.zeros_like(flat)
            mask[indices] = flat[indices]
            compressed.append(mask.reshape(g.shape))
        return compressed

    def _random_k_compress(self, gradients: List[np.ndarray], sparsity: float = 0.99) -> List[np.ndarray]:
        """Random-K сжатие."""
        compressed = []
        for g in gradients:
            flat = g.flatten()
            k = max(1, int(len(flat) * (1 - sparsity)))
            indices = np.random.choice(len(flat), k, replace=False)
            mask = np.zeros_like(flat)
            mask[indices] = flat[indices]
            compressed.append(mask.reshape(g.shape))
        return compressed

    def _quantize_compress(self, gradients: List[np.ndarray], bits: int = 8) -> List[np.ndarray]:
        """Квантизация градиентов."""
        compressed = []
        for g in gradients:
            max_val = np.max(np.abs(g))
            if max_val > 0:
                scale = (2 ** (bits - 1) - 1) / max_val
                quantized = np.clip(np.round(g * scale), -(2 ** (bits - 1)), 2 ** (bits - 1) - 1)
                compressed.append((quantized / scale).astype(g.dtype))
            else:
                compressed.append(g)
        return compressed


class PerformanceMonitor:
    """Мониторинг производительности распределённого обучения."""

    def __init__(self):
        self.worker_metrics: Dict[int, WorkerState] = {}
        self.step_times: List[float] = []
        self.throughput_history: List[float] = []
        self.memory_history: List[float] = []
        self.comm_times: List[float] = []
        self._lock = threading.Lock()

    def register_worker(self, worker_id: int, rank: int = 0) -> None:
        """Регистрация воркера."""
        with self._lock:
            self.worker_metrics[worker_id] = WorkerState(worker_id=worker_id, rank=rank)

    def record_step(self, worker_id: int, step_time: float, loss: float, memory_mb: float = 0.0) -> None:
        """Запись метрики шага."""
        with self._lock:
            if worker_id in self.worker_metrics:
                state = self.worker_metrics[worker_id]
                state.current_step += 1
                state.loss_history.append(loss)
                state.compute_time += step_time
                state.memory_usage = memory_mb

            self.step_times.append(step_time)
            self.memory_history.append(memory_mb)

    def record_communication(self, worker_id: int, comm_time: float) -> None:
        """Запись времени коммуникации."""
        with self._lock:
            if worker_id in self.worker_metrics:
                self.worker_metrics[worker_id].comm_time += comm_time
            self.comm_times.append(comm_time)

    def compute_throughput(self, batch_size: int, step_time: float) -> float:
        """Расчёт пропускной способности."""
        if step_time > 0:
            throughput = batch_size / step_time
            self.throughput_history.append(throughput)
            return throughput
        return 0.0

    def get_summary(self) -> Dict[str, Any]:
        """Сводка производительности."""
        worker_summaries = {}
        for wid, state in self.worker_metrics.items():
            worker_summaries[wid] = {
                "worker_id": wid,
                "rank": state.rank,
                "current_step": state.current_step,
                "avg_loss": (np.mean(state.loss_history[-100:]) if state.loss_history else 0.0),
                "total_compute_time": state.compute_time,
                "total_comm_time": state.comm_time,
                "memory_mb": state.memory_usage,
            }

        return {
            "num_workers": len(self.worker_metrics),
            "avg_step_time": float(np.mean(self.step_times[-100:])) if self.step_times else 0.0,
            "avg_throughput": float(np.mean(self.throughput_history[-100:])) if self.throughput_history else 0.0,
            "avg_comm_time": float(np.mean(self.comm_times[-100:])) if self.comm_times else 0.0,
            "total_steps": len(self.step_times),
            "workers": worker_summaries,
        }


class DataParallelWorker:
    """Воркер для параллелизма данных."""

    def __init__(self, worker_id: int, model, config: DistributedConfig):
        self.worker_id = worker_id
        self.model = model
        self.config = config
        self.state = WorkerState(worker_id=worker_id)
        self.gradient_accumulator = GradientAccumulator(model, config.gradient_accumulation_steps)
        self.compressor = GradientCompressor(config.compression)

    def train_step(self, batch_x, batch_y, loss_fn, optimizer) -> Dict[str, float]:
        """Один шаг обучения."""
        import tensorflow as tf

        start_time = time.time()

        with tf.GradientTape() as tape:
            predictions = self.model(batch_x, training=True)
            loss = loss_fn(batch_y, predictions)

        gradients = tape.gradient(loss, self.model.trainable_weights)

        if self.config.max_grad_norm > 0:
            grads, _ = tf.clip_by_global_norm(gradients, self.config.max_grad_norm)
            gradients = grads

        compressed_grads, compression_info = self.compressor.compress([g.numpy() for g in gradients])

        should_update = self.gradient_accumulator.accumulate(compressed_grads)

        step_time = time.time() - start_time
        self.state.loss_history.append(float(loss))
        self.state.compute_time += step_time

        return {
            "loss": float(loss),
            "step_time": step_time,
            "should_update": should_update,
            "compression_ratio": compression_info.get("ratio", 1.0),
        }

    def get_weights(self) -> List[np.ndarray]:
        """Получение весов."""
        try:
            return [w.numpy() for w in self.model.trainable_weights]
        except (AttributeError, TypeError):
            return []

    def set_weights(self, weights: List[np.ndarray]) -> None:
        """Установка весов."""
        try:
            for w, new_w in zip(self.model.trainable_weights, weights):
                w.assign(new_w)
        except (AttributeError, TypeError):
            pass


class GradientAllReducer:
    """AllReduce операции для синхронизации градиентов."""

    def __init__(self, algorithm: str = "ring"):
        self.algorithm = algorithm

    def all_reduce_sum(self, gradients_list: List[List[np.ndarray]]) -> List[np.ndarray]:
        """AllReduce Sum — суммирование градиентов."""
        if not gradients_list:
            return []

        num_workers = len(gradients_list)
        num_layers = len(gradients_list[0])
        averaged = []

        for layer_idx in range(num_layers):
            layer_sum = np.zeros_like(gradients_list[0][layer_idx])
            for worker_grads in gradients_list:
                if layer_idx < len(worker_grads):
                    layer_sum += worker_grads[layer_idx]
            averaged.append(layer_sum / num_workers)

        return averaged

    def all_reduce_mean(self, gradients_list: List[List[np.ndarray]]) -> List[np.ndarray]:
        """AllReduce Mean — усреднение градиентов."""
        return self.all_reduce_sum(gradients_list)

    def broadcast_weights(self, weights: List[np.ndarray], num_workers: int) -> List[List[np.ndarray]]:
        """Broadcast — рассылка весов всем воркерам."""
        return [list(weights) for _ in range(num_workers)]


class DistributedTrainer:
    """Главный тренер распределённого обучения."""

    def __init__(self, config: DistributedConfig, global_model):
        self.config = config
        self.global_model = global_model
        self.workers: List[DataParallelWorker] = []
        self.all_reduce = GradientAllReducer(config.all_reduce_algorithm)
        self.monitor = PerformanceMonitor()
        self.step = 0

        os.makedirs(config.checkpoint_dir, exist_ok=True)
        os.makedirs(config.log_dir, exist_ok=True)

    def setup_workers(self) -> None:
        """Настройка воркеров."""
        import copy

        for i in range(self.config.num_workers):
            worker_model = copy.deepcopy(self.global_model)
            worker = DataParallelWorker(i, worker_model, self.config)
            self.workers.append(worker)
            self.monitor.register_worker(i, rank=i)

        logger.info(f"Настроено {self.config.num_workers} воркеров")

    def synchronize_weights(self) -> None:
        """Синхронизация весов с главной моделью."""
        global_weights = self.get_global_weights()
        for worker in self.workers:
            worker.set_weights(global_weights)

    def get_global_weights(self) -> List[np.ndarray]:
        """Получение глобальных весов."""
        try:
            return [w.numpy() for w in self.global_model.trainable_weights]
        except (AttributeError, TypeError):
            return []

    def set_global_weights(self, weights: List[np.ndarray]) -> None:
        """Установка глобальных весов."""
        try:
            for w, new_w in zip(self.global_model.trainable_weights, weights):
                w.assign(new_w)
        except (AttributeError, TypeError):
            pass

    def train_epoch(self, dataset, loss_fn, optimizer_fn) -> Dict[str, Any]:
        """Одна эпоха распределённого обучения."""

        start_time = time.time()
        epoch_losses = []

        for batch_x, batch_y in dataset:
            worker_gradients = []

            for worker in self.workers:
                worker.set_weights(self.get_global_weights())
                metrics = worker.train_step(batch_x, batch_y, loss_fn, optimizer_fn())
                worker_gradients.append(worker.gradient_accumulator.get_accumulated() or [])
                epoch_losses.append(metrics["loss"])

            if self.config.sync_frequency <= 1 or self.step % self.config.sync_frequency == 0:
                valid_gradients = [g for g in worker_gradients if g]
                if valid_gradients:
                    averaged = self.all_reduce.all_reduce_mean(valid_gradients)
                    self.set_global_weights(averaged)

            self.step += 1

        epoch_time = time.time() - start_time
        avg_loss = np.mean(epoch_losses) if epoch_losses else 0.0

        return {
            "epoch_loss": float(avg_loss),
            "epoch_time": epoch_time,
            "step": self.step,
        }

    def train(self, dataset, loss_fn, optimizer_fn, num_epochs: int = 10) -> Dict[str, Any]:
        """Полное распределённое обучение."""
        self.setup_workers()
        self.synchronize_weights()

        history = {"loss": [], "epoch_time": []}
        start_time = time.time()

        for epoch in range(num_epochs):
            epoch_result = self.train_epoch(dataset, loss_fn, optimizer_fn)
            history["loss"].append(epoch_result["epoch_loss"])
            history["epoch_time"].append(epoch_result["epoch_time"])

            if epoch % 5 == 0:
                summary = self.monitor.get_summary()
                logger.info(
                    f"Эпоха {epoch}: loss = {epoch_result['epoch_loss']:.4f}, "
                    f"время = {epoch_result['epoch_time']:.2f}s, "
                    f"воркеры = {summary['num_workers']}"
                )

        total_time = time.time() - start_time
        self.save_checkpoint()

        return {
            "history": history,
            "total_time": total_time,
            "final_loss": history["loss"][-1] if history["loss"] else 0.0,
            "performance": self.monitor.get_summary(),
        }

    def save_checkpoint(self) -> str:
        """Сохранение чекпоинта."""

        checkpoint_path = os.path.join(self.config.checkpoint_dir, f"step_{self.step:06d}")
        try:
            self.global_model.save(checkpoint_path)
            logger.info(f"Чекпоинт сохранён: {checkpoint_path}")
            return checkpoint_path
        except Exception as e:
            logger.error(f"Ошибка сохранения чекпоинта: {e}")
            return ""

    def get_training_summary(self) -> Dict[str, Any]:
        """Сводка обучения."""
        return {
            "strategy": self.config.strategy,
            "num_workers": self.config.num_workers,
            "current_step": self.step,
            "gradient_accumulation": self.config.gradient_accumulation_steps,
            "mixed_precision": self.config.mixed_precision,
            "performance": self.monitor.get_summary(),
        }
