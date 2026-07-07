# -*- coding: utf-8 -*-
"""Additional segmentation architectures for GlacierNET-KZ.

FCN, DeepLabV3, PSPNet, LinkNet, SegNet, Attention FPN, and HRNet-style
models with a shared backbone loader, model registry, and complexity estimation.
TensorFlow is imported lazily inside each function.
"""

from __future__ import annotations

__all__ = [
    "get_backbone",
    "build_fcn",
    "build_deeplabv3",
    "build_pspnet",
    "build_linknet",
    "build_segnet",
    "build_attention_fpn",
    "build_hrnet",
    "SEGMENTATION_MODELS",
    "list_segmentation_models",
    "get_model_info",
    "build_model_by_name",
    "count_parameters",
    "estimate_model_complexity",
]

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model metadata
# ---------------------------------------------------------------------------

_MODEL_INFO: dict[str, dict[str, Any]] = {
    "fcn": {
        "description": "Fully Convolutional Network with skip connections from encoder stages.",
        "complexity": "medium",
        "param_count_estimate": "30M\u2013140M (backbone-dependent)",
        "recommended_input_size": 256,
    },
    "deeplabv3": {
        "description": "DeepLabV3 with Atrous Spatial Pyramid Pooling for multi-scale context.",
        "complexity": "high",
        "param_count_estimate": "40M\u2013150M (backbone-dependent)",
        "recommended_input_size": 512,
    },
    "pspnet": {
        "description": "Pyramid Scene Parsing Network with pyramid pooling module.",
        "complexity": "high",
        "param_count_estimate": "50M\u2013160M (backbone-dependent)",
        "recommended_input_size": 512,
    },
    "linknet": {
        "description": "LinkNet encoder-decoder with transposed convolution skip links.",
        "complexity": "medium",
        "param_count_estimate": "25M\u2013120M (backbone-dependent)",
        "recommended_input_size": 256,
    },
    "segnet": {
        "description": "SegNet with max-pooling index-based up-sampling.",
        "complexity": "medium",
        "param_count_estimate": "15M\u201360M",
        "recommended_input_size": 256,
    },
    "attention_fpn": {
        "description": "Attention Feature Pyramid Network with channel/spatial attention on fused features.",
        "complexity": "high",
        "param_count_estimate": "35M\u2013130M (backbone-dependent)",
        "recommended_input_size": 512,
    },
    "hrnet": {
        "description": "HRNet-style high-resolution network maintaining parallel feature streams.",
        "complexity": "high",
        "param_count_estimate": "25M\u201365M",
        "recommended_input_size": 256,
    },
}

# Channel sets used to identify skip feature maps in common backbones.
_SKIP_CHANNELS = frozenset({64, 128, 256, 512, 1024, 2048})


# ---------------------------------------------------------------------------
# Shared backbone loader
# ---------------------------------------------------------------------------


def get_backbone(
    name: str,
    weights: str = "imagenet",
    input_shape: tuple[int, int, int] | None = None,
) -> Any:
    """Return a pre-trained backbone from ``tf.keras.applications``.

    Supported: ``resnet50``, ``vgg16``, ``mobilenetv2``, ``efficientnetb0``.
    """
    import tensorflow as tf

    key = name.lower().replace("-", "").replace("_", "")
    builders: dict[str, Callable] = {
        "resnet50": tf.keras.applications.ResNet50,
        "vgg16": tf.keras.applications.VGG16,
        "mobilenetv2": tf.keras.applications.MobileNetV2,
        "efficientnetb0": tf.keras.applications.EfficientNetB0,
    }
    if key not in builders:
        raise ValueError(f"Unknown backbone '{name}'. Choose from: {list(builders.keys())}")
    kwargs: dict[str, Any] = {"weights": weights, "include_top": False}
    if input_shape is not None:
        kwargs["input_shape"] = input_shape
    logger.info("Loading backbone '%s' with weights=%s", name, weights)
    return builders[key](**kwargs)


# ---------------------------------------------------------------------------
# Utility layers
# ---------------------------------------------------------------------------


