#!/usr/bin/env python3
"""GlacierNET-KZ — Gradio app for HuggingFace Spaces."""
import gradio as gr
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import io, json

# ── Lazy model loading ──────────────────────────────────────────────
_model = None

def _load_model():
    global _model
    if _model is not None:
        return _model
    import tensorflow as tf
    from pathlib import Path
    # Find model weights relative to spaces/ or project root
    candidates = [
        Path(__file__).resolve().parent.parent / "models" / "attention_unet_best.h5",
        Path(__file__).resolve().parent.parent / "models" / "unet_best.h5",
        Path(__file__).resolve().parent / "models" / "attention_unet_best.h5",
        Path("models/attention_unet_best.h5"),
        Path("models/unet_best.h5"),
    ]
    weights_path = next((p for p in candidates if p.exists()), None)
    if weights_path is None:
        raise FileNotFoundError(
            "No model weights found. Place attention_unet_best.h5 or unet_best.h5 in models/"
        )

    # Import build function from project
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.models import build_model, compile_model
    from src.config import PATCH_SIZE, N_CHANNELS

    input_shape = (PATCH_SIZE, PATCH_SIZE, N_CHANNELS)
    _model = build_model(input_shape)
    _model = compile_model(_model)
    _model.load_weights(str(weights_path))
    print(f"✓ Model loaded from {weights_path}")
    return _model

# ── Spectral indices ────────────────────────────────────────────────
def _add_indices(bands):
    """Compute NDSI, NDWI, BSI, EVI from 7-band Sentinel-2 array.

    Expected band order: B2, B3, B4, B8, B8A, B11, B12
    (standard Sentinel-2 L2A ordering).
    """
    if bands.shape[-1] < 7:
        return bands
    B2, B3, B4, B8, B8A, B11, B12 = bands[..., :7]
    ndsi = np.where((B3 + B11) > 0, (B3 - B11) / (B3 + B11 + 1e-10), 0)
    ndwi = np.where((B3 + B8) > 0, (B3 - B8) / (B3 + B8 + 1e-10), 0)
    bsi = np.where((B11 + B4) > 0, (B11 - B4) / (B11 + B4 + 1e-10), 0)
    evi = np.where(B8 > 0, 2.5 * (B8 - B4) / (B8 + 6 * B4 - 7.5 * B2 + 1 + 1e-10), 0)
    return np.stack([B2, B3, B4, B8, B8A, B11, B12, ndsi, ndwi, bsi, evi], axis=-1)

# ── Inference ───────────────────────────────────────────────────────
def classify_glacier(bands_input):
    """Run Attention U-Net on (H,W,7) band array → mask, confidence, overlay."""
    from src.config import PATCH_SIZE, N_CHANNELS
    bands = bands_input.astype(np.float32)
    bands_11ch = _add_indices(bands)

    h, w = bands_11ch.shape[:2]
    # Pad to multiple of PATCH_SIZE
    pad_h = (PATCH_SIZE - h % PATCH_SIZE) % PATCH_SIZE
    pad_w = (PATCH_SIZE - w % PATCH_SIZE) % PATCH_SIZE
    padded = np.pad(bands_11ch, ((0, pad_h), (0, pad_w), (0, 0)), mode="reflect")

    # Sliding window 50% overlap
    step = PATCH_SIZE // 2
    count = np.zeros((padded.shape[0], padded.shape[1]), dtype=np.float32)
    result = np.zeros((padded.shape[0], padded.shape[1]), dtype=np.float32)

    model = _load_model()
    for y in range(0, padded.shape[0] - PATCH_SIZE + 1, step):
        for x in range(0, padded.shape[1] - PATCH_SIZE + 1, step):
            patch = padded[y:y+PATCH_SIZE, x:x+PATCH_SIZE]
            pred = model.predict(patch[np.newaxis], verbose=0)[0, ..., 0]
            result[y:y+PATCH_SIZE, x:x+PATCH_SIZE] += pred
            count[y:y+PATCH_SIZE, x:x+PATCH_SIZE] += 1

    count[count == 0] = 1
    confidence = result / count
    mask = (confidence > 0.5).astype(np.float32)

    # Remove padding
    mask = mask[:h, :w]
    confidence = confidence[:h, :w]
    return mask, confidence

