# -*- coding: utf-8 -*-
"""Multi-task learning model for joint segmentation, classification, and regression.

Implements a shared encoder with task-specific heads for simultaneous
glacier segmentation (pixel-level), glacier type classification (image-level),
and area/volume regression.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

__all__ = [
    "MultiTaskConfig",
    "shared_encoder",
    "segmentation_head",
    "classification_head",
    "regression_head",
    "build_multi_task_model",
    "multi_task_loss",
    "train_multi_task",
    "evaluate_multi_task",
]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class MultiTaskConfig:
    """Configuration for multi-task learning model."""

    image_size: int = 256
    num_channels: int = 11
    num_classes: int = 2
    num_segmentation_classes: int = 1
    encoder_filters: tuple[int, ...] = (64, 128, 256, 512)
    decoder_filters: tuple[int, ...] = (256, 128, 64)
    attention_reduction: int = 16
    dropout_rate: float = 0.2
    learning_rate: float = 1e-4
    seg_weight: float = 1.0
    cls_weight: float = 0.5
    reg_weight: float = 0.3
    use_attention: bool = True

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.image_size < 32:
            errors.append("image_size must be >= 32")
        if len(self.encoder_filters) < 1:
            errors.append("encoder_filters must have at least 1 element")
        return errors


# ---------------------------------------------------------------------------
# Shared Encoder
# ---------------------------------------------------------------------------


def shared_encoder(x, filters: tuple[int, ...] | MultiTaskConfig, dropout_rate: float = 0.2):
    """Shared encoder backbone with downsampling blocks.

    Args:
        x: Input tensor of shape (B, H, W, C).
        filters: Tuple of filter counts for each encoder stage.
        dropout_rate: Dropout rate.

    Returns:
        Tuple of (final_features, skip_connections).
    """
    import tensorflow as tf

    return_tuple = True
    if isinstance(filters, MultiTaskConfig):
        dropout_rate = filters.dropout_rate
        filters = filters.encoder_filters
        return_tuple = False

    skips = []
    for i, f in enumerate(filters):
        x = tf.keras.layers.Conv2D(f, 3, padding="same")(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Activation("relu")(x)
        x = tf.keras.layers.Conv2D(f, 3, padding="same")(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Activation("relu")(x)
        skips.append(x)
        if i < len(filters) - 1:
            x = tf.keras.layers.MaxPooling2D(2)(x)
            x = tf.keras.layers.Dropout(dropout_rate)(x)

    if return_tuple:
        return x, skips
    return x


# ---------------------------------------------------------------------------
# Task-Specific Heads
# ---------------------------------------------------------------------------


def segmentation_head(
    features,
    skips=None,
    num_classes: int = 1,
    decoder_filters: tuple[int, ...] | None = None,
    use_attention: bool = True,
    filters: int | None = None,
):
    """U-Net style decoder for pixel-level segmentation.

    Args:
        features: Bottleneck features from encoder.
        skips: Skip connection features from encoder stages.
        num_classes: Number of segmentation output classes.
        decoder_filters: Filter counts for decoder stages.
        use_attention: Whether to use attention gates.

    Returns:
        Segmentation output tensor.
    """
    import tensorflow as tf

    if skips is None:
        skips = []
    if decoder_filters is None:
        decoder_filters = (filters or 64,)

    x = features

    for i, f in enumerate(decoder_filters):
        x = tf.keras.layers.UpSampling2D(2, interpolation="bilinear")(x)

        if skips and i < len(skips):
            skip = skips[-(i + 1)]

            if use_attention:
                # Simple channel attention
                scale = tf.keras.layers.Dense(skip.shape[-1], activation="sigmoid")(
                    tf.keras.layers.GlobalAveragePooling2D()(x)
                )
                scale = tf.keras.layers.Reshape((1, 1, skip.shape[-1]))(scale)
                skip = skip * scale

            # Match spatial dimensions
            x = tf.keras.layers.CenterCrop(skip.shape[1], skip.shape[2])(x) if x.shape[1] != skip.shape[1] else x
            x = tf.keras.layers.Concatenate()([x, skip])

        x = tf.keras.layers.Conv2D(f, 3, padding="same")(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Activation("relu")(x)
        x = tf.keras.layers.Conv2D(f, 3, padding="same")(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Activation("relu")(x)

    # Output 1x1 convolution
    if num_classes == 1:
        seg_out = tf.keras.layers.Conv2D(1, 1, activation="sigmoid", name="segmentation")(x)
    else:
        seg_out = tf.keras.layers.Conv2D(num_classes, 1, activation="softmax", name="segmentation")(x)

    return seg_out


def classification_head(features, num_classes: int, dropout_rate: float = 0.3):
    """Global pooling + MLP for image-level classification.

    Args:
        features: Bottleneck features of shape (B, H, W, C).
        num_classes: Number of classification classes.
        dropout_rate: Dropout rate.

    Returns:
        Classification logits of shape (B, num_classes).
    """
    import tensorflow as tf

    if len(features.shape) == 2:
        pooled = features
    else:
        gap = tf.keras.layers.GlobalAveragePooling2D()(features)
        gmp = tf.keras.layers.GlobalMaxPooling2D()(features)
        pooled = tf.keras.layers.Concatenate()([gap, gmp])

    x = tf.keras.layers.Dense(256, activation="relu")(pooled)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dropout(dropout_rate)(x)
    x = tf.keras.layers.Dense(128, activation="relu")(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dropout(dropout_rate)(x)
    logits = tf.keras.layers.Dense(num_classes, name="classification")(x)
    return logits


def regression_head(features, output_dim: int = 1, dropout_rate: float = 0.3, num_outputs: int | None = None):
    """Global pooling + MLP for regression (e.g., glacier area).

    Args:
        features: Bottleneck features of shape (B, H, W, C).
        output_dim: Number of regression outputs.
        dropout_rate: Dropout rate.

    Returns:
        Regression output of shape (B, output_dim).
    """
    import tensorflow as tf

    if num_outputs is not None:
        output_dim = num_outputs

    if len(features.shape) == 2:
        pooled = features
    else:
        gap = tf.keras.layers.GlobalAveragePooling2D()(features)
        gmp = tf.keras.layers.GlobalMaxPooling2D()(features)
        pooled = tf.keras.layers.Concatenate()([gap, gmp])

    x = tf.keras.layers.Dense(128, activation="relu")(pooled)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dropout(dropout_rate)(x)
    x = tf.keras.layers.Dense(64, activation="relu")(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dropout(dropout_rate)(x)
    output = tf.keras.layers.Dense(output_dim, activation="linear", name="regression")(x)
    return output


# ---------------------------------------------------------------------------
# Multi-Task Model
# ---------------------------------------------------------------------------


def build_multi_task_model(config: MultiTaskConfig):
    """Build a multi-task model with shared encoder and task-specific heads.

    Args:
        config: Multi-task configuration.

    Returns:
        Keras Model with single input and three outputs.
    """
    import tensorflow as tf

    inputs = tf.keras.Input(shape=(config.image_size, config.image_size, config.num_channels))

    # Shared encoder
    bottleneck, skips = shared_encoder(inputs, config.encoder_filters, config.dropout_rate)

    # Task-specific heads
    seg_output = segmentation_head(
        bottleneck,
        skips,
        config.num_segmentation_classes,
        config.decoder_filters,
        config.use_attention,
    )
    cls_output = classification_head(bottleneck, config.num_classes, config.dropout_rate)
    reg_output = regression_head(bottleneck, output_dim=1, dropout_rate=config.dropout_rate)

    model = tf.keras.Model(
        inputs=inputs,
        outputs=[seg_output, cls_output, reg_output],
        name="multi_task_model",
    )
    return model


# ---------------------------------------------------------------------------
# Multi-Task Loss
# ---------------------------------------------------------------------------


def multi_task_loss(config: MultiTaskConfig):
    """Create combined multi-task loss function.

    Args:
        config: Multi-task configuration with task weights.

    Returns:
        Loss function that computes weighted sum of task losses.
    """
    import tensorflow as tf

    seg_loss_fn = tf.keras.losses.BinaryCrossentropy(name="seg_loss")
    cls_loss_fn = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True, name="cls_loss")
    reg_loss_fn = tf.keras.losses.MeanSquaredError(name="reg_loss")

    def combined_loss(*args):
        if len(args) == 2:
            (y_true_seg, y_true_cls, y_true_reg), (y_pred_seg, y_pred_cls, y_pred_reg) = args
        elif len(args) == 6:
            y_true_seg, y_true_cls, y_true_reg, y_pred_seg, y_pred_cls, y_pred_reg = args
        else:
            raise TypeError("combined_loss expects either 2 tuples or 6 tensors")

        seg_loss = seg_loss_fn(y_true_seg, y_pred_seg)
        cls_loss = cls_loss_fn(y_true_cls, y_pred_cls)
        reg_loss = reg_loss_fn(y_true_reg, y_pred_reg)

        total = config.seg_weight * seg_loss + config.cls_weight * cls_loss + config.reg_weight * reg_loss
        if len(args) == 2:
            return total
        return total, seg_loss, cls_loss, reg_loss

    return combined_loss


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_multi_task(
    model,
    train_dataset,
    val_dataset,
    config: MultiTaskConfig,
    epochs: int = 100,
    save_dir: str = "models",
):
    """Train the multi-task model.

    Args:
        model: Multi-task Keras model.
        train_dataset: Training dataset yielding (images, (seg, cls, reg)).
        val_dataset: Validation dataset.
        config: Configuration.
        epochs: Number of epochs.
        save_dir: Directory to save checkpoints.

    Returns:
        Training history dictionary.
    """
    from pathlib import Path

    import tensorflow as tf

    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)

    optimizer = tf.keras.optimizers.Adam(learning_rate=config.learning_rate)
    loss_fn = multi_task_loss(config)

    history = {"total_loss": [], "seg_loss": [], "cls_loss": [], "reg_loss": [], "val_total_loss": []}

    best_val_loss = float("inf")

    for epoch in range(epochs):
        epoch_losses: dict[str, list[float]] = {"total": [], "seg": [], "cls": [], "reg": []}

        for batch in train_dataset:
            images, (y_seg, y_cls, y_reg) = batch

            with tf.GradientTape() as tape:
                pred_seg, pred_cls, pred_reg = model(images, training=True)
                total, seg, cls, reg = loss_fn(y_seg, y_cls, y_reg, pred_seg, pred_cls, pred_reg)

            grads = tape.gradient(total, model.trainable_variables)
            optimizer.apply_gradients(zip(grads, model.trainable_variables))

            epoch_losses["total"].append(float(total))
            epoch_losses["seg"].append(float(seg))
            epoch_losses["cls"].append(float(cls))
            epoch_losses["reg"].append(float(reg))

        for key in ("total", "seg", "cls", "reg"):
            history[f"{key}_loss"].append(np.mean(epoch_losses[key]))

        # Validation
        val_losses = []
        for batch in val_dataset:
            images, (y_seg, y_cls, y_reg) = batch
            pred_seg, pred_cls, pred_reg = model(images, training=False)
            total, _, _, _ = loss_fn(y_seg, y_cls, y_reg, pred_seg, pred_cls, pred_reg)
            val_losses.append(float(total))
        avg_val_loss = np.mean(val_losses)
        history["val_total_loss"].append(avg_val_loss)

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            model.save_weights(str(save_path / "multi_task_best.weights.h5"))

        if (epoch + 1) % 10 == 0:
            logger.info(
                "Epoch %d — total: %.4f, seg: %.4f, cls: %.4f, reg: %.4f, val: %.4f",
                epoch + 1,
                history["total_loss"][-1],
                history["seg_loss"][-1],
                history["cls_loss"][-1],
                history["reg_loss"][-1],
                avg_val_loss,
            )

    return history


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def evaluate_multi_task(model, test_dataset, config: MultiTaskConfig):
    """Evaluate multi-task model on test data.

    Args:
        model: Trained multi-task model.
        test_dataset: Test dataset.
        config: Configuration.

    Returns:
        Dictionary with per-task metrics.
    """
    from sklearn.metrics import accuracy_score, f1_score, mean_squared_error

    all_seg_preds, all_seg_true = [], []
    all_cls_preds, all_cls_true = [], []
    all_reg_preds, all_reg_true = [], []

    for batch in test_dataset:
        images, (y_seg, y_cls, y_reg) = batch
        pred_seg, pred_cls, pred_reg = model(images, training=False)

        seg_pred = (pred_seg.numpy().squeeze(-1) > 0.5).astype(int)
        seg_true = y_seg.numpy().squeeze(-1).astype(int)
        all_seg_preds.extend(seg_pred.flatten())
        all_seg_true.extend(seg_true.flatten())

        cls_pred = np.argmax(pred_cls.numpy(), axis=-1)
        all_cls_preds.extend(cls_pred)
        all_cls_true.extend(y_cls.numpy().flatten())

        all_reg_preds.extend(pred_reg.numpy().flatten())
        all_reg_true.extend(y_reg.numpy().flatten())

    seg_acc = float(np.mean(np.array(all_seg_preds) == np.array(all_seg_true)))
    cls_acc = accuracy_score(all_cls_true, all_cls_preds)
    cls_f1 = f1_score(all_cls_true, all_cls_preds, average="weighted", zero_division=0)
    reg_mse = mean_squared_error(all_reg_true, all_reg_preds)
    reg_rmse = float(np.sqrt(reg_mse))

    return {
        "segmentation": {"pixel_accuracy": seg_acc},
        "classification": {"accuracy": cls_acc, "f1_weighted": cls_f1},
        "regression": {"mse": reg_mse, "rmse": reg_rmse},
    }