def _bn_relu(x: Any, filters: int, name: str | None = None) -> Any:
    """Conv3x3 \u2192 BatchNorm \u2192 ReLU."""
    import tensorflow as tf

    x = tf.keras.layers.Conv2D(filters, 3, padding="same", use_bias=False, name=f"{name}_conv" if name else None)(x)
    x = tf.keras.layers.BatchNormalization(name=f"{name}_bn" if name else None)(x)
    x = tf.keras.layers.ReLU(name=f"{name}_relu" if name else None)(x)
    return x


def _upsample(x: Any, factor: int, name: str | None = None) -> Any:
    """Bilinear up-sample by *factor*."""
    import tensorflow as tf

    return tf.keras.layers.UpSampling2D(size=factor, interpolation="bilinear", name=name)(x)


def _collect_skips(encoder: Any, count: int) -> list[Any]:
    """Extract *count* skip tensors from encoder layers by channel signature."""
    skips: list[Any] = []
    for layer in encoder.layers:
        if not hasattr(layer, "output_shape") or layer.output_shape is None:
            continue
        if not isinstance(layer.output_shape, tuple) or len(layer.output_shape) != 4:
            continue
        if layer.output_shape[-1] in _SKIP_CHANNELS:
            skips.append(layer.output)
            if len(skips) >= count:
                break
    while len(skips) < count:
        skips.insert(0, encoder.output)
    return skips


def _aspp(x: Any, filters: int = 256, name: str = "aspp") -> Any:
    """Atrous Spatial Pyramid Pooling (rates 1/6/12/18 + image-level)."""
    import tensorflow as tf

    h, w = x.shape[1] or 1, x.shape[2] or 1
    branches: list[Any] = []

    b1 = tf.keras.layers.Conv2D(filters, 1, padding="same", use_bias=False, name=f"{name}_1x1")(x)
    b1 = tf.keras.layers.BatchNormalization(name=f"{name}_1x1_bn")(b1)
    b1 = tf.keras.layers.ReLU(name=f"{name}_1x1_relu")(b1)
    branches.append(b1)

    for rate in (6, 12, 18):
        b = tf.keras.layers.Conv2D(
            filters, 3, padding="same", dilation_rate=rate, use_bias=False, name=f"{name}_d{rate}"
        )(x)
        b = tf.keras.layers.BatchNormalization(name=f"{name}_d{rate}_bn")(b)
        b = tf.keras.layers.ReLU(name=f"{name}_d{rate}_relu")(b)
        branches.append(b)

    b_img = tf.keras.layers.GlobalAveragePooling2D(name=f"{name}_gap")(x)
    b_img = tf.keras.layers.Reshape((1, 1, -1), name=f"{name}_reshape")(b_img)
    b_img = tf.keras.layers.Conv2D(filters, 1, use_bias=False, name=f"{name}_img")(b_img)
    b_img = tf.keras.layers.BatchNormalization(name=f"{name}_img_bn")(b_img)
    b_img = tf.keras.layers.ReLU(name=f"{name}_img_relu")(b_img)
    b_img = tf.keras.layers.UpSampling2D(size=(h, w), interpolation="bilinear", name=f"{name}_img_up")(b_img)
    branches.append(b_img)

    fused = tf.keras.layers.Concatenate(name=f"{name}_concat")(branches)
    fused = tf.keras.layers.Conv2D(filters, 1, use_bias=False, name=f"{name}_fuse")(fused)
    fused = tf.keras.layers.BatchNormalization(name=f"{name}_fuse_bn")(fused)
    fused = tf.keras.layers.ReLU(name=f"{name}_fuse_relu")(fused)
    return fused


