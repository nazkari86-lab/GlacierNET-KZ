import json
import logging
import urllib.request
from typing import Optional

from app import config

log = logging.getLogger(__name__)

SYSTEM_PROMPT_DESCRIBE = (
    "Ты — экспертный гляциолог, анализирующий результаты сегментации ледников "
    "по спутниковым снимкам. Отвечай кратко, научно, на русском языке."
)

SYSTEM_PROMPT_TREND = (
    "Ты — экспертный гляциолог, анализирующий многолетние тренды изменения ледников. "
    "Отвечай развёрнуто, с цифрами, на русском языке. "
    "Выделяй ускорение таяния, аномальные годы и сравнивай с региональными климатическими данными."
)

SYSTEM_PROMPT_COMPARE = (
    "Ты — экспертный гляциолог, сравнивающий результаты разных моделей сегментации ледников. "
    "Анализируй расхождения, точность границ, устойчивость к шумам. Отвечай на русском языке."
)


def _model_mapping(provider: str, model: str) -> str:
    mappings = {
        "openai": model or "gpt-4o-mini",
        "anthropic": model or "claude-3-5-haiku-20241022",
        "groq": f"groq/{model or 'llama3-70b-8192'}",
        "google": f"gemini/{model or 'gemini-1.5-flash'}",
        "ollama": f"ollama/{model or config.LLM_FALLBACK_MODEL}",
        "openrouter": f"openrouter/{model or 'openai/gpt-4o-mini'}",
    }
    return mappings.get(provider, model)


def _get_api_key(provider: str) -> Optional[str]:
    keys = {
        "openai": config.OPENAI_API_KEY,
        "anthropic": config.ANTHROPIC_API_KEY,
        "groq": config.GROQ_API_KEY,
        "google": config.GOOGLE_API_KEY,
        "openrouter": config.OPENROUTER_API_KEY,
    }
    return keys.get(provider)