# ── Visualization ───────────────────────────────────────────────────
def _to_rgb(bands):
    """7-band → RGB composite (B4/B3/B2 true color)."""
    rgb = bands[..., [2, 1, 0]]  # B4, B3, B2 in standard Sentinel-2 order
    p2, p98 = np.percentile(rgb[rgb > 0], [2, 98]) if np.any(rgb > 0) else (0, 1)
    rgb = np.clip((rgb - p2) / (p98 - p2 + 1e-10), 0, 1)
    return rgb

def make_figure(bands, mask, confidence):
    """Create 4-panel figure: RGB, mask, confidence, overlay."""
    rgb = _to_rgb(bands)
    glacier_cmap = ListedColormap(["#00000000", "#00BCD4"])

    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    axes[0].imshow(rgb)
    axes[0].set_title("True Color (B4/B3/B2)")
    axes[1].imshow(mask, cmap=glacier_cmap, vmin=0, vmax=1)
    axes[1].set_title("Glacier Mask")
    axes[2].imshow(confidence, cmap="hot", vmin=0, vmax=1)
    axes[2].set_title("Confidence Map")
    axes[3].imshow(rgb)
    axes[3].imshow(mask, cmap=glacier_cmap, vmin=0, vmax=1, alpha=0.4)
    axes[3].set_title("Overlay")

    for ax in axes:
        ax.axis("off")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    from PIL import Image as _PilImage
    return _PilImage.open(buf)

# ── Gradio handler ──────────────────────────────────────────────────
def predict(file):
    if file is None:
        return None, "Upload a GeoTIFF or NumPy file.", None

    try:
        import rasterio
        with rasterio.open(file.name) as src:
            if src.count < 7:
                return None, f"Need >=7 bands, got {src.count}.", None
            bands = np.stack([src.read(i+1) for i in range(7)], axis=-1).astype(np.float32)
    except ImportError:
        try:
            data = np.load(file.name)
            if data.ndim == 3 and data.shape[2] >= 7:
                bands = data[..., :7].astype(np.float32)
            else:
                return None, f"Expected (H,W,7+) array, got shape {data.shape}.", None
        except Exception as e:
            return None, f"Cannot read file: {e}", None
    except Exception as e:
        return None, f"Cannot read file: {e}", None

    MAX_DIM = 4096
    if bands.shape[0] > MAX_DIM or bands.shape[1] > MAX_DIM:
        return None, f"Image too large ({bands.shape[0]}x{bands.shape[1]}). Max {MAX_DIM}x{MAX_DIM}.", None

    # Normalise to [0,1] if values > 1
    if bands.max() > 1.5:
        p2, p98 = np.percentile(bands[bands > 0], [2, 98])
        bands = np.clip((bands - p2) / (p98 - p2 + 1e-10), 0, 1)

    mask, confidence = classify_glacier(bands)
    glacier_km2 = float(np.sum(mask) * 10 * 10 / 1e6)  # 10m pixel → km²
    glacier_pct = float(np.mean(mask) * 100)

    fig_buf = make_figure(bands, mask, confidence)
    stats = f"🏔️ **Glacier area:** {glacier_km2:.2f} km² ({glacier_pct:.1f}% of scene)\n\n" \
            f"**Method:** Attention U-Net (F1=0.876, IoU=0.779)\n" \
            f"**Patch size:** 256×256, 50% overlap\n" \
            f"**Threshold:** 0.5"

    return fig_buf, stats, confidence

# ── Demo ────────────────────────────────────────────────────────────
demo = gr.Interface(
    fn=predict,
    inputs=gr.File(label="Upload satellite composite (GeoTIFF or .npy)", file_types=[".tif", ".tiff", ".npy"]),
    outputs=[
        gr.Image(label="Results"),
        gr.Markdown(label="Statistics"),
        gr.Image(label="Confidence Map"),
    ],
    title="🏔️ GlacierNET-KZ — AI Glacier Monitoring",
    description=(
        "Upload a Sentinel-2 or Landsat composite (7+ bands) to classify glacier extent "
        "using an Attention U-Net model trained on the Ili Alatau, Kazakhstan."
    ),
    examples=[
        ["examples/sample_2020.npy"] if __import__("pathlib").Path("examples/sample_2020.npy").exists() else None,
    ],

)

if __name__ == "__main__":
    import os

    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("DEMO_PORT", "7860")),
        root_path=os.environ.get("GRADIO_ROOT_PATH", ""),
    )
