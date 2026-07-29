import logging

from fastapi import APIRouter, HTTPException

from app.schemas.requests import FetchModelsRequest, LLMAnalyzeRequest
from app.schemas.responses import LLMAnalyzeResponse, LLMModelInfo, LLMProviderInfo
from app.services.evidence_service import get_trend_evidence, trend_evidence_prompt
from app.services.llm_service import (
    SYSTEM_PROMPT_COMPARE,
    SYSTEM_PROMPT_DESCRIBE,
    SYSTEM_PROMPT_TREND,
    _fetch_models_with_key,
    analyze,
    is_repetitive_completion,
    list_available,
)
from app.storage.analysis_history import save_analysis

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])

PROJECT_PURPOSE = """GlacierNET-KZ — локальная платформа наблюдения за криосферой Казахстана.
Цель: по спутниковым данным оценивать площадь и состояние ледников, сохраняя источник, качество и ограничения каждого результата.
Задачи: (1) выделять ледниковые маски на Sentinel-2 и Landsat; (2) сравнивать доступные годы и методы сегментации; (3) показывать границы, снимки и показатели качества на карте; (4) отмечать неподтверждённые или аномальные изменения; (5) объединять ледники, озёра, рельеф и исторические события в исследовательский Risk Twin.
Граница утверждений: проект не измеряет объём льда или водный запас без отдельной валидации и не заменяет экспертную гляциологическую оценку."""


def _asks_project_purpose(prompt: str) -> bool:
    normalized = prompt.lower()
    return any(
        token in normalized
        for token in ("предназначен", "предназначение", "цель проекта", "задач проекта", "что делает проект")
    )


@router.get("/models")
def get_models() -> list[LLMProviderInfo]:
    return list_available()


@router.get("/evidence/trend")
def get_verified_trend_evidence() -> dict:
    """Chart-ready local evidence; no LLM and no external data are involved."""
    try:
        return get_trend_evidence()
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/models/fetch")
def fetch_models_with_key(body: FetchModelsRequest) -> list[LLMModelInfo]:
    """Fetch models from a provider using a user-supplied API key."""
    if body.provider != "groq":
        raise HTTPException(status_code=422, detail="Only Groq is enabled")
    try:
        models = _fetch_models_with_key(body.provider, body.api_key)
    except RuntimeError as error:
        raise HTTPException(status_code=422, detail=f"Groq key/model check failed: {error}") from error
    return [LLMModelInfo(**m) for m in models]


@router.post("/analyze")
def analyze_text(body: LLMAnalyzeRequest) -> LLMAnalyzeResponse:
    if body.provider and body.provider != "groq":
        raise HTTPException(status_code=422, detail="Only Groq is enabled")
    system_map = {
        "describe": SYSTEM_PROMPT_DESCRIBE,
        "trend": SYSTEM_PROMPT_TREND,
        "compare": SYSTEM_PROMPT_COMPARE,
    }
    system_prompt = system_map.get(body.mode, SYSTEM_PROMPT_DESCRIBE)

    evidence_context = PROJECT_PURPOSE if body.mode == "describe" else ""
    if body.mode == "trend":
        try:
            evidence_context = trend_evidence_prompt(get_trend_evidence())
        except FileNotFoundError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    supplied_context = f"Контекст проекта:\n{body.context}" if body.context else ""
    full_prompt = "\n\n".join(part for part in (body.prompt, evidence_context, supplied_context) if part)

    result = analyze(
        prompt=full_prompt,
        provider=body.provider,
        model=body.model,
        api_key=body.api_key,
        system_prompt=system_prompt,
    )

    # Groq occasionally produces a degenerate loop.  For a stable, factual
    # project-purpose answer use the maintained local card instead of exposing
    # repetition to the presenter.
    if body.mode == "describe" and _asks_project_purpose(body.prompt) and is_repetitive_completion(result["content"]):
        result["content"] = (
            "**Предназначение GlacierNET-KZ**\n\n"
            "Проект помогает наблюдать состояние и изменение площади ледников Казахстана по спутниковым данным. "
            "Он объединяет сегментацию снимков, карту, проверку качества и исследовательскую оценку связанных криосферных рисков.\n\n"
            "**Цель** — сделать результаты наблюдений за ледниками понятными, воспроизводимыми и проверяемыми.\n\n"
            "**Основные задачи**\n"
            "1. Выделять ледниковые маски на снимках Sentinel-2 и Landsat.\n"
            "2. Сравнивать доступные годы и методы сегментации.\n"
            "3. Показывать на карте границы, снимки, маски и ограничения качества.\n"
            "4. Отмечать подозрительные изменения, а не выдавать их за подтверждённый тренд.\n"
            "5. Собирать данные о ледниках, озёрах, рельефе и исторических GLOF-событиях для Risk Twin.\n\n"
            "Важно: проект оценивает результаты сегментации площади; он не измеряет объём льда или водный запас без отдельной валидации."
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