def analyze(
    prompt: str,
    provider: str = "",
    model: str = "",
    api_key: Optional[str] = None,
    system_prompt: str = "",
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> dict:
    try:
        from litellm import completion
    except Exception as e:
        log.warning("LiteLLM is not available: %s", e)
        return _fallback_unavailable()

    _provider = provider or config.LLM_PROVIDER
    _requested_model = model or config.LLM_MODEL
    _model_full = _model_mapping(_provider, _requested_model)
    _system = system_prompt or SYSTEM_PROMPT_DESCRIBE
    _temp = temperature if temperature is not None else config.LLM_TEMPERATURE
    _max = max_tokens if max_tokens is not None else config.LLM_MAX_TOKENS

    kwargs = {
        "model": _model_full,
        "messages": [
            {"role": "system", "content": _system},
            {"role": "user", "content": prompt},
        ],
        "temperature": _temp,
        "max_tokens": _max,
    }

    api_key = api_key or _get_api_key(_provider)
    if api_key:
        kwargs["api_key"] = api_key

    if _provider == "ollama" and config.OLLAMA_BASE_URL:
        kwargs["api_base"] = config.OLLAMA_BASE_URL

    try:
        log.info("LLM request: provider=%s model=%s", _provider, _model_full)
        resp = completion(**kwargs)
        content = ""
        if resp.choices:
            content = resp.choices[0].message.content or ""
        log.info("LLM response: provider=%s model=%s chars=%d", _provider, _requested_model, len(content))
        return {
            "content": content,
            "provider": _provider,
            "model": _requested_model,
            "fallback_used": False,
        }
    except Exception as e:
        log.warning("LLM request failed for %s/%s: %s", _provider, _requested_model, e)
        return _fallback(prompt, _system, _temp, _max)


def _fallback(prompt: str, system: str, temp: float, max_tok: int) -> dict:
    try:
        from litellm import completion
    except Exception as e:
        log.warning("LiteLLM fallback is not available: %s", e)
        return _fallback_unavailable()

    fallback_model = _model_mapping("ollama", config.LLM_FALLBACK_MODEL)
    try:
        log.info("Fallback to Ollama: %s", fallback_model)
        resp = completion(
            model=fallback_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            api_base=config.OLLAMA_BASE_URL,
            temperature=temp,
            max_tokens=max_tok,
        )
        content = ""
        if resp.choices:
            content = resp.choices[0].message.content or ""
        log.info("Ollama response: chars=%d", len(content))
        return {
            "content": content,
            "provider": "ollama",
            "model": config.LLM_FALLBACK_MODEL,
            "fallback_used": True,
        }
    except Exception as e:
        log.warning("Ollama fallback failed: %s", e)
        return _fallback_unavailable()


def _fallback_unavailable() -> dict:
    return {
        "content": "Все LLM-провайдеры недоступны. Проверьте API-ключи или подключение к Ollama.",
        "provider": "",
        "model": "",
        "fallback_used": True,
    }


def _fetch_json(url: str, headers: Optional[dict] = None, timeout: int = 5) -> Optional[dict]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            return json.loads(resp.read())
    except Exception:
        return None


def _as_model_list(model_ids: list[str]) -> list[dict]:
    return [{"id": m, "name": m, "free": False} for m in model_ids]


def _fetch_openai_models() -> list[dict]:
    key = _get_api_key("openai")
    if not key:
        return _as_model_list(["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"])
    data = _fetch_json("https://api.openai.com/v1/models", {"Authorization": f"Bearer {key}"})
    if not data:
        return _as_model_list(["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"])
    ids = sorted([m["id"] for m in data.get("data", []) if not m["id"].startswith("ft:")])
    return _as_model_list(ids)


def _fetch_anthropic_models() -> list[dict]:
    return _as_model_list(
        ["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"]
    )


def _fetch_groq_models() -> list[dict]:
    key = _get_api_key("groq")
    if not key:
        return _as_model_list(["llama3-70b-8192", "mixtral-8x7b-32768", "gemma2-9b-it"])
    data = _fetch_json("https://api.groq.com/openai/v1/models", {"Authorization": f"Bearer {key}"})
    if not data:
        return _as_model_list(["llama3-70b-8192", "mixtral-8x7b-32768", "gemma2-9b-it"])
    ids = sorted([m["id"] for m in data.get("data", [])])
    return _as_model_list(ids)


def _fetch_google_models() -> list[dict]:
    key = _get_api_key("google")
    if not key:
        return _as_model_list(["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"])
    data = _fetch_json(f"https://generativelanguage.googleapis.com/v1/models?key={key}")
    if not data:
        return _as_model_list(["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"])
    ids = sorted(
        m["name"].replace("models/", "")
        for m in data.get("models", [])
        if "generateContent" in m.get("supportedGenerationMethods", [])
    )
    return _as_model_list(ids)


def _fetch_ollama_models() -> list[dict]:
    try:
        data = _fetch_json(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=3)
        if data and "models" in data:
            ids = sorted(m["name"] for m in data["models"])
            return _as_model_list(ids)
    except Exception:
        pass
    return _as_model_list(["mistral:7b", "llama3.1:8b", "qwen3:8b", "llama3.2:1b", "deepseek-coder-v2", "mixtral:8x7b"])


def _fetch_openrouter_models() -> list[dict]:
    key = _get_api_key("openrouter")
    if not key:
        return [
            {"id": "openai/gpt-4o-mini", "name": "OpenAI GPT-4o Mini", "free": False},
            {"id": "anthropic/claude-3.5-haiku", "name": "Anthropic Claude 3.5 Haiku", "free": False},
            {"id": "meta-llama/llama-3.1-8b", "name": "Meta Llama 3.1 8B", "free": False},
        ]
    data = _fetch_json("https://openrouter.ai/api/v1/models", {"Authorization": f"Bearer {key}"}, timeout=15)
    if not data:
        return [
            {"id": "openai/gpt-4o-mini", "name": "OpenAI GPT-4o Mini", "free": False},
            {"id": "anthropic/claude-3.5-haiku", "name": "Anthropic Claude 3.5 Haiku", "free": False},
            {"id": "meta-llama/llama-3.1-8b", "name": "Meta Llama 3.1 8B", "free": False},
        ]
    result = []
    for m in data.get("data", []):
        mid = m.get("id", "")
        if not mid:
            continue
        pricing = m.get("pricing", {})
        is_free = (pricing.get("prompt") == "0" and pricing.get("completion") == "0") or ":free" in mid
        name = m.get("name", "") or mid
        result.append({"id": mid, "name": name, "free": is_free})
    return sorted(result, key=lambda x: x["id"])


def _fetch_models_with_key(provider: str, api_key: str) -> list[dict]:
    """Fetch models from a provider using a user-supplied API key."""
    if not api_key:
        return []

    if provider == "openai":
        data = _fetch_json("https://api.openai.com/v1/models", {"Authorization": f"Bearer {api_key}"})
        if not data:
            return []
        ids = sorted([m["id"] for m in data.get("data", []) if not m["id"].startswith("ft:")])
        return _as_model_list(ids)

    if provider == "groq":
        data = _fetch_json("https://api.groq.com/openai/v1/models", {"Authorization": f"Bearer {api_key}"})
        if not data:
            return []
        ids = sorted([m["id"] for m in data.get("data", [])])
        return _as_model_list(ids)

    if provider == "google":
        data = _fetch_json(f"https://generativelanguage.googleapis.com/v1/models?key={api_key}")
        if not data:
            return []
        ids = sorted(
            m["name"].replace("models/", "")
            for m in data.get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])
        )
        return _as_model_list(ids)

    if provider == "openrouter":
        data = _fetch_json("https://openrouter.ai/api/v1/models", {"Authorization": f"Bearer {api_key}"}, timeout=15)
        if not data:
            return []
        result = []
        for m in data.get("data", []):
            mid = m.get("id", "")
            if not mid:
                continue
            pricing = m.get("pricing", {})
            is_free = (pricing.get("prompt") == "0" and pricing.get("completion") == "0") or ":free" in mid
            name = m.get("name", "") or mid
            result.append({"id": mid, "name": name, "free": is_free})
        return sorted(result, key=lambda x: x["id"])

    if provider == "anthropic":
        return _as_model_list(
            [
                "claude-3-5-haiku-20241022",
                "claude-3-5-sonnet-20241022",
                "claude-3-opus-20240229",
                "claude-3-haiku-20240307",
            ]
        )

    return []


def list_available() -> list[dict]:
    return [
        {"provider": "openai", "label": "OpenAI", "models": _fetch_openai_models(), "needs_key": True},
        {"provider": "anthropic", "label": "Anthropic", "models": _fetch_anthropic_models(), "needs_key": True},
        {"provider": "groq", "label": "Groq (free)", "models": _fetch_groq_models(), "needs_key": True},
        {"provider": "google", "label": "Google Gemini", "models": _fetch_google_models(), "needs_key": True},
        {"provider": "ollama", "label": "Ollama (local)", "models": _fetch_ollama_models(), "needs_key": False},
        {"provider": "openrouter", "label": "OpenRouter", "models": _fetch_openrouter_models(), "needs_key": True},
    ]