def _ppm(x: Any, pool_sizes: tuple[int, ...] = (1, 2, 3, 6), name: str = "ppm") -> Any:
    """Pyramid Pooling Module: multi-scale avg-pool \u2192 1\u00d71 conv \u2192 up-sample \u2192 concat."""
    import tensorflow as tf

    channels = x.shape[-1] or 256
    branches: list[Any] = [x]
    for size in pool_sizes:
        gap = tf.keras.layers.AveragePooling2D(pool_size=size, padding="same", name=f"{name}_pool{size}")(x)
        gap = tf.keras.layers.Conv2D(channels // 4, 1, use_bias=False, name=f"{name}_conv{size}")(gap)
        gap = tf.keras.layers.BatchNormalization(name=f"{name}_bn{size}")(gap)
        gap = tf.keras.layers.ReLU(name=f"{name}_relu{size}")(gap)
        gap = tf.keras.layers.UpSampling2D(
            size=(x.shape[1] // gap.shape[1] or 1, x.shape[2] // gap.shape[2] or 1),
            interpolation="bilinear",
            name=f"{name}_up{size}",
        )(gap)
        branches.append(gap)
    return tf.keras.layers.Concatenate(name=f"{name}_concat")(branches)


def _channel_attention(x: Any, reduction: int = 16, name: str = "ca") -> Any:
    """Squeeze-and-Excitation channel attention."""
    import tensorflow as tf

    ch = x.shape[-1] or 64
    squeeze = max(ch // reduction, 1)
    gap = tf.keras.layers.GlobalAveragePooling2D(name=f"{name}_gap")(x)
    d1 = tf.keras.layers.Dense(squeeze, activation="relu", name=f"{name}_fc1")(gap)
    d2 = tf.keras.layers.Dense(ch, activation="sigmoid", name=f"{name}_fc2")(d1)
    d2 = tf.keras.layers.Reshape((1, 1, ch), name=f"{name}_reshape")(d2)
    return tf.keras.layers.Multiply(name=f"{name}_scale")([x, d2])


def _spatial_attention(x: Any, kernel_size: int = 7, name: str = "sa") -> Any:
    """Spatial attention: channel avg+max pool \u2192 7\u00d77 conv \u2192 sigmoid."""
    import tensorflow as tf

    avg = tf.keras.layers.Lambda(lambda t: tf.reduce_mean(t, axis=-1, keepdims=True), name=f"{name}_avg")(x)
    mx = tf.keras.layers.Lambda(lambda t: tf.reduce_max(t, axis=-1, keepdims=True), name=f"{name}_max")(x)
    cat = tf.keras.layers.Concatenate(name=f"{name}_cat")([avg, mx])
    att = tf.keras.layers.Conv2D(1, kernel_size, padding="same", activation="sigmoid", name=f"{name}_conv")(cat)
    return tf.keras.layers.Multiply(name=f"{name}_scale")([x, att])


# ---------------------------------------------------------------------------
# FCN
# ---------------------------------------------------------------------------


def build_fcn(
    input_shape: tuple[int, int, int],
    num_classes: int = 1,
    backbone: str = "resnet50",
) -> Any:
    """Fully Convolutional Network with multi-scale skip connections."""
    import tensorflow as tf

    inputs = tf.keras.layers.Input(shape=input_shape, name="fcn_input")
    encoder = get_backbone(backbone, input_shape=input_shape)
    encoder.trainable = False

    skips = _collect_skips(encoder, 3)
    skip_early = _upsample(skips[0], 4, name="fcn_skip_early")
    skip_mid = _upsample(skips[1], 2, name="fcn_skip_mid")
    skip_late = skips[2]

    skip_early = tf.keras.layers.Conv2D(256, 1, padding="same", name="fcn_proj_e")(skip_early)
    skip_mid = tf.keras.layers.Conv2D(256, 1, padding="same", name="fcn_proj_m")(skip_mid)
    skip_late = tf.keras.layers.Conv2D(256, 1, padding="same", name="fcn_proj_l")(skip_late)

    fused = tf.keras.layers.Concatenate(name="fcn_concat")([skip_early, skip_mid, skip_late])
    fused = _bn_relu(fused, 512, name="fcn_dec")
    fused = _upsample(fused, input_shape[0] // fused.shape[1] or 4, name="fcn_up")

    outputs = tf.keras.layers.Conv2D(num_classes, 1, activation="sigmoid", name="fcn_output")(fused)
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="fcn")
    logger.info("Built FCN with backbone '%s' (%d classes)", backbone, num_classes)
    return model


# ---------------------------------------------------------------------------
# DeepLabV3
# ---------------------------------------------------------------------------


def build_deeplabv3(
    input_shape: tuple[int, int, int],
    num_classes: int = 1,
    backbone: str = "resnet50",
) -> Any:
    """DeepLabV3 with Atrous Spatial Pyramid Pooling."""
    import tensorflow as tf

    inputs = tf.keras.layers.Input(shape=input_shape, name="dlv3_input")
    encoder = get_backbone(backbone, input_shape=input_shape)
    encoder.trainable = False

    x = _aspp(encoder.output, 256, name="dlv3_aspp")
    x = _upsample(x, input_shape[0] // (x.shape[1] or 1) or 4, name="dlv3_up")
    outputs = tf.keras.layers.Conv2D(num_classes, 1, activation="sigmoid", name="dlv3_output")(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="deeplabv3")
    logger.info("Built DeepLabV3 with backbone '%s' (%d classes)", backbone, num_classes)
    return model


# ---------------------------------------------------------------------------
# PSPNet
# ---------------------------------------------------------------------------


def build_pspnet(
    input_shape: tuple[int, int, int],
    num_classes: int = 1,
    backbone: str = "resnet50",
) -> Any:
    """Pyramid Scene Parsing Network with pyramid pooling module."""
    import tensorflow as tf

    inputs = tf.keras.layers.Input(shape=input_shape, name="psp_input")
    encoder = get_backbone(backbone, input_shape=input_shape)
    encoder.trainable = False

    x = _ppm(encoder.output, (1, 2, 3, 6), name="psp_ppm")
    x = _bn_relu(x, 512, name="psp_dec")
    x = tf.keras.layers.Dropout(0.1, name="psp_drop")(x)
    x = _upsample(x, input_shape[0] // (x.shape[1] or 1) or 4, name="psp_up")
    outputs = tf.keras.layers.Conv2D(num_classes, 1, activation="sigmoid", name="psp_output")(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="pspnet")
    logger.info("Built PSPNet with backbone '%s' (%d classes)", backbone, num_classes)
    return model


# ---------------------------------------------------------------------------
# LinkNet
# ---------------------------------------------------------------------------


def _linknet_dec_block(x: Any, skip: Any, filters: int, name: str) -> Any:
    """Decoder: 1\u00d71 proj \u2192 up2\u00d7 \u2192 3\u00d73 conv \u2192 + skip \u2192 ReLU."""
    import tensorflow as tf

    x = tf.keras.layers.Conv2D(filters // 4, 1, padding="same", use_bias=False, name=f"{name}_proj")(x)
    x = tf.keras.layers.BatchNormalization(name=f"{name}_proj_bn")(x)
    x = tf.keras.layers.ReLU(name=f"{name}_proj_relu")(x)
    x = tf.keras.layers.UpSampling2D(2, interpolation="bilinear", name=f"{name}_up")(x)
    x = tf.keras.layers.Conv2D(filters // 4, 3, padding="same", use_bias=False, name=f"{name}_c1")(x)
    x = tf.keras.layers.BatchNormalization(name=f"{name}_c1_bn")(x)
    x = tf.keras.layers.ReLU(name=f"{name}_c1_relu")(x)
    x = tf.keras.layers.Conv2D(filters, 3, padding="same", use_bias=False, name=f"{name}_c2")(x)
    x = tf.keras.layers.BatchNormalization(name=f"{name}_c2_bn")(x)
    x = tf.keras.layers.ReLU(name=f"{name}_c2_relu")(x)
    if skip.shape[-1] != filters:
        skip = tf.keras.layers.Conv2D(filters, 1, padding="same", name=f"{name}_sp")(skip)
        skip = tf.keras.layers.BatchNormalization(name=f"{name}_sp_bn")(skip)
    x = tf.keras.layers.Add(name=f"{name}_add")([x, skip])
    return tf.keras.layers.ReLU(name=f"{name}_out_relu")(x)


def build_linknet(
    input_shape: tuple[int, int, int],
    num_classes: int = 1,
    backbone: str = "resnet50",
) -> Any:
    """LinkNet encoder-decoder with skip connections."""
    import tensorflow as tf

    inputs = tf.keras.layers.Input(shape=input_shape, name="link_input")
    encoder = get_backbone(backbone, input_shape=input_shape)
    encoder.trainable = False

    skips = _collect_skips(encoder, 4)
    filters = [256, 128, 64, 32]
    x = skips[-1]
    for idx, (f, sk) in enumerate(zip(reversed(filters), reversed(skips[:-1]))):
        x = _linknet_dec_block(x, sk, f, name=f"link{idx}")

    x = _upsample(x, input_shape[0] // (x.shape[1] or 1) or 4, name="link_up")
    outputs = tf.keras.layers.Conv2D(num_classes, 1, activation="sigmoid", name="link_output")(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="linknet")
    logger.info("Built LinkNet with backbone '%s' (%d classes)", backbone, num_classes)
    return model


# ---------------------------------------------------------------------------
# SegNet
# ---------------------------------------------------------------------------


def _seg_enc_block(x: Any, filters: int, name: str) -> tuple[Any, Any]:
    """Encoder: Conv3x3\u00d72 \u2192 BN \u2192 ReLU \u2192 MaxPool(2) with index."""
    import tensorflow as tf

    x = tf.keras.layers.Conv2D(filters, 3, padding="same", use_bias=False, name=f"{name}_c1")(x)
    x = tf.keras.layers.BatchNormalization(name=f"{name}_bn1")(x)
    x = tf.keras.layers.ReLU(name=f"{name}_r1")(x)
    x = tf.keras.layers.Conv2D(filters, 3, padding="same", use_bias=False, name=f"{name}_c2")(x)
    x = tf.keras.layers.BatchNormalization(name=f"{name}_bn2")(x)
    x = tf.keras.layers.ReLU(name=f"{name}_r2")(x)
    return tf.keras.layers.MaxPooling2D(2, name=f"{name}_pool")(x, return_indices=True)


def _seg_dec_block(x: Any, filters: int, name: str) -> Any:
    """Decoder: UpSample(2) \u2192 Conv3x3\u00d72 \u2192 BN \u2192 ReLU."""
    import tensorflow as tf

    x = tf.keras.layers.UpSampling2D(2, name=f"{name}_unpool")(x)
    x = tf.keras.layers.Conv2D(filters, 3, padding="same", use_bias=False, name=f"{name}_c1")(x)
    x = tf.keras.layers.BatchNormalization(name=f"{name}_bn1")(x)
    x = tf.keras.layers.ReLU(name=f"{name}_r1")(x)
    x = tf.keras.layers.Conv2D(filters, 3, padding="same", use_bias=False, name=f"{name}_c2")(x)
    x = tf.keras.layers.BatchNormalization(name=f"{name}_bn2")(x)
    x = tf.keras.layers.ReLU(name=f"{name}_r2")(x)
    return x


def build_segnet(input_shape: tuple[int, int, int], num_classes: int = 1) -> Any:
    """SegNet with VGG-style encoder and symmetric decoder."""
    import tensorflow as tf

    inputs = tf.keras.layers.Input(shape=input_shape, name="seg_input")
    filters = [64, 128, 256, 512, 512]
    x = inputs
    for idx, f in enumerate(filters):
        x, _ = _seg_enc_block(x, f, f"seg_e{idx}")

    # Bottleneck
    for tag in ("c1", "c2"):
        x = tf.keras.layers.Conv2D(1024, 3, padding="same", use_bias=False, name=f"seg_bn_{tag}")(x)
        x = tf.keras.layers.BatchNormalization(name=f"seg_bn_{tag}_bn")(x)
        x = tf.keras.layers.ReLU(name=f"seg_bn_{tag}_r")(x)

    for idx, f in enumerate(reversed(filters)):
        x = _seg_dec_block(x, f, f"seg_d{idx}")

    outputs = tf.keras.layers.Conv2D(num_classes, 1, activation="sigmoid", name="seg_output")(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="segnet")
    logger.info("Built SegNet (%d classes)", num_classes)
    return model


# ---------------------------------------------------------------------------
# Attention Feature Pyramid Network
# ---------------------------------------------------------------------------


def _attn_fpn_block(x: Any, skip: Any, filters: int, name: str) -> Any:
    """Up-sample x, fuse with skip, apply channel + spatial attention."""
    import tensorflow as tf

    factor = x.shape[1] // skip.shape[1] if skip.shape[1] and x.shape[1] else 2
    up = _upsample(x, factor, name=f"{name}_up")
    skip_p = tf.keras.layers.Conv2D(filters, 1, padding="same", name=f"{name}_sp")(skip)
    up_p = tf.keras.layers.Conv2D(filters, 1, padding="same", name=f"{name}_up_p")(up)
    fused = tf.keras.layers.Add(name=f"{name}_add")([skip_p, up_p])
    fused = _channel_attention(fused, name=f"{name}_ca")
    fused = _spatial_attention(fused, name=f"{name}_sa")
    return fused


def build_attention_fpn(
    input_shape: tuple[int, int, int],
    num_classes: int = 1,
    backbone: str = "resnet50",
) -> Any:
    """Attention Feature Pyramid Network with channel/spatial attention fusion."""
    import tensorflow as tf

    inputs = tf.keras.layers.Input(shape=input_shape, name="afpn_input")
    encoder = get_backbone(backbone, input_shape=input_shape)
    encoder.trainable = False

    scales = _collect_skips(encoder, 4)
    fpn_f = [256, 128, 64]
    x = scales[-1]
    for idx in range(3):
        si = max(len(scales) - 2 - idx, 0)
        x = _attn_fpn_block(x, scales[si], fpn_f[idx], name=f"af{idx}")

    x = _upsample(x, input_shape[0] // (x.shape[1] or 1) or 4, name="afpn_up")
    x = _bn_relu(x, 256, name="afpn_head")
    outputs = tf.keras.layers.Conv2D(num_classes, 1, activation="sigmoid", name="afpn_output")(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="attention_fpn")
    logger.info("Built Attention FPN with backbone '%s' (%d classes)", backbone, num_classes)
    return model


# ---------------------------------------------------------------------------
# HRNet-style
# ---------------------------------------------------------------------------


def _hr_block(x: Any, filters: int, name: str) -> Any:
    """Residual block: Conv3x3\u00d72 + BN + skip."""
    import tensorflow as tf

    shortcut = x
    x = tf.keras.layers.Conv2D(filters, 3, padding="same", use_bias=False, name=f"{name}_c1")(x)
    x = tf.keras.layers.BatchNormalization(name=f"{name}_bn1")(x)
    x = tf.keras.layers.ReLU(name=f"{name}_r1")(x)
    x = tf.keras.layers.Conv2D(filters, 3, padding="same", use_bias=False, name=f"{name}_c2")(x)
    x = tf.keras.layers.BatchNormalization(name=f"{name}_bn2")(x)
    if shortcut.shape[-1] != filters:
        shortcut = tf.keras.layers.Conv2D(filters, 1, padding="same", name=f"{name}_proj")(shortcut)
        shortcut = tf.keras.layers.BatchNormalization(name=f"{name}_proj_bn")(shortcut)
    x = tf.keras.layers.Add(name=f"{name}_add")([x, shortcut])
    return tf.keras.layers.ReLU(name=f"{name}_relu")(x)


def _hr_stage(x: Any, num_blocks: int, filters: int, si: int) -> Any:
    """One HRNet stage: two parallel branches \u2192 cross-fusion concat."""
    import tensorflow as tf

    low = x
    for i in range(num_blocks):
        low = _hr_block(low, filters, f"hr{si}_b0_{i}")
    high = tf.keras.layers.MaxPooling2D(2, name=f"hr{si}_ds")(x)
    for i in range(num_blocks):
        high = _hr_block(high, filters, f"hr{si}_b1_{i}")

    target = high.shape[1] or 1
    fused: list[Any] = []
    for idx, br in enumerate((low, high)):
        res = br.shape[1] or 1
        if res < target:
            br = tf.keras.layers.UpSampling2D(target // res, interpolation="bilinear", name=f"hr{si}_up{idx}")(br)
        elif res > target:
            br = tf.keras.layers.AveragePooling2D(res // target, name=f"hr{si}_dn{idx}")(br)
        br = tf.keras.layers.Conv2D(filters, 1, padding="same", name=f"hr{si}_pj{idx}")(br)
        fused.append(br)

    x = tf.keras.layers.Concatenate(name=f"hr{si}_cat")(fused)
    x = tf.keras.layers.Conv2D(filters, 1, padding="same", use_bias=False, name=f"hr{si}_mix")(x)
    x = tf.keras.layers.BatchNormalization(name=f"hr{si}_mix_bn")(x)
    x = tf.keras.layers.ReLU(name=f"hr{si}_mix_relu")(x)
    return x


def build_hrnet(
    input_shape: tuple[int, int, int],
    num_classes: int = 1,
    channels: int = 48,
    num_stages: int = 3,
    num_blocks: int = 4,
) -> Any:
    """HRNet-style high-resolution network with parallel resolution branches."""
    import tensorflow as tf

    inputs = tf.keras.layers.Input(shape=input_shape, name="hrnet_in")
    # Stem: stride-4
    x = tf.keras.layers.Conv2D(64, 3, strides=2, padding="same", use_bias=False, name="hr_stem_c1")(inputs)
    x = tf.keras.layers.BatchNormalization(name="hr_stem_bn1")(x)
    x = tf.keras.layers.ReLU(name="hr_stem_r1")(x)
    x = tf.keras.layers.Conv2D(64, 3, strides=2, padding="same", use_bias=False, name="hr_stem_c2")(x)
    x = tf.keras.layers.BatchNormalization(name="hr_stem_bn2")(x)
    x = tf.keras.layers.ReLU(name="hr_stem_r2")(x)

    for s in range(num_stages):
        x = _hr_stage(x, num_blocks, channels, s)

    x = _upsample(x, 4, name="hr_up")
    x = _bn_relu(x, channels, name="hr_head")
    outputs = tf.keras.layers.Conv2D(num_classes, 1, activation="sigmoid", name="hr_output")(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="hrnet")
    logger.info("Built HRNet (%d classes, %d stages)", num_classes, num_stages)
    return model


# ---------------------------------------------------------------------------
# Registry & factory
# ---------------------------------------------------------------------------

SEGMENTATION_MODELS: dict[str, Callable] = {
    "fcn": build_fcn,
    "deeplabv3": build_deeplabv3,
    "pspnet": build_pspnet,
    "linknet": build_linknet,
    "segnet": build_segnet,
    "attention_fpn": build_attention_fpn,
    "hrnet": build_hrnet,
}


def list_segmentation_models() -> list[str]:
    """Return sorted list of available segmentation model names."""
    return sorted(SEGMENTATION_MODELS.keys())


def get_model_info(name: str) -> dict[str, Any]:
    """Return metadata dict for the named model.

    Keys: ``name``, ``description``, ``complexity``, ``param_count_estimate``,
    ``recommended_input_size``.
    """
    key = name.lower()
    if key not in _MODEL_INFO:
        raise ValueError(f"Unknown model '{name}'. Available: {list_segmentation_models()}")
    info = dict(_MODEL_INFO[key])
    info["name"] = key
    return info


def build_model_by_name(
    name: str,
    input_shape: tuple[int, int, int],
    num_classes: int = 1,
    **kwargs: Any,
) -> Any:
    """Factory: build a segmentation model by string name with forwarded kwargs."""
    key = name.lower()
    if key not in SEGMENTATION_MODELS:
        raise ValueError(f"Unknown model '{name}'. Available: {list_segmentation_models()}")
    import inspect

    sig = inspect.signature(SEGMENTATION_MODELS[key])
    valid = set(sig.parameters.keys()) - {"input_shape", "num_classes"}
    filtered = {k: v for k, v in kwargs.items() if k in valid}
    return SEGMENTATION_MODELS[key](input_shape=input_shape, num_classes=num_classes, **filtered)


# ---------------------------------------------------------------------------
# Parameter counting & complexity estimation
# ---------------------------------------------------------------------------


def count_parameters(model: Any) -> dict[str, int]:
    """Return ``{total, trainable, non_trainable}`` parameter counts."""
    total = int(model.count_params())
    trainable = sum(
        int(w.numpy().size) if hasattr(w, "numpy") else int(w.shape.num_elements()) for w in model.trainable_weights
    )
    return {"total": total, "trainable": trainable, "non_trainable": total - trainable}


_FLOPS_TABLE: dict[str, float] = {
    "fcn": 45.0,
    "deeplabv3": 62.0,
    "pspnet": 70.0,
    "linknet": 35.0,
    "segnet": 25.0,
    "attention_fpn": 55.0,
    "hrnet": 30.0,
}


def estimate_model_complexity(name: str) -> dict[str, Any]:
    """Heuristic complexity estimate: FLOPs, memory, inference time.

    Values are approximate (GFLOPs at 512\u00d7512 input, MB, ms on a 10-TFLOPS GPU).
    """
    key = name.lower()
    if key not in _MODEL_INFO:
        raise ValueError(f"Unknown model '{name}'. Available: {list_segmentation_models()}")
    flops = _FLOPS_TABLE.get(key, 40.0)
    return {
        "model": key,
        "flops_estimate_gflops": flops,
        "memory_estimate_mb": round(flops * 3.5 + 200, 1),
        "inference_time_estimate_ms": round(flops / 10.0 * 1000.0, 1),
    }
