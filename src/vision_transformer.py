# -*- coding: utf-8 -*-
"""Vision Transformer (ViT) for satellite image classification.

Implements patch embedding, multi-head self-attention, positional encoding,
and a full classification head for glacier vs. non-glacier satellite imagery.
TensorFlow is imported lazily inside functions.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

__all__ = [
    "ViTConfig",
    "patch_embedding",
    "multi_head_attention",
    "transformer_encoder_block",
    "vit_classifier",
    "build_vit_for_glacier",
    "train_vit",
    "evaluate_vit",
]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class ViTConfig:
    """Configuration for Vision Transformer."""

    image_size: int = 256
    patch_size: int = 16
    num_channels: int = 11
    embed_dim: int = 768
    num_heads: int = 12
    num_layers: int = 12
    mlp_dim: int = 3072
    dropout_rate: float = 0.1
    num_classes: int = 2
    attention_dropout_rate: float = 0.0
    weight_decay: float = 0.05
    learning_rate: float = 1e-4
    warmup_steps: int = 1000
    label_smoothing: float = 0.1

    @property
    def num_patches(self) -> int:
        return (self.image_size // self.patch_size) ** 2

    @property
    def grid_size(self) -> int:
        return self.image_size // self.patch_size

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.image_size % self.patch_size != 0:
            errors.append(f"image_size ({self.image_size}) must be divisible by patch_size ({self.patch_size})")
        if self.embed_dim % self.num_heads != 0:
            errors.append(f"embed_dim ({self.embed_dim}) must be divisible by num_heads ({self.num_heads})")
        if self.num_layers < 1:
            errors.append("num_layers must be >= 1")
        if self.num_classes < 2:
            errors.append("num_classes must be >= 2")
        return errors


# ---------------------------------------------------------------------------
# Patch Embedding
# ---------------------------------------------------------------------------


def patch_embedding(x, embed_dim: int, patch_size: int):
    """Convert image into sequence of patch embeddings.

    Args:
        x: Input tensor of shape (B, H, W, C).
        embed_dim: Output embedding dimension.
        patch_size: Size of each patch.

    Returns:
        Tensor of shape (B, num_patches, embed_dim).
    """
    import tensorflow as tf

    batch_size = tf.shape(x)[0]
    h = tf.shape(x)[1]
    w = tf.shape(x)[2]

    num_patches_h = h // patch_size
    num_patches_w = w // patch_size

    # Extract patches using strided convolution
    patches = tf.nn.conv2d(
        x,
        filters=tf.random.normal((patch_size, patch_size, x.shape[-1], embed_dim), stddev=0.02),
        strides=(1, patch_size, patch_size, 1),
        padding="VALID",
    )

    # Reshape to (B, num_patches, embed_dim)
    patches = tf.reshape(patches, (batch_size, num_patches_h * num_patches_w, embed_dim))
    return patches


class PatchEmbeddingLayer:
    """Keras-compatible patch embedding using a Conv2D layer."""

    def __init__(self, config: ViTConfig):
        self.config = config

    def __call__(self, x, training: bool = False):
        import tensorflow as tf

        patch_size = self.config.patch_size
        embed_dim = self.config.embed_dim

        patches = tf.nn.conv2d(
            x,
            filters=tf.random.normal(
                (patch_size, patch_size, self.config.num_channels, embed_dim),
                stddev=0.02,
            ),
            strides=(1, patch_size, patch_size, 1),
            padding="VALID",
        )

        num_patches = self.config.num_patches
        patches = tf.reshape(patches, (tf.shape(x)[0], num_patches, embed_dim))
        return patches


# ---------------------------------------------------------------------------
# Positional Encoding
# ---------------------------------------------------------------------------


def get_positional_encoding(max_len: int, embed_dim: int):
    """Generate sinusoidal positional encoding.

    Args:
        max_len: Maximum sequence length.
        embed_dim: Embedding dimension.

    Returns:
        NumPy array of shape (1, max_len, embed_dim).
    """
    pe = np.zeros((1, max_len, embed_dim), dtype=np.float32)
    position = np.arange(0, max_len, dtype=np.float32)[:, np.newaxis]
    div_term = np.exp(np.arange(0, embed_dim, 2, dtype=np.float32) * -(math.log(10000.0) / embed_dim))

    pe[0, :, 0::2] = np.sin(position * div_term)
    pe[0, :, 1::2] = np.cos(position * div_term)
    return pe


class PositionalEncodingLayer:
    """Adds learnable or sinusoidal positional encoding to patch embeddings."""

    def __init__(self, config: ViTConfig, use_sinusoidal: bool = False):
        self.config = config
        self.use_sinusoidal = use_sinusoidal

    def __call__(self, x, training: bool = False):
        import tensorflow as tf

        num_patches = self.config.num_patches
        embed_dim = self.config.embed_dim

        if self.use_sinusoidal:
            pe = get_positional_encoding(num_patches + 1, embed_dim)
            pe_tensor = tf.constant(pe, dtype=tf.float32)
            return x + pe_tensor[:, :num_patches, :]

        pos_embedding = tf.Variable(
            tf.random.normal((1, num_patches + 1, embed_dim), stddev=0.02),
            trainable=True,
            name="pos_embedding",
        )
        return x + pos_embedding[:, :num_patches, :]


# ---------------------------------------------------------------------------
# Multi-Head Self-Attention
# ---------------------------------------------------------------------------


def multi_head_attention(x, num_heads: int, embed_dim: int, dropout_rate: float = 0.0):
    """Multi-head self-attention mechanism.

    Args:
        x: Input tensor of shape (B, seq_len, embed_dim).
        num_heads: Number of attention heads.
        embed_dim: Total embedding dimension.
        dropout_rate: Dropout rate for attention weights.

    Returns:
        Output tensor of shape (B, seq_len, embed_dim).
    """
    import tensorflow as tf

    head_dim = embed_dim // num_heads

    qkv = tf.keras.layers.Dense(embed_dim * 3, use_bias=False)(x)
    qkv = tf.reshape(qkv, (tf.shape(x)[0], -1, 3, num_heads, head_dim))
    qkv = tf.transpose(qkv, perm=[0, 2, 3, 1, 4])

    q, k, v = qkv[:, 0], qkv[:, 1], qkv[:, 2]

    scale = math.sqrt(head_dim)
    attn_scores = tf.matmul(q, k, transpose_b=True) / scale
    attn_weights = tf.nn.softmax(attn_scores, axis=-1)

    if dropout_rate > 0.0:
        attn_weights = tf.nn.dropout(attn_weights, rate=dropout_rate)

    attn_output = tf.matmul(attn_weights, v)
    attn_output = tf.transpose(attn_output, perm=[0, 2, 1, 3])
    batch_size = tf.shape(x)[0]
    attn_output = tf.reshape(attn_output, (batch_size, -1, embed_dim))

    output = tf.keras.layers.Dense(embed_dim, use_bias=False)(attn_output)
    if dropout_rate > 0.0:
        output = tf.nn.dropout(output, rate=dropout_rate)
    return output


class MultiHeadAttentionLayer:
    """Keras-compatible multi-head self-attention with pre-norm."""

    def __init__(self, config: ViTConfig):
        self.config = config

    def __call__(self, x, training: bool = False):
        import tensorflow as tf

        embed_dim = self.config.embed_dim
        num_heads = self.config.num_heads
        head_dim = embed_dim // num_heads
        attn_drop = self.config.attention_dropout_rate if training else 0.0

        # Pre-norm
        normed = tf.keras.layers.LayerNormalization(epsilon=1e-6)(x)

        qkv = tf.keras.layers.Dense(embed_dim * 3, use_bias=False)(normed)
        qkv = tf.reshape(qkv, (tf.shape(x)[0], -1, 3, num_heads, head_dim))
        qkv = tf.transpose(qkv, perm=[0, 2, 3, 1, 4])
        q, k, v = qkv[:, 0], qkv[:, 1], qkv[:, 2]

        scale = math.sqrt(head_dim)
        attn_scores = tf.matmul(q, k, transpose_b=True) / scale
        attn_weights = tf.nn.softmax(attn_scores, axis=-1)

        if attn_drop > 0.0:
            attn_weights = tf.nn.dropout(attn_weights, rate=attn_drop)

        attn_output = tf.matmul(attn_weights, v)
        attn_output = tf.transpose(attn_output, perm=[0, 2, 1, 3])
        batch_size = tf.shape(x)[0]
        attn_output = tf.reshape(attn_output, (batch_size, -1, embed_dim))

        attn_output = tf.keras.layers.Dense(embed_dim, use_bias=False)(attn_output)
        if attn_drop > 0.0:
            attn_output = tf.nn.dropout(attn_output, rate=attn_drop)

        return x + attn_output


# ---------------------------------------------------------------------------
# Transformer Encoder Block
# ---------------------------------------------------------------------------


def transformer_encoder_block(x, num_heads: int, embed_dim: int, mlp_dim: int, dropout_rate: float = 0.1):
    """Single transformer encoder block: attention + FFN with residual connections.

    Args:
        x: Input tensor of shape (B, seq_len, embed_dim).
        num_heads: Number of attention heads.
        embed_dim: Embedding dimension.
        mlp_dim: Hidden dimension in feed-forward network.
        dropout_rate: Dropout rate.

    Returns:
        Output tensor of shape (B, seq_len, embed_dim).
    """
    import tensorflow as tf

    # Multi-head attention with residual
    attn_out = multi_head_attention(x, num_heads, embed_dim, dropout_rate)
    x = x + attn_out

    # Feed-forward network with residual
    normed = tf.keras.layers.LayerNormalization(epsilon=1e-6)(x)
    ffn = tf.keras.layers.Dense(mlp_dim, activation="gelu")(normed)
    ffn = tf.keras.layers.Dropout(dropout_rate)(ffn)
    ffn = tf.keras.layers.Dense(embed_dim)(ffn)
    ffn = tf.keras.layers.Dropout(dropout_rate)(ffn)
    x = x + ffn

    return x


class TransformerEncoderBlock:
    """Keras-compatible transformer encoder block with pre-norm architecture."""

    def __init__(self, config: ViTConfig):
        self.config = config
        self.mlp_dim = config.mlp_dim

    def __call__(self, x, training: bool = False):
        import tensorflow as tf

        embed_dim = self.config.embed_dim
        drop = self.config.dropout_rate if training else 0.0

        # Pre-norm attention
        normed = tf.keras.layers.LayerNormalization(epsilon=1e-6)(x)
        attn_out = tf.keras.layers.MultiHeadAttention(
            num_heads=self.config.num_heads,
            key_dim=embed_dim // self.config.num_heads,
            dropout=self.config.attention_dropout_rate,
        )(normed, normed, training=training)
        x = x + attn_out

        # Pre-norm FFN
        normed = tf.keras.layers.LayerNormalization(epsilon=1e-6)(x)
        ffn = tf.keras.layers.Dense(self.mlp_dim, activation="gelu")(normed)
        ffn = tf.keras.layers.Dropout(drop)(ffn)
        ffn = tf.keras.layers.Dense(embed_dim)(ffn)
        ffn = tf.keras.layers.Dropout(drop)(ffn)
        x = x + ffn

        return x


# ---------------------------------------------------------------------------
# Classification Head
# ---------------------------------------------------------------------------


def classification_head(x, embed_dim: int, num_classes: int, dropout_rate: float = 0.1):
    """Classification head: global average pooling + MLP.

    Args:
        x: Input tensor of shape (B, seq_len, embed_dim).
        embed_dim: Embedding dimension.
        num_classes: Number of output classes.
        dropout_rate: Dropout rate.

    Returns:
        Logits tensor of shape (B, num_classes).
    """
    import tensorflow as tf

    # Take the [CLS] token (first token)
    cls_token = x[:, 0]

    cls_token = tf.keras.layers.LayerNormalization(epsilon=1e-6)(cls_token)
    cls_token = tf.keras.layers.Dropout(dropout_rate)(cls_token)
    cls_token = tf.keras.layers.Dense(embed_dim, activation="gelu")(cls_token)
    cls_token = tf.keras.layers.Dropout(dropout_rate)(cls_token)
    logits = tf.keras.layers.Dense(num_classes)(cls_token)
    return logits


# ---------------------------------------------------------------------------
# Full ViT Model
# ---------------------------------------------------------------------------


def vit_classifier(config: ViTConfig):
    """Build a complete Vision Transformer classifier.

    Args:
        config: ViT configuration.

    Returns:
        Keras Model instance.
    """
    import tensorflow as tf

    input_shape = (config.image_size, config.image_size, config.num_channels)
    inputs = tf.keras.Input(shape=input_shape)

    patches = tf.keras.layers.Conv2D(
        config.embed_dim,
        kernel_size=config.patch_size,
        strides=config.patch_size,
        padding="valid",
        name="patch_projection",
    )(inputs)
    patches = tf.keras.layers.Reshape((config.num_patches, config.embed_dim), name="patch_sequence")(patches)

    def add_tokens(patch_tensor):
        batch = tf.shape(patch_tensor)[0]
        cls = tf.zeros((batch, 1, config.embed_dim), dtype=patch_tensor.dtype)
        return tf.concat([cls, patch_tensor], axis=1)

    x = tf.keras.layers.Lambda(add_tokens, name="add_cls_token")(patches)
    x = tf.keras.layers.Embedding(config.num_patches + 1, config.embed_dim, name="pos_embedding")(
        tf.range(config.num_patches + 1)
    ) + x

    x = tf.keras.layers.Dropout(config.dropout_rate)(x)

    # Transformer encoder blocks
    for _ in range(config.num_layers):
        block = TransformerEncoderBlock(config)
        x = block(x, training=True)

    # Classification head
    logits = classification_head(x, config.embed_dim, config.num_classes, config.dropout_rate)

    model = tf.keras.Model(inputs=inputs, outputs=logits, name="vit_classifier")
    return model


# ---------------------------------------------------------------------------
# Convenience builders
# ---------------------------------------------------------------------------


def build_vit_for_glacier(
    image_size: int = 256,
    patch_size: int = 16,
    num_channels: int = 11,
    num_classes: int = 2,
    num_layers: int = 12,
    embed_dim: int = 768,
    num_heads: int = 12,
    mlp_dim: int = 3072,
):
    """Build a ViT configured for glacier satellite image classification.

    Args:
        image_size: Input image spatial size.
        patch_size: Patch size for tokenization.
        num_channels: Number of input spectral channels.
        num_classes: Number of classes (default: glacier/not-glacier).
        num_layers: Number of transformer layers.
        embed_dim: Embedding dimension.
        num_heads: Number of attention heads.
        mlp_dim: MLP hidden dimension.

    Returns:
        Tuple of (ViTConfig, keras.Model).
    """
    config = ViTConfig(
        image_size=image_size,
        patch_size=patch_size,
        num_channels=num_channels,
        embed_dim=embed_dim,
        num_heads=num_heads,
        num_layers=num_layers,
        mlp_dim=mlp_dim,
        num_classes=num_classes,
    )

    errors = config.validate()
    if errors:
        raise ValueError(f"Invalid config: {'; '.join(errors)}")

    model = vit_classifier(config)
    logger.info(
        "Built ViT: image=%d, patch=%d, layers=%d, heads=%d, params=%s",
        image_size,
        patch_size,
        num_layers,
        num_heads,
        f"{model.count_params():,}",
    )
    return model


# ---------------------------------------------------------------------------
# Training Loop
# ---------------------------------------------------------------------------


def train_vit(
    model,
    train_data,
    val_data,
    config: ViTConfig,
    epochs: int = 100,
    save_dir: str = "models",
    patience: int = 15,
):
    """Train the ViT model with cosine learning rate schedule and warmup.

    Args:
        model: Compiled Keras model.
        train_data: Training dataset or generator.
        val_data: Validation dataset or generator.
        config: ViT configuration.
        epochs: Maximum training epochs.
        save_dir: Directory to save checkpoints.
        patience: Early stopping patience.

    Returns:
        Training history dictionary.
    """
    from pathlib import Path

    import tensorflow as tf

    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)

    # Cosine decay with warmup
    total_steps = epochs * max(1, len(train_data) if hasattr(train_data, "__len__") else 100)

    def lr_schedule(epoch, lr):
        if epoch < config.warmup_steps:
            return config.learning_rate * (epoch + 1) / config.warmup_steps
        progress = (epoch - config.warmup_steps) / max(1, total_steps - config.warmup_steps)
        return config.learning_rate * 0.5 * (1 + math.cos(math.pi * progress))

    lr_callback = tf.keras.callbacks.LearningRateScheduler(lr_schedule, verbose=0)

    checkpoint_cb = tf.keras.callbacks.ModelCheckpoint(
        str(save_path / "vit_best.keras"),
        monitor="val_loss",
        save_best_only=True,
        verbose=1,
    )

    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=patience,
        restore_best_weights=True,
        verbose=1,
    )

    tensorboard_cb = tf.keras.callbacks.TensorBoard(
        log_dir=str(save_path / "tensorboard_vit"),
        histogram_freq=1,
    )

    optimizer = tf.keras.optimizers.AdamW(
        learning_rate=config.learning_rate,
        weight_decay=config.weight_decay,
    )

    loss_fn = tf.keras.losses.CategoricalCrossentropy(from_logits=True, label_smoothing=config.label_smoothing)

    model.compile(optimizer=optimizer, loss=loss_fn, metrics=["accuracy"])

    history = model.fit(
        train_data,
        validation_data=val_data,
        epochs=epochs,
        callbacks=[lr_callback, checkpoint_cb, early_stop, tensorboard_cb],
        verbose=1,
    )

    logger.info("Training complete. Best val_loss: %.4f", min(history.history.get("val_loss", [float("inf")])))
    return history.history


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def evaluate_vit(model, test_data, class_names: list[str] | None = None):
    """Evaluate a trained ViT model.

    Args:
        model: Trained Keras model.
        test_data: Test dataset or generator.
        class_names: Optional list of class names for reporting.

    Returns:
        Dictionary with evaluation metrics.
    """

    results = model.evaluate(test_data, verbose=0)
    metric_names = model.metrics_names
    metrics = dict(zip(metric_names, results))

    # Compute per-class accuracy if predictions available
    if hasattr(test_data, "__len__") and len(test_data) > 0:
        y_true_all: list[np.ndarray] = []
        y_pred_all: list[np.ndarray] = []

        for batch in test_data:
            if isinstance(batch, tuple) and len(batch) == 2:
                x_batch, y_batch = batch
                y_pred = model.predict(x_batch, verbose=0)
                y_true_all.append(np.argmax(y_batch, axis=-1))
                y_pred_all.append(np.argmax(y_pred, axis=-1))

        if y_true_all:
            y_true_arr = np.concatenate(y_true_all)
            y_pred_arr = np.concatenate(y_pred_all)

            num_classes = max(y_true_arr.max(), y_pred_arr.max()) + 1
            per_class_acc = {}
            for c in range(num_classes):
                mask = y_true_arr == c
                if mask.sum() > 0:
                    name = class_names[c] if class_names and c < len(class_names) else f"class_{c}"
                    per_class_acc[name] = float((y_pred_arr[mask] == c).mean())

            metrics["per_class_accuracy"] = per_class_acc

            # Overall confusion matrix
            cm = np.zeros((num_classes, num_classes), dtype=int)
            for t, p in zip(y_true_arr, y_pred_arr):
                cm[t, p] += 1
            metrics["confusion_matrix"] = cm.tolist()

    logger.info("Evaluation complete: %s", metrics)
    return metrics
