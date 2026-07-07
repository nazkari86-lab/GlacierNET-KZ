"""
Модуль сжатия моделей для GlacierNET-KZ.

Реализует методы сжатия:
- Квантизация (INT8, FLOAT16)
- Обрезка (Pruning) — structured/unstructured
- Дистилляция знаний (Knowledge Distillation)
- Аналитика размера модели
"""

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CompressionConfig:
    """Конфигурация сжатия."""

    quantization: bool = True
    quantization_type: str = "int8"
    quantization_sensitive_layers: List[str] = field(default_factory=list)

    pruning: bool = True
    pruning_method: str = "magnitude"
    pruning_sparsity: float = 0.5
    pruning_schedule: str = "polynomial"
    pruning_start_step: int = 0
    pruning_end_step: int = 1000

    distillation: bool = False
    distillation_temperature: float = 4.0
    distillation_alpha: float = 0.7
    distillation_teacher_model: Optional[str] = None

    target_compression_ratio: float = 0.5
    fine_tune_epochs: int = 5
    fine_tune_lr: float = 1e-5
    batch_size: int = 8

    checkpoint_dir: str = "checkpoints/compressed"
    log_dir: str = "logs/compression"


@dataclass
class ModelAnalytics:
    """Аналитика модели."""

    total_params: int = 0
    trainable_params: int = 0
    non_trainable_params: int = 0
    total_bytes: int = 0
    model_size_mb: float = 0.0
    layer_count: int = 0
    layer_params: Dict[str, int] = field(default_factory=dict)
    compression_ratio: float = 1.0
    sparsity: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_params": self.total_params,
            "trainable_params": self.trainable_params,
            "non_trainable_params": self.non_trainable_params,
            "total_bytes": self.total_bytes,
            "model_size_mb": self.model_size_mb,
            "layer_count": self.layer_count,
            "compression_ratio": self.compression_ratio,
            "sparsity": self.sparsity,
        }


class ModelAnalyzer:
    """Аналитика размера и структуры модели."""

    @staticmethod
    def analyze(model) -> ModelAnalytics:
        """Анализ модели."""
        analytics = ModelAnalytics()

        try:
            analytics.total_params = int(np.sum([int(np.prod(w.shape)) for w in model.trainable_weights]))
            analytics.trainable_params = int(np.sum([int(np.prod(w.shape)) for w in model.trainable_weights]))
            analytics.non_trainable_params = int(np.sum([int(np.prod(w.shape)) for w in model.non_trainable_weights]))
        except (AttributeError, TypeError):
            analytics.total_params = 0

        total_bytes = 0
        layer_params = {}
        try:
            for layer in model.layers:
                layer_params[layer.name] = sum(int(np.prod(w.shape)) for w in layer.weights)
                for w in layer.weights:
                    total_bytes += int(np.prod(w.shape)) * w.dtype.size
        except (AttributeError, TypeError):
            pass

        analytics.total_bytes = total_bytes
        analytics.model_size_mb = total_bytes / (1024 * 1024)
        analytics.layer_count = len(model.layers) if hasattr(model, "layers") else 0
        analytics.layer_params = layer_params

        total_count = sum(layer_params.values()) if layer_params else 1
        zero_count = 0
        try:
            for w in model.trainable_weights:
                zero_count += int(np.sum(np.abs(w.numpy()) < 1e-8))
        except (AttributeError, TypeError):
            pass

        analytics.sparsity = zero_count / max(total_count, 1)
        return analytics


