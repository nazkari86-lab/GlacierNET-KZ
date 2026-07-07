import logging

from fastapi import APIRouter

from app.schemas.requests import FetchModelsRequest, LLMAnalyzeRequest
from app.schemas.responses import LLMAnalyzeResponse, LLMModelInfo, LLMProviderInfo
from app.services.llm_service import (
    SYSTEM_PROMPT_COMPARE,
    SYSTEM_PROMPT_DESCRIBE,
    SYSTEM_PROMPT_TREND,
    _fetch_models_with_key,
    analyze,
    list_available,
)
from app.storage.analysis_history import save_analysis

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


@router.get("/models")
def get_models() -> list[LLMProviderInfo]:
    return list_available()


@router.post("/models/fetch")
def fetch_models_with_key(body: FetchModelsRequest) -> list[LLMModelInfo]:
    """Fetch models from a provider using a user-supplied API key."""
    models = _fetch_models_with_key(body.provider, body.api_key)
    return [LLMModelInfo(**m) for m in models]


@router.post("/analyze")
def analyze_text(body: LLMAnalyzeRequest) -> LLMAnalyzeResponse:
    system_map = {
        "describe": SYSTEM_PROMPT_DESCRIBE,
        "trend": SYSTEM_PROMPT_TREND,
        "compare": SYSTEM_PROMPT_COMPARE,
    }
    system_prompt = system_map.get(body.mode, SYSTEM_PROMPT_DESCRIBE)

    if body.context:
        full_prompt = f"{body.prompt}\n\nКонтекст:\n{body.context}"
    else:
        full_prompt = body.prompt

    result = analyze(
        prompt=full_prompt,
        provider=body.provider,
        model=body.model,
        api_key=body.api_key,
        system_prompt=system_prompt,
    )

    try:
        save_analysis(
            prompt=body.prompt,
            mode=body.mode or "describe",
            provider=result["provider"],
            model=result["model"],
            response=result["content"],
            fallback_used=result["fallback_used"],
        )
    except Exception as e:
        log.warning("Failed to save analysis to history: %s", e)

    return LLMAnalyzeResponse(
        content=result["content"],
        provider=result["provider"],
        model=result["model"],
        fallback_used=result["fallback_used"],
    )
