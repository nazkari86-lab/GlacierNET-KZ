from fastapi import APIRouter

from app.services.model_availability import filter_available_models, is_model_available

router = APIRouter(prefix="/api", tags=["Models"])

MODELS_CATALOG = [
    {
        "name": "unet",
        "display_name": "U-Net",
        "description": "Baseline U-Net with 4 encoder levels and Dice loss. Best general-purpose choice.",
        "supports_tta": True,
        "supports_crf": True,
        "supports_uncertainty": True,
    },
    {
        "name": "attention_unet",
        "display_name": "Attention U-Net",
        "description": "U-Net with attention gates on skip connections. Sharper glacier boundaries.",
        "supports_tta": True,
        "supports_crf": True,
        "supports_uncertainty": True,
    },
    {
        "name": "unet_plus_plus",
        "display_name": "U-Net++",
        "description": "Nested U-Net with dense skip connections. Highest boundary quality at moderate parameter cost.",
        "supports_tta": True,
        "supports_crf": True,
        "supports_uncertainty": True,
    },
    {
        "name": "ndsi",
        "display_name": "NDSI Threshold",
        "description": "Normalized Difference Snow Index — fast threshold method, no deep learning required.",
        "supports_tta": False,
        "supports_crf": False,
        "supports_uncertainty": False,
    },
    {
        "name": "rf",
        "display_name": "Random Forest",
        "description": "Pixel-based Random Forest classifier. Robust on heterogeneous terrain.",
        "supports_tta": False,
        "supports_crf": True,
        "supports_uncertainty": True,
    },
    {
        "name": "ensemble",
        "display_name": "Ensemble (U-Net + NDSI + RF)",
        "description": "Weighted average of all available models. Most stable predictions.",
        "supports_tta": True,
        "supports_crf": True,
        "supports_uncertainty": False,
    },
]


@router.get("/models")
def list_models():
    """Return models that have trained weights (or need no weights, e.g. NDSI)."""
    return filter_available_models(MODELS_CATALOG)


@router.get("/models/all")
def list_all_models():
    """Full catalog including models without weights (for training UI)."""
    return [{**m, "available": is_model_available(m["name"])} for m in MODELS_CATALOG]


@router.get("/models/available")
def list_available_architectures():
    """Список архитектур из реестра src.models."""
    try:
        from src.models import get_model_info
        from src.models import list_models as registry_list_models

        names = registry_list_models()
        return [get_model_info(n) for n in names]
    except ImportError:
        return [{"name": "unet"}, {"name": "attention_unet"}, {"name": "unet_plus_plus"}]