class Quantizer:
    """Квантизация моделей."""

    def __init__(self, config: CompressionConfig):
        self.config = config

    def quantize_int8(self, model):
        """INT8 квантизация."""
        import tensorflow as tf

        try:
            converter = tf.lite.TFLiteConverter.from_keras_model(model)
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
            converter.target_spec.supported_types = [tf.int8]
            tflite_model = converter.convert()
            return tflite_model
        except Exception as e:
            logger.error(f"Ошибка INT8 квантизации: {e}")
            return None

    def quantize_float16(self, model):
        """FLOAT16 квантизация."""
        import tensorflow as tf

        try:
            converter = tf.lite.TFLiteConverter.from_keras_model(model)
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
            converter.target_spec.supported_types = [tf.float16]
            tflite_model = converter.convert()
            return tflite_model
        except Exception as e:
            logger.error(f"Ошибка FLOAT16 квантизации: {e}")
            return None

    def quantize(self, model) -> Tuple[Optional[bytes], ModelAnalytics]:
        """Квантизация модели."""
        if self.config.quantization_type == "int8":
            quantized = self.quantize_int8(model)
        elif self.config.quantization_type == "float16":
            quantized = self.quantize_float16(model)
        else:
            quantized = self.quantize_float16(model)

        analytics = ModelAnalytics()
        if quantized:
            analytics.total_bytes = len(quantized)
            analytics.model_size_mb = len(quantized) / (1024 * 1024)

            original_size = ModelAnalyzer.analyze(model).total_bytes
            analytics.compression_ratio = original_size / max(len(quantized), 1)

        return quantized, analytics

    def save_quantized(self, tflite_model: bytes, path: str) -> str:
        """Сохранение квантизованной модели."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            f.write(tflite_model)
        logger.info(f"Квантизованная модель сохранена: {path}")
        return path


class Pruner:
    """Обрезка моделей."""

    def __init__(self, config: CompressionConfig):
        self.config = config
        self.masks: Dict[str, np.ndarray] = {}
        self.current_step = 0

    def compute_magnitude_mask(self, weights: np.ndarray, sparsity: float) -> np.ndarray:
        """Вычисление маски по величине весов."""
        threshold = np.percentile(np.abs(weights), sparsity * 100)
        mask = (np.abs(weights) >= threshold).astype(np.float32)
        return mask

    def compute_gradient_mask(self, weights: np.ndarray, gradients: np.ndarray, sparsity: float) -> np.ndarray:
        """Вычисление маски по градиентам."""
        importance = np.abs(weights) * np.abs(gradients)
        threshold = np.percentile(importance, sparsity * 100)
        mask = (importance >= threshold).astype(np.float32)
        return mask

    def compute_structured_mask(self, weights: np.ndarray, sparsity: float, axis: int = -1) -> np.ndarray:
        """Структурированная обрезка по фильтрам/каналам."""
        norm = np.linalg.norm(weights, axis=tuple(i for i in range(weights.ndim) if i != axis))
        threshold = np.percentile(norm, sparsity * 100)
        mask_1d = (norm >= threshold).astype(np.float32)

        mask = np.zeros_like(weights)
        slices = [slice(None)] * weights.ndim
        for i in range(weights.shape[axis]):
            if mask_1d[i] > 0:
                slices[axis] = i
                mask[tuple(slices)] = 1.0

        return mask

    def apply_mask(self, variable, mask: np.ndarray) -> None:
        """Применение маски к переменной."""
        original = variable.numpy()
        pruned = original * mask
        variable.assign(pruned)

    def prune_model(self, model, step: int = 0) -> Dict[str, Any]:
        """Обрезка всех весов модели."""

        self.current_step = step
        total_params = 0
        pruned_params = 0

        for layer in model.layers:
            for w in layer.weights:
                if "kernel" in w.name or "weight" in w.name:
                    weights = w.numpy()
                    total_params += weights.size

                    if self.config.pruning_method == "magnitude":
                        mask = self.compute_magnitude_mask(weights, self.config.pruning_sparsity)
                    elif self.config.pruning_method == "structured":
                        mask = self.compute_structured_mask(weights, self.config.pruning_sparsity)
                    else:
                        mask = self.compute_magnitude_mask(weights, self.config.pruning_sparsity)

                    self.masks[w.name] = mask
                    pruned_weights = weights * mask
                    w.assign(pruned_weights)
                    pruned_params += int(np.sum(mask == 0))

        sparsity_achieved = pruned_params / max(total_params, 1)

        return {
            "total_params": total_params,
            "pruned_params": pruned_params,
            "sparsity": sparsity_achieved,
            "num_layers_pruned": len(self.masks),
        }

    def get_sparsity_schedule(self, current_step: int, total_steps: int) -> float:
        """Расписание обрезки."""
        if self.config.pruning_schedule == "constant":
            return self.config.pruning_sparsity
        elif self.config.pruning_schedule == "linear":
            progress = current_step / max(total_steps, 1)
            return self.config.pruning_sparsity * progress
        elif self.config.pruning_schedule == "polynomial":
            progress = current_step / max(total_steps, 1)
            return self.config.pruning_sparsity * (1 - (1 - progress) ** 3)
        return self.config.pruning_sparsity

    def save_masks(self, path: str) -> None:
        """Сохранение масок."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        np.savez_compressed(path, **self.masks)
        logger.info(f"Маски сохранены: {path}")


