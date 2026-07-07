# -*- coding: utf-8 -*-
"""Denoising Diffusion Probabilistic Model (DDPM) for image super-resolution.

Implements the forward diffusion process, learned reverse denoising process,
U-Net backbone with time conditioning, noise schedules, and sampling for
satellite image super-resolution of glacier imagery.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

__all__ = [
    "DiffusionConfig",
    "get_noise_schedule",
    "forward_diffusion",
    "build_unet",
    "sample_ddpm",
    "train_diffusion_step",
    "build_super_res_diffusion",
]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class DiffusionConfig:
    """Configuration for diffusion model."""

    image_size: int = 256
    low_res_size: int = 64
    num_channels: int = 11
    timesteps: int = 1000
    beta_start: float = 1e-4
    beta_end: float = 0.02
    schedule_type: str = "linear"  # linear, cosine
    base_channels: int = 128
    channel_mults: tuple[int, ...] = (1, 2, 4, 8)
    num_res_blocks: int = 2
    attention_resolutions: tuple[int, ...] = (32, 16)
    dropout_rate: float = 0.0
    ema_decay: float = 0.9999
    learning_rate: float = 2e-4
    batch_size: int = 4

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.image_size % 4 != 0:
            errors.append(f"image_size ({self.image_size}) must be divisible by 4")
        if self.timesteps < 1:
            errors.append("timesteps must be >= 1")
        if self.schedule_type not in ("linear", "cosine"):
            errors.append(f"Unknown schedule_type: {self.schedule_type}")
        return errors


# ---------------------------------------------------------------------------
# Noise Schedules
# ---------------------------------------------------------------------------


def get_noise_schedule(config: DiffusionConfig):
    """Compute noise schedule (betas, alphas, alpha_cumprod).

    Args:
        config: Diffusion configuration.

    Returns:
        Dictionary with numpy arrays: betas, alphas, alpha_cumprod,
        sqrt_alpha_cumprod, sqrt_one_minus_alpha_cumprod.
    """
    t = config.timesteps

    if config.schedule_type == "linear":
        betas = np.linspace(config.beta_start, config.beta_end, t, dtype=np.float64)
    elif config.schedule_type == "cosine":
        steps = np.arange(t + 1, dtype=np.float64)
        f = np.cos((steps / t + 0.008) / 1.008 * math.pi / 2) ** 2
        alphas_cumprod = f / f[0]
        betas = 1.0 - (alphas_cumprod[1:] / alphas_cumprod[:-1])
        betas = np.clip(betas, 0.0, 0.999)
    else:
        raise ValueError(f"Unknown schedule: {config.schedule_type}")

    alphas = 1.0 - betas
    alpha_cumprod = np.cumprod(alphas)

    return {
        "betas": betas.astype(np.float32),
        "alphas": alphas.astype(np.float32),
        "alpha_cumprod": alpha_cumprod.astype(np.float32),
        "sqrt_alpha_cumprod": np.sqrt(alpha_cumprod).astype(np.float32),
        "sqrt_one_minus_alpha_cumprod": np.sqrt(1.0 - alpha_cumprod).astype(np.float32),
    }


# ---------------------------------------------------------------------------
# Forward Diffusion Process
# ---------------------------------------------------------------------------


def forward_diffusion(x_0, t, noise_schedule, noise: np.ndarray | None = None):
    """Add noise to image at timestep t (q(x_t | x_0)).

    Args:
        x_0: Original image tensor of shape (B, H, W, C).
        t: Timestep tensor of shape (B,).
        noise_schedule: Dictionary from get_noise_schedule.
        noise: Optional pre-generated noise (same shape as x_0).

    Returns:
        Tuple of (noisy_image, noise).
    """
    import tensorflow as tf

    if noise is None:
        noise = tf.random.normal(tf.shape(x_0))

    sqrt_alpha = tf.gather(tf.constant(noise_schedule["sqrt_alpha_cumprod"]), t)
    sqrt_one_minus_alpha = tf.gather(tf.constant(noise_schedule["sqrt_one_minus_alpha_cumprod"]), t)

    # Reshape for broadcasting: (B,) -> (B, 1, 1, 1)
    ndim = len(x_0.shape)
    shape = [-1] + [1] * (ndim - 1)
    sqrt_alpha = tf.reshape(sqrt_alpha, shape)
    sqrt_one_minus_alpha = tf.reshape(sqrt_one_minus_alpha, shape)

    x_t = sqrt_alpha * x_0 + sqrt_one_minus_alpha * noise
    return x_t, noise


# ---------------------------------------------------------------------------
# U-Net Architecture
# ---------------------------------------------------------------------------


def _residual_block(x, channels: int, time_emb, dropout_rate: float = 0.0):
    """Residual block with time embedding injection."""
    import tensorflow as tf

    h = tf.keras.layers.GroupNormalization(groups=min(32, channels))(x)
    h = tf.keras.layers.Activation("swish")(h)
    h = tf.keras.layers.Conv2D(channels, 3, padding="same")(h)

    # Time embedding projection
    time_proj = tf.keras.layers.Dense(channels)(time_emb)
    time_proj = tf.keras.layers.Activation("swish")(time_proj)
    time_proj = tf.keras.layers.Reshape((1, 1, channels))(time_proj)
    h = h + time_proj

    h = tf.keras.layers.GroupNormalization(groups=min(32, channels))(h)
    h = tf.keras.layers.Activation("swish")(h)
    if dropout_rate > 0:
        h = tf.keras.layers.Dropout(dropout_rate)(h)
    h = tf.keras.layers.Conv2D(channels, 3, padding="same")(h)

    # Skip connection
    if x.shape[-1] != channels:
        x = tf.keras.layers.Conv2D(channels, 1, padding="same")(x)

    return x + h


def _self_attention(x, channels: int):
    """Self-attention for spatial features."""
    import tensorflow as tf

    batch_size = tf.shape(x)[0]
    h = tf.keras.layers.GroupNormalization(groups=min(32, channels))(x)
    q = tf.keras.layers.Dense(channels)(h)
    k = tf.keras.layers.Dense(channels)(h)
    v = tf.keras.layers.Dense(channels)(h)

    # Reshape to (B, HW, C)
    q = tf.reshape(q, (batch_size, -1, channels))
    k = tf.reshape(k, (batch_size, -1, channels))
    v = tf.reshape(v, (batch_size, -1, channels))

    scale = math.sqrt(channels)
    attn = tf.matmul(q, k, transpose_b=True) / scale
    attn = tf.nn.softmax(attn, axis=-1)

    out = tf.matmul(attn, v)
    hw = tf.shape(x)[1]
    out = tf.reshape(out, (batch_size, hw, hw, channels))

    out = tf.keras.layers.Dense(channels)(out)
    return x + out


def _time_embedding(timesteps: int, embed_dim: int):
    """Sinusoidal time embedding."""
    import tensorflow as tf

    half_dim = embed_dim // 2
    emb = math.log(10000) / (half_dim - 1)
    emb = tf.exp(tf.range(half_dim, dtype=tf.float32) * -emb)
    emb = tf.cast(timesteps, tf.float32)[:, None] * emb[None, :]
    emb = tf.concat([tf.sin(emb), tf.cos(emb)], axis=-1)
    return emb


def build_unet(config: DiffusionConfig):
    """Build U-Net for diffusion denoising with time conditioning.

    Args:
        config: Diffusion configuration.

    Returns:
        Keras Model with inputs (noisy_image, timestep) and output (predicted_noise).
    """
    import tensorflow as tf

    img_input = tf.keras.Input(shape=(config.image_size, config.image_size, config.num_channels))
    t_input = tf.keras.Input(shape=(), dtype=tf.int32)

    # Time embedding
    time_emb = _time_embedding(t_input, config.base_channels * 4)
    time_emb = tf.keras.layers.Dense(config.base_channels * 4, activation="swish")(time_emb)
    time_emb = tf.keras.layers.Dense(config.base_channels * 4)(time_emb)

    # --- Encoder ---
    channels_list: list[int] = []
    skip_connections: list = []

    h = tf.keras.layers.Conv2D(config.base_channels, 3, padding="same")(img_input)
    channels_list.append(config.base_channels)

    current_res = config.image_size
    channels = config.base_channels

    for i, mult in enumerate(config.channel_mults):
        channels = config.base_channels * mult
        for _ in range(config.num_res_blocks):
            h = _residual_block(h, channels, time_emb, config.dropout_rate)
            if current_res in config.attention_resolutions:
                h = _self_attention(h, channels)
            skip_connections.append(h)
            channels_list.append(channels)

        if i < len(config.channel_mults) - 1:
            h = tf.keras.layers.Conv2D(channels, 3, strides=2, padding="same")(h)
            current_res //= 2

    # --- Bottleneck ---
    h = _residual_block(h, channels, time_emb, config.dropout_rate)
    h = _self_attention(h, channels)
    h = _residual_block(h, channels, time_emb, config.dropout_rate)

    # --- Decoder ---
    for i in reversed(range(len(config.channel_mults))):
        channels = config.base_channels * config.channel_mults[i]

        for _ in range(config.num_res_blocks):
            if skip_connections:
                h = tf.keras.layers.Concatenate()([h, skip_connections.pop()])
            h = _residual_block(h, channels, time_emb, config.dropout_rate)
            if current_res in config.attention_resolutions:
                h = _self_attention(h, channels)

        if i > 0:
            h = tf.keras.layers.UpSampling2D(2, interpolation="nearest")(h)
            current_res *= 2

    h = tf.keras.layers.GroupNormalization(groups=min(32, channels))(h)
    h = tf.keras.layers.Activation("swish")(h)
    output = tf.keras.layers.Conv2D(config.num_channels, 3, padding="same")(h)

    model = tf.keras.Model(inputs=[img_input, t_input], outputs=output, name="ddpm_unet")
    return model


# ---------------------------------------------------------------------------
# Super-Resolution U-Net
# ---------------------------------------------------------------------------


def build_super_res_diffusion(config: DiffusionConfig):
    """Build super-resolution diffusion model that takes low-res input.

    Concatenates the low-res input with the noisy image at the input.

    Returns:
        Tuple of (config, model) where model accepts (noisy_img, low_res_img, timestep).
    """
    import tensorflow as tf

    low_res_input = tf.keras.Input(shape=(config.low_res_size, config.low_res_size, config.num_channels))
    noisy_input = tf.keras.Input(shape=(config.image_size, config.image_size, config.num_channels))
    t_input = tf.keras.Input(shape=(), dtype=tf.int32)

    # Upsample low-res to match noisy input size
    upsampled = tf.keras.layers.UpSampling2D(size=config.image_size // config.low_res_size, interpolation="bilinear")(
        low_res_input
    )

    # Concatenate along channel dimension
    tf.keras.layers.Concatenate()([noisy_input, upsampled])

    # Create a modified config with doubled input channels
    sr_config = DiffusionConfig(**{**config.__dict__, "num_channels": config.num_channels * 2})

    # Build U-Net with merged input
    build_unet(sr_config)

    # We need to rewire: inputs are merged, but unet expects single input
    # Build the U-Net with merged channels
    img_input = tf.keras.Input(shape=(config.image_size, config.image_size, config.num_channels * 2))
    t_emb = _time_embedding(t_input, config.base_channels * 4)
    t_emb = tf.keras.layers.Dense(config.base_channels * 4, activation="swish")(t_emb)
    t_emb = tf.keras.layers.Dense(config.base_channels * 4)(t_emb)

    h = tf.keras.layers.Conv2D(config.base_channels, 3, padding="same")(img_input)

    skip_connections = []
    channels = config.base_channels
    current_res = config.image_size

    for i, mult in enumerate(config.channel_mults):
        channels = config.base_channels * mult
        for _ in range(config.num_res_blocks):
            h = _residual_block(h, channels, t_emb, config.dropout_rate)
            skip_connections.append(h)
        if i < len(config.channel_mults) - 1:
            h = tf.keras.layers.Conv2D(channels, 3, strides=2, padding="same")(h)
            current_res //= 2

    # Bottleneck
    h = _residual_block(h, channels, t_emb, config.dropout_rate)

    # Decoder
    for i in reversed(range(len(config.channel_mults))):
        channels = config.base_channels * config.channel_mults[i]
        for _ in range(config.num_res_blocks):
            if skip_connections:
                h = tf.keras.layers.Concatenate()([h, skip_connections.pop()])
            h = _residual_block(h, channels, t_emb, config.dropout_rate)
        if i > 0:
            h = tf.keras.layers.UpSampling2D(2, interpolation="nearest")(h)

    h = tf.keras.layers.GroupNormalization(groups=min(32, channels))(h)
    h = tf.keras.layers.Activation("swish")(h)
    output = tf.keras.layers.Conv2D(config.num_channels, 3, padding="same")(h)

    model = tf.keras.Model(
        inputs=[noisy_input, low_res_input, t_input],
        outputs=output,
        name="sr_diffusion",
    )
    return config, model


# ---------------------------------------------------------------------------
# Sampling (Reverse Process)
# ---------------------------------------------------------------------------


def sample_ddpm(
    model,
    low_res: np.ndarray | None,
    config: DiffusionConfig,
    num_samples: int = 1,
    guidance_scale: float = 1.0,
    return_all_steps: bool = False,
):
    """Generate images via DDPM sampling (reverse diffusion).

    Args:
        model: Trained denoising model.
        low_res: Optional low-resolution input for super-resolution.
        config: Diffusion configuration.
        num_samples: Number of samples to generate.
        guidance_scale: Classifier-free guidance scale.
        return_all_steps: If True, return all intermediate steps.

    Returns:
        Generated images as numpy array of shape (B, H, W, C) in [0, 1].
    """
    import tensorflow as tf

    noise_schedule = get_noise_schedule(config)
    betas = tf.constant(noise_schedule["betas"], dtype=tf.float32)
    tf.constant(noise_schedule["alpha_cumprod"], dtype=tf.float32)
    sqrt_one_minus_alpha_cumprod = tf.constant(noise_schedule["sqrt_one_minus_alpha_cumprod"], dtype=tf.float32)
    sqrt_recip_alpha = tf.constant(1.0 / np.sqrt(noise_schedule["alphas"]), dtype=tf.float32)

    # Start from pure noise
    shape = (num_samples, config.image_size, config.image_size, config.num_channels)
    x_t = tf.random.normal(shape)

    all_steps = []

    for t in reversed(range(config.timesteps)):
        t_batch = tf.constant([t] * num_samples, dtype=tf.int32)

        # Predict noise
        if low_res is not None:
            low_res_batch = tf.constant(low_res, dtype=tf.float32)
            if len(low_res_batch.shape) == 3:
                low_res_batch = tf.repeat(low_res_batch[None], num_samples, axis=0)
            pred_noise = model([x_t, low_res_batch, t_batch], training=False)
        else:
            pred_noise = model([x_t, t_batch], training=False)

        # DDPM update
        beta_t = tf.gather(betas, t)
        sqrt_recip_alpha_t = tf.gather(sqrt_recip_alpha, t)
        sqrt_one_minus_alpha_t = tf.gather(sqrt_one_minus_alpha_cumprod, t)

        mean = sqrt_recip_alpha_t * (x_t - beta_t / sqrt_one_minus_alpha_t * pred_noise)

        if t > 0:
            noise = tf.random.normal(shape)
            sigma = tf.sqrt(beta_t)
            x_t = mean + sigma * noise
        else:
            x_t = mean

        if return_all_steps:
            all_steps.append(x_t.numpy())

    if return_all_steps:
        return np.stack(all_steps, axis=0)

    # Clamp to [0, 1]
    x_t = tf.clip_by_value(x_t, 0.0, 1.0)
    return x_t.numpy()


# ---------------------------------------------------------------------------
# Training Step
# ---------------------------------------------------------------------------


def train_diffusion_step(model, batch, config: DiffusionConfig):
    """Single training step for the diffusion model.

    Args:
        model: U-Net denoising model.
        batch: Batch of clean images of shape (B, H, W, C).
        config: Diffusion configuration.

    Returns:
        Scalar loss value.
    """
    import tensorflow as tf

    noise_schedule = get_noise_schedule(config)
    batch_size = tf.shape(batch)[0]

    # Sample random timesteps
    t = tf.random.uniform((batch_size,), 0, config.timesteps, dtype=tf.int32)

    # Generate noise and create noisy version
    noise = tf.random.normal(tf.shape(batch))
    x_t, _ = forward_diffusion(batch, t, noise_schedule, noise)

    # Predict noise
    pred_noise = model([x_t, t], training=True)

    # MSE loss
    loss = tf.reduce_mean(tf.square(pred_noise - noise))
    return loss


# ---------------------------------------------------------------------------
# Convenience Builder
# ---------------------------------------------------------------------------


def build_and_train_diffusion(
    config: DiffusionConfig | None = None,
    train_dataset=None,
    val_dataset=None,
    epochs: int = 200,
    save_dir: str = "models",
):
    """Build and train a diffusion model end-to-end.

    Args:
        config: Optional diffusion config (uses defaults if None).
        train_dataset: Training tf.data.Dataset.
        val_dataset: Validation tf.data.Dataset.
        epochs: Training epochs.
        save_dir: Directory to save model.

    Returns:
        Tuple of (config, model, training_history).
    """
    from pathlib import Path

    import tensorflow as tf

    if config is None:
        config = DiffusionConfig()

    errors = config.validate()
    if errors:
        raise ValueError(f"Invalid config: {'; '.join(errors)}")

    model = build_unet(config)
    optimizer = tf.keras.optimizers.Adam(learning_rate=config.learning_rate)

    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)

    history = {"loss": [], "val_loss": []}

    for epoch in range(epochs):
        epoch_losses = []
        for batch in train_dataset:
            with tf.GradientTape() as tape:
                loss = train_diffusion_step(model, batch, config)
            grads = tape.gradient(loss, model.trainable_variables)
            optimizer.apply_gradients(zip(grads, model.trainable_variables))
            epoch_losses.append(float(loss))

        avg_loss = np.mean(epoch_losses)
        history["loss"].append(avg_loss)

        # Validation
        if val_dataset is not None:
            val_losses = []
            for batch in val_dataset:
                loss = train_diffusion_step(model, batch, config)
                val_losses.append(float(loss))
            avg_val_loss = np.mean(val_losses)
            history["val_loss"].append(avg_val_loss)
            logger.info("Epoch %d/%d — loss: %.4f, val_loss: %.4f", epoch + 1, epochs, avg_loss, avg_val_loss)
        else:
            logger.info("Epoch %d/%d — loss: %.4f", epoch + 1, epochs, avg_loss)

        # Save checkpoint
        if (epoch + 1) % 10 == 0:
            model.save_weights(str(save_path / f"diffusion_epoch_{epoch + 1}.weights.h5"))

    model.save_weights(str(save_path / "diffusion_final.weights.h5"))
    return config, model, history
