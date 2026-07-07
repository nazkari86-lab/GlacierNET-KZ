"""
Модуль самообучения (Self-Supervised Learning) для GlacierNET-KZ.

Реализует методы контрастивного обучения:
- SimCLR (Simple Framework for Contrastive Learning)
- BYOL (Bootstrap Your Own Latent)
- MoCo (Momentum Contrast)
- Augmentation pipeline
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SelfSupervisedConfig:
    """Конфигурация самообучения."""

    method: str = "simclr"
    encoder_backbone: str = "resnet50"
    projection_dim: int = 128
    hidden_dim: int = 2048
    temperature: float = 0.07
    momentum: float = 0.999
    queue_size: int = 65536
    batch_size: int = 256
    learning_rate: float = 3e-4
    weight_decay: float = 1e-4
    epochs: int = 200
    warmup_epochs: int = 10
    augmentationStrength: float = 1.0
    input_shape: Tuple[int, ...] = (256, 256, 3)
    num_classes: int = 1
    checkpoint_dir: str = "checkpoints/self_supervised"
    log_dir: str = "logs/self_supervised"


@dataclass
class AugmentationConfig:
    """Конфигурация аугментаций."""

    random_crop: bool = True
    random_flip_h: bool = True
    random_flip_v: bool = False
    color_jitter: bool = True
    brightness: float = 0.4
    contrast: float = 0.4
    saturation: float = 0.4
    hue: float = 0.1
    gaussian_blur: bool = True
    blur_kernel_size: int = 23
    random_erasing: bool = True
    erasing_prob: float = 0.5
    erasing_scale: Tuple[float, float] = (0.02, 0.33)
    normalize: bool = True
    mean: Tuple[float, ...] = (0.485, 0.456, 0.406)
    std: Tuple[float, ...] = (0.229, 0.224, 0.225)


class AugmentationPipeline:
    """Пайплайн аугментаций для контрастивного обучения."""

    def __init__(self, config: AugmentationConfig, input_shape: Tuple[int, ...] = (256, 256, 3)):
        self.config = config
        self.input_shape = input_shape

    def build(self):
        """Построение пайплайна аугментаций."""
        import tensorflow as tf

        layers = []

        if self.config.random_crop:
            layers.append(tf.keras.layers.RandomCrop(self.input_shape[0], self.input_shape[1]))

        if self.config.random_flip_h:
            layers.append(tf.keras.layers.RandomFlip("horizontal"))

        if self.config.random_flip_v:
            layers.append(tf.keras.layers.RandomFlip("vertical"))

        if self.config.color_jitter:
            layers.append(tf.keras.layers.RandomBrightness(self.config.brightness))
            layers.append(tf.keras.layers.RandomContrast(self.config.contrast))

        if self.config.gaussian_blur:
            layers.append(self._build_gaussian_blur())

        if self.config.normalize:
            layers.append(
                tf.keras.layers.Normalization(mean=self.config.mean, variance=[s**2 for s in self.config.std])
            )

        return layers

    def _build_gaussian_blur(self):
        """Построение слоя гауссова размытия."""
        import tensorflow as tf

        kernel_size = self.config.blur_kernel_size
        sigma = tf.random.uniform([], 0.1, 2.0)

        x = tf.range(-kernel_size // 2 + 1, kernel_size // 2 + 1, dtype=tf.float32)
        x = tf.exp(-(x**2) / (2 * sigma**2))
        kernel_1d = x / tf.reduce_sum(x)
        kernel_2d = tf.tensordot(kernel_1d, kernel_1d, axes=0)
        kernel_2d = kernel_2d[:, :, tf.newaxis, tf.newaxis]

        def blur_fn(images):
            kernel = tf.tile(kernel_2d, [1, 1, tf.shape(images)[-1], 1])
            return tf.nn.depthwise_conv2d(images, kernel, strides=[1, 1, 1, 1], padding="SAME")

        return tf.keras.layers.Lambda(blur_fn)

    def __call__(self, images, training=True):
        """Применение аугментаций."""

        x = images
        for layer in self.layers:
            x = layer(x, training=training) if hasattr(layer, "__call__") else layer(x)
        return x


class SimCLR:
    """SimCLR — Simple Framework for Contrastive Learning."""

    def __init__(self, config: SelfSupervisedConfig):
        self.config = config
        self.encoder = None
        self.projector = None
        self.model = None

    def build_encoder(self):
        """Построение энкодера."""
        import tensorflow as tf

        backbone = tf.keras.applications.ResNet50(
            include_top=False,
            weights=None,
            input_shape=self.config.input_shape,
        )

        inputs = tf.keras.Input(shape=self.config.input_shape)
        features = backbone(inputs)
        pooled = tf.keras.layers.GlobalAveragePooling2D()(features)

        model = tf.keras.Model(inputs=inputs, outputs=pooled)
        return model

    def build_projector(self, encoder_output_dim: int):
        """Построение проекционной головы."""
        import tensorflow as tf

        inputs = tf.keras.Input(shape=(encoder_output_dim,))
        x = inputs
        x = tf.keras.layers.Dense(self.config.hidden_dim)(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.ReLU()(x)
        x = tf.keras.layers.Dense(self.config.hidden_dim)(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.ReLU()(x)
        x = tf.keras.layers.Dense(self.config.projection_dim)(x)

        return tf.keras.Model(inputs=inputs, outputs=x)

    def build(self):
        """Построение полной модели SimCLR."""
        import tensorflow as tf

        self.encoder = self.build_encoder()
        self.projector = self.build_projector(2048)

        inputs = tf.keras.Input(shape=self.config.input_shape)
        features = self.encoder(inputs)
        projections = self.projector(features)

        self.model = tf.keras.Model(inputs=inputs, outputs=projections)
        return self.model

    def nt_xent_loss(self, z_i: Any, z_j: Any) -> Any:
        """NT-Xent loss (Normalized Temperature-scaled Cross Entropy)."""
        import tensorflow as tf

        batch_size = tf.shape(z_i)[0]
        z_i = tf.math.l2_normalize(z_i, axis=1)
        z_j = tf.math.l2_normalize(z_j, axis=1)

        representations = tf.concat([z_i, z_j], axis=0)
        similarity_matrix = tf.matmul(representations, representations, transpose_b=True)

        mask = tf.eye(2 * batch_size)
        logits = (similarity_matrix - mask * 1e9) / self.config.temperature

        labels = tf.concat(
            [
                tf.range(batch_size, 2 * batch_size),
                tf.range(0, batch_size),
            ],
            axis=0,
        )

        loss = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(labels=labels, logits=logits))
        return loss

    def train_step(self, x_i: Any, x_j: Any, optimizer) -> Dict[str, float]:
        """Один шаг обучения."""
        import tensorflow as tf

        with tf.GradientTape() as tape:
            z_i = self.model(x_i, training=True)
            z_j = self.model(x_j, training=True)
            loss = self.nt_xent_loss(z_i, z_j)

        gradients = tape.gradient(loss, self.model.trainable_weights)
        optimizer.apply_gradients(zip(gradients, self.model.trainable_weights))

        return {"loss": float(loss)}

    def train(self, dataset, num_epochs: Optional[int] = None) -> Dict[str, Any]:
        """Полное обучение SimCLR."""
        import tensorflow as tf

        epochs = num_epochs or self.config.epochs
        optimizer = tf.keras.optimizers.AdamW(
            learning_rate=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )

        history = {"loss": [], "epoch": []}
        start_time = time.time()

        for epoch in range(epochs):
            epoch_loss = 0.0
            num_batches = 0

            for batch in dataset:
                if isinstance(batch, tuple) and len(batch) == 2:
                    x_i, x_j = batch
                else:
                    x_i = x_j = batch

                metrics = self.train_step(x_i, x_j, optimizer)
                epoch_loss += metrics["loss"]
                num_batches += 1

            avg_loss = epoch_loss / max(num_batches, 1)
            history["loss"].append(avg_loss)
            history["epoch"].append(epoch)

            if epoch % 10 == 0:
                logger.info(f"SimCLR Epoch {epoch}/{epochs}: loss = {avg_loss:.4f}")

        total_time = time.time() - start_time
        return {
            "history": history,
            "total_time": total_time,
            "final_loss": history["loss"][-1] if history["loss"] else 0.0,
        }


class BYOL:
    """BYOL — Bootstrap Your Own Latent."""

    def __init__(self, config: SelfSupervisedConfig):
        self.config = config
        self.online_encoder = None
        self.online_projector = None
        self.online_predictor = None
        self.target_encoder = None
        self.target_projector = None
        self.model = None

    def build(self):
        """Построение модели BYOL."""

        online_encoder = self._build_encoder()
        online_projector = self._build_projector(2048)
        online_predictor = self._build_predictor()

        target_encoder = self._build_encoder()
        target_projector = self._build_projector(2048)

        self.online_encoder = online_encoder
        self.online_projector = online_projector
        self.online_predictor = online_predictor
        self.target_encoder = target_encoder
        self.target_projector = target_projector

        self._initialize_target()
        return self

    def _build_encoder(self):
        import tensorflow as tf

        backbone = tf.keras.applications.ResNet50(
            include_top=False,
            weights=None,
            input_shape=self.config.input_shape,
        )
        inputs = tf.keras.Input(shape=self.config.input_shape)
        features = backbone(inputs)
        pooled = tf.keras.layers.GlobalAveragePooling2D()(features)
        return tf.keras.Model(inputs=inputs, outputs=pooled)

    def _build_projector(self, encoder_dim: int):
        import tensorflow as tf

        inputs = tf.keras.Input(shape=(encoder_dim,))
        x = tf.keras.layers.Dense(self.config.hidden_dim)(inputs)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.ReLU()(x)
        x = tf.keras.layers.Dense(self.config.projection_dim)(x)
        return tf.keras.Model(inputs=inputs, outputs=x)

    def _build_predictor(self):
        import tensorflow as tf

        inputs = tf.keras.Input(shape=(self.config.projection_dim,))
        x = tf.keras.layers.Dense(self.config.hidden_dim)(inputs)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.ReLU()(x)
        x = tf.keras.layers.Dense(self.config.projection_dim)(x)
        return tf.keras.Model(inputs=inputs, outputs=x)

    def _initialize_target(self):
        """Инициализация целевых весов (копия онлайн весов)."""
        for w, tw in zip(
            self.online_encoder.trainable_weights + self.online_projector.trainable_weights,
            self.target_encoder.trainable_weights + self.target_projector.trainable_weights,
        ):
            tw.assign(w)

    def _update_target(self):
        """Обновление целевых весов (EMA)."""
        for w, tw in zip(
            self.online_encoder.trainable_weights + self.online_projector.trainable_weights,
            self.target_encoder.trainable_weights + self.target_projector.trainable_weights,
        ):
            tw.assign(self.config.momentum * tw + (1 - self.config.momentum) * w)

    def predict(self, x: Any, training: bool = True):
        """Онлайн предсказание."""
        features = self.online_encoder(x, training=training)
        projections = self.online_projector(features, training=training)
        predictions = self.online_predictor(projections, training=training)
        return predictions

    @staticmethod
    def regression_loss(p: Any, z: Any) -> Any:
        """MSE loss между предсказаниями и целевыми представлениями."""
        import tensorflow as tf

        p = tf.math.l2_normalize(p, axis=1)
        z = tf.math.l2_normalize(z, axis=1)
        return 2.0 - 2.0 * tf.reduce_mean(tf.reduce_sum(p * z, axis=1))

    def train_step(self, x_i: Any, x_j: Any, optimizer) -> Dict[str, float]:
        """Один шаг обучения BYOL."""
        import tensorflow as tf

        with tf.GradientTape() as tape:
            p_i = self.predict(x_i, training=True)
            with tf.GradientTape(watch_non_trainable=True):
                features_j = self.target_encoder(x_j, training=False)
                z_j = self.target_projector(features_j, training=False)

            loss = self.regression_loss(p_i, z_j)

        gradients = tape.gradient(loss, self.model.trainable_weights if self.model else [])
        if gradients:
            optimizer.apply_gradients(zip(gradients, self.model.trainable_weights))

        self._update_target()
        return {"loss": float(loss)}

    def train(self, dataset, num_epochs: Optional[int] = None) -> Dict[str, Any]:
        """Полное обучение BYOL."""
        import tensorflow as tf

        epochs = num_epochs or self.config.epochs
        all_weights = (
            self.online_encoder.trainable_weights
            + self.online_projector.trainable_weights
            + self.online_predictor.trainable_weights
        )
        self.model = tf.keras.Sequential([tf.keras.layers.Lambda(lambda x: x)])
        self.model.trainable_weights = all_weights

        optimizer = tf.keras.optimizers.AdamW(
            learning_rate=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )

        history = {"loss": []}
        start_time = time.time()

        for epoch in range(epochs):
            epoch_loss = 0.0
            num_batches = 0

            for batch in dataset:
                if isinstance(batch, tuple) and len(batch) == 2:
                    x_i, x_j = batch
                else:
                    x_i = x_j = batch

                metrics = self.train_step(x_i, x_j, optimizer)
                epoch_loss += metrics["loss"]
                num_batches += 1

            avg_loss = epoch_loss / max(num_batches, 1)
            history["loss"].append(avg_loss)

            if epoch % 10 == 0:
                logger.info(f"BYOL Epoch {epoch}/{epochs}: loss = {avg_loss:.4f}")

        return {
            "history": history,
            "total_time": time.time() - start_time,
            "final_loss": history["loss"][-1] if history["loss"] else 0.0,
        }


class MoCo:
    """MoCo — Momentum Contrast."""

    def __init__(self, config: SelfSupervisedConfig):
        self.config = config
        self.encoder = None
        self.projector = None
        self.query_head = None
        self.key_head = None
        self.key_queue: Optional[np.ndarray] = None
        self.momentum_encoder = None
        self.momentum_projector = None

    def build(self):
        """Построение модели MoCo."""

        self.encoder = self._build_encoder()
        self.projector = self._build_projector(2048)

        self.momentum_encoder = self._build_encoder()
        self.momentum_projector = self._build_projector(2048)

        self._initialize_momentum()
        self.key_queue = np.random.randn(self.config.queue_size, self.config.projection_dim).astype(np.float32)
        self.key_queue = self.key_queue / (np.linalg.norm(self.key_queue, axis=1, keepdims=True) + 1e-8)

        return self

    def _build_encoder(self):
        import tensorflow as tf

        backbone = tf.keras.applications.ResNet50(
            include_top=False,
            weights=None,
            input_shape=self.config.input_shape,
        )
        inputs = tf.keras.Input(shape=self.config.input_shape)
        features = backbone(inputs)
        pooled = tf.keras.layers.GlobalAveragePooling2D()(features)
        return tf.keras.Model(inputs=inputs, outputs=pooled)

    def _build_projector(self, encoder_dim: int):
        import tensorflow as tf

        inputs = tf.keras.Input(shape=(encoder_dim,))
        x = tf.keras.layers.Dense(self.config.hidden_dim)(inputs)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.ReLU()(x)
        x = tf.keras.layers.Dense(self.config.projection_dim)(x)
        return tf.keras.Model(inputs=inputs, outputs=x)

    def _initialize_momentum(self):
        for w, mw in zip(
            self.encoder.trainable_weights + self.projector.trainable_weights,
            self.momentum_encoder.trainable_weights + self.momentum_projector.trainable_weights,
        ):
            mw.assign(w)

    def _update_momentum(self):
        for w, mw in zip(
            self.encoder.trainable_weights + self.projector.trainable_weights,
            self.momentum_encoder.trainable_weights + self.momentum_projector.trainable_weights,
        ):
            mw.assign(self.config.momentum * mw + (1 - self.config.momentum) * w)

    def enqueue(self, keys: np.ndarray) -> None:
        """Добавление ключей в очередь."""
        keys.shape[0]
        if self.key_queue is None:
            self.key_queue = keys
        else:
            self.key_queue = np.concatenate([self.key_queue, keys], axis=0)
            if self.key_queue.shape[0] > self.config.queue_size:
                self.key_queue = self.key_queue[-self.config.queue_size :]

    def dequeue(self, batch_size: int) -> np.ndarray:
        """Извлечение ключей из очереди."""
        if self.key_queue is None or self.key_queue.shape[0] < batch_size:
            return np.zeros((batch_size, self.config.projection_dim), dtype=np.float32)
        indices = np.random.choice(self.key_queue.shape[0], batch_size, replace=False)
        return self.key_queue[indices]

    def compute_logits(self, q: Any, k: Any, keys: Any) -> Any:
        """Вычисление логитов для contrastive loss."""
        import tensorflow as tf

        q = tf.math.l2_normalize(q, axis=1)
        k = tf.math.l2_normalize(k, axis=1)
        keys = tf.math.l2_normalize(keys, axis=1)

        l_pos = tf.reduce_sum(q * k, axis=1, keepdims=True)
        l_neg = tf.matmul(q, keys, transpose_b=True)

        logits = tf.concat([l_pos, l_neg], axis=1) / self.config.temperature
        return logits

    def momentum_contrast_loss(self, q: Any, k: Any, keys: Any) -> Any:
        """MoCo contrastive loss."""
        import tensorflow as tf

        logits = self.compute_logits(q, k, keys)
        labels = tf.zeros(tf.shape(logits)[0], dtype=tf.int64)
        return tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(labels=labels, logits=logits))

    def train(self, dataset, num_epochs: Optional[int] = None) -> Dict[str, Any]:
        """Полное обучение MoCo."""
        import tensorflow as tf

        epochs = num_epochs or self.config.epochs
        all_weights = self.encoder.trainable_weights + self.projector.trainable_weights

        optimizer = tf.keras.optimizers.AdamW(
            learning_rate=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )

        history = {"loss": []}
        start_time = time.time()

        for epoch in range(epochs):
            epoch_loss = 0.0
            num_batches = 0

            for batch in dataset:
                if isinstance(batch, tuple) and len(batch) == 2:
                    x_q, x_k = batch
                else:
                    x_q = x_k = batch

                with tf.GradientTape() as tape:
                    q = self.projector(self.encoder(x_q, training=True), training=True)
                    with tf.GradientTape(watch_non_trainable=True):
                        k = self.momentum_projector(self.momentum_encoder(x_k, training=False), training=False)
                    keys_np = self.dequeue(tf.shape(q)[0])
                    keys = tf.constant(keys_np)
                    loss = self.momentum_contrast_loss(q, k, keys)

                gradients = tape.gradient(loss, all_weights)
                optimizer.apply_gradients(zip(gradients, all_weights))

                self._update_momentum()
                self.enqueue(k.numpy())

                epoch_loss += float(loss)
                num_batches += 1

            avg_loss = epoch_loss / max(num_batches, 1)
            history["loss"].append(avg_loss)

            if epoch % 10 == 0:
                logger.info(f"MoCo Epoch {epoch}/{epochs}: loss = {avg_loss:.4f}")

        return {
            "history": history,
            "total_time": time.time() - start_time,
            "final_loss": history["loss"][-1] if history["loss"] else 0.0,
        }


class SelfSupervisedManager:
    """Менеджер самообучения."""

    def __init__(self, config: SelfSupervisedConfig):
        self.config = config
        self.method = config.method.lower()
        self.model = None
        self.augmentation = AugmentationPipeline(AugmentationConfig(), config.input_shape)

    def build(self):
        """Построение модели."""
        if self.method == "simclr":
            self.model = SimCLR(self.config)
            self.model.build()
        elif self.method == "byol":
            self.model = BYOL(self.config)
            self.model.build()
        elif self.method == "moco":
            self.model = MoCo(self.config)
            self.model.build()
        else:
            raise ValueError(f"Неизвестный метод: {self.method}")
        return self

    def pretrain(self, dataset, num_epochs: Optional[int] = None) -> Dict[str, Any]:
        """Предобучение на неразмеченных данных."""
        logger.info(f"Запуск предобучения ({self.method})")
        result = self.model.train(dataset, num_epochs)
        logger.info(f"Предобучение завершено: {result['final_loss']:.4f}")
        return result

    def get_encoder(self):
        """Получение обученного энкодера."""
        if self.method == "simclr":
            return self.model.encoder
        elif self.method == "byol":
            return self.model.online_encoder
        elif self.method == "moco":
            return self.model.encoder
        return None

    def save_pretrained(self, path: str) -> str:
        """Сохранение предобученных весов."""
        encoder = self.get_encoder()
        if encoder is not None:
            encoder.save(path)
            logger.info(f"Предобученные веса сохранены: {path}")
            return path
        return ""

    def load_pretrained(self, path: str) -> bool:
        """Загрузка предобученных весов."""
        import tensorflow as tf

        encoder = self.get_encoder()
        if encoder is not None:
            try:
                encoder = tf.keras.models.load_model(path)
                logger.info(f"Предобученные веса загружены: {path}")
                return True
            except Exception as e:
                logger.error(f"Ошибка загрузки весов: {e}")
        return False