class KnowledgeDistiller:
    """Дистилляция знаний."""

    def __init__(self, config: CompressionConfig):
        self.config = config
        self.teacher_model = None
        self.student_model = None

    def load_teacher(self, teacher_model) -> None:
        """Загрузка учителя."""
        self.teacher_model = teacher_model
        if self.teacher_model is not None:
            try:
                self.teacher_model.trainable = False
            except (AttributeError, TypeError):
                pass
        logger.info("Модель учителя загружена")

    def set_student(self, student_model) -> None:
        """Установка студента."""
        self.student_model = student_model

    def distillation_loss(self, student_logits: Any, teacher_logits: Any, labels: Any) -> Any:
        """Функция потерь дистилляции."""
        import tensorflow as tf

        hard_loss = tf.keras.losses.binary_crossentropy(labels, student_logits)

        soft_student = tf.nn.sigmoid(student_logits / self.config.distillation_temperature)
        soft_teacher = tf.nn.sigmoid(teacher_logits / self.config.distillation_temperature)

        soft_loss = tf.keras.losses.binary_crossentropy(soft_teacher, soft_student)

        combined_loss = (1 - self.config.distillation_alpha) * hard_loss + self.config.distillation_alpha * soft_loss

        return tf.reduce_mean(combined_loss)

    def train_step(self, x: Any, y: Any, optimizer) -> Dict[str, float]:
        """Один шаг дистилляции."""
        import tensorflow as tf

        with tf.GradientTape() as tape:
            student_output = self.student_model(x, training=True)

            teacher_output = tf.stop_gradient(self.teacher_model(x, training=False))

            loss = self.distillation_loss(student_output, teacher_output, y)

        gradients = tape.gradient(loss, self.student_model.trainable_weights)
        optimizer.apply_gradients(zip(gradients, self.student_model.trainable_weights))

        return {"distillation_loss": float(loss)}

    def train(self, train_dataset, num_epochs: Optional[int] = None) -> Dict[str, Any]:
        """Обучение студента дистилляцией."""
        import tensorflow as tf

        epochs = num_epochs or self.config.fine_tune_epochs
        optimizer = tf.keras.optimizers.Adam(learning_rate=self.config.fine_tune_lr)

        history = {"distillation_loss": []}
        start_time = time.time()

        for epoch in range(epochs):
            epoch_loss = 0.0
            num_batches = 0

            for batch_x, batch_y in train_dataset:
                metrics = self.train_step(batch_x, batch_y, optimizer)
                epoch_loss += metrics["distillation_loss"]
                num_batches += 1

            avg_loss = epoch_loss / max(num_batches, 1)
            history["distillation_loss"].append(avg_loss)

            logger.info(f"Дистилляция Epoch {epoch}/{epochs}: loss = {avg_loss:.4f}")

        return {
            "history": history,
            "total_time": time.time() - start_time,
            "final_loss": history["distillation_loss"][-1] if history["distillation_loss"] else 0.0,
        }


class ModelCompressor:
    """Менеджер сжатия моделей."""

    def __init__(self, config: CompressionConfig):
        self.config = config
        self.quantizer = Quantizer(config)
        self.pruner = Pruner(config)
        self.distiller = KnowledgeDistiller(config)
        self.analytics_history: List[Dict[str, Any]] = []

    def compress(self, model, teacher_model=None, train_dataset=None) -> Tuple[Any, Dict[str, Any]]:
        """Полное сжатие модели."""

        start_time = time.time()
        original_analytics = ModelAnalyzer.analyze(model)

        results = {
            "original_size_mb": original_analytics.model_size_mb,
            "original_params": original_analytics.total_params,
            "steps": [],
        }

        if self.config.pruning:
            logger.info("Применение обрезки...")
            pruning_result = self.pruner.prune_model(model)
            results["pruning"] = pruning_result

        if self.config.distillation and teacher_model is not None:
            logger.info("Запуск дистилляции...")
            self.distiller.load_teacher(teacher_model)
            self.distiller.set_student(model)

            if train_dataset is not None:
                distill_result = self.distiller.train(train_dataset, self.config.fine_tune_epochs)
                results["distillation"] = distill_result

        if self.config.quantization:
            logger.info("Применение квантизации...")
            quantized_model, quant_analytics = self.quantizer.quantize(model)
            results["quantization"] = {
                "type": self.config.quantization_type,
                "compressed_size_mb": quant_analytics.model_size_mb,
                "compression_ratio": quant_analytics.compression_ratio,
            }

            if quantized_model is not None:
                quant_path = os.path.join(
                    self.config.checkpoint_dir, f"model_quantized_{self.config.quantization_type}.tflite"
                )
                self.quantizer.save_quantized(quantized_model, quant_path)

        final_analytics = ModelAnalyzer.analyze(model)
        results["final_size_mb"] = final_analytics.model_size_mb
        results["final_params"] = final_analytics.total_params
        results["total_compression_ratio"] = original_analytics.total_bytes / max(final_analytics.total_bytes, 1)
        results["total_time"] = time.time() - start_time

        self.analytics_history.append(results)
        return model, results

    def save_compressed(self, model, path: str) -> str:
        """Сохранение сжатой модели."""
        try:
            model.save(path)
            logger.info(f"Сжатая модель сохранена: {path}")
            return path
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
            return ""

    def get_compression_report(self) -> Dict[str, Any]:
        """Отчёт о сжатии."""
        if not self.analytics_history:
            return {"status": "no_compressions"}

        latest = self.analytics_history[-1]
        return {
            "original_size_mb": latest.get("original_size_mb", 0),
            "final_size_mb": latest.get("final_size_mb", 0),
            "compression_ratio": latest.get("total_compression_ratio", 1.0),
            "total_time": latest.get("total_time", 0),
            "pruning_applied": "pruning" in latest,
            "quantization_applied": "quantization" in latest,
            "distillation_applied": "distillation" in latest,
        }
