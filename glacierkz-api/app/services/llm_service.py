import json
import logging
import re
import urllib.error
import urllib.request
from typing import Optional

from app import config

log = logging.getLogger(__name__)

SYSTEM_PROMPT_DESCRIBE = (
    "Ты — экспертный гляциолог, анализирующий результаты сегментации ледников "
    "по спутниковым снимкам. Отвечай кратко, связно и научно на русском языке. "
    "Не повторяй одну и ту же мысль или фразу. Если спрашивают о предназначении проекта, "
    "сформулируй одну цель и 3–5 конкретных задач, не добавляя неподтверждённые результаты."
)

SYSTEM_PROMPT_TREND = (
    "Ты — экспертный гляциолог, анализирующий многолетние тренды изменения ледников. "
    "Отвечай на русском языке, но используй числа только из блока VERIFIED LOCAL EVIDENCE. "
    "Не заявляй об ускорении, климатических причинах, температуре, осадках, станциях, прогнозе или "
    "точности модели, если этого нет в этом блоке. Не рисуй псевдографики в тексте: график строится интерфейсом. "
    "Явно различай результаты сегментации площади и физические свойства ледника; перечисляй ограничения."
)

SYSTEM_PROMPT_COMPARE = (
    "Ты — экспертный гляциолог, сравнивающий результаты разных моделей сегментации ледников. "
    "Анализируй расхождения, точность границ, устойчивость к шумам. Отвечай на русском языке."
)


def is_repetitive_completion(content: str) -> bool:
    """Detect obvious degenerate repetitions without treating normal prose as bad.

    This is a last-resort response-quality guard: repeated sentences are not a
    scientific result and should never silently reach a presentation screen.
    """
    chunks = [
        re.sub(r"[^\wа-яё]+", " ", sentence.lower()).strip()
        for sentence in re.split(r"[.!?\n]+", content, flags=re.IGNORECASE)
    ]
    chunks = [chunk for chunk in chunks if len(chunk) >= 18]
    return len(chunks) >= 4 and max(chunks.count(chunk) for chunk in set(chunks)) >= 3


def _get_api_key(provider: str) -> Optional[str]:
    return config.GROQ_API_KEY if provider == "groq" else None


def analyze(
    prompt: str,
    provider: str = "",
    model: str = "",
    api_key: Optional[str] = None,
    system_prompt: str = "",
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> dict:
    if provider and provider != "groq":
        return _provider_error("Only Groq is enabled in this GlacierNET-KZ workspace.")
    _requested_model = model or "llama-3.3-70b-versatile"
    _system = system_prompt or SYSTEM_PROMPT_DESCRIBE
    _temp = temperature if temperature is not None else config.LLM_TEMPERATURE
    _max = max_tokens if max_tokens is not None else config.LLM_MAX_TOKENS
    key = api_key or _get_api_key("groq")
    if not key:
        return _provider_error("Enter a Groq API key. The key is used only for this request and is not stored.")
    payload = {
        "model": _requested_model,
        "messages": [{"role": "system", "content": _system}, {"role": "user", "content": prompt}],
        "temperature": max(float(_temp), 1e-8),
        "max_tokens": _max,
    }
    try:
        response = _post_json("https://api.groq.com/openai/v1/chat/completions", payload, key)
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            return _provider_error("Groq returned an empty completion. Try another model or a shorter prompt.")
        return {"content": content, "provider": "groq", "model": _requested_model, "fallback_used": False}
    except RuntimeError as error:
        log.warning("Groq request failed for %s: %s", _requested_model, error)
        return _provider_error(str(error))


def _provider_error(message: str) -> dict:
    return {"content": f"❌ Groq: {_groq_hint(message)}", "provider": "groq", "model": "", "fallback_used": False}


def _groq_hint(message: str) -> str:
    if "1010" in message:
        return (
            "Groq/Cloudflare rejected the server request (error 1010). "
            "GlacierNET-KZ will retry with its application HTTP identity; refresh the page and check the key again."
        )
    return message


def _groq_headers(api_key: str, *, content_type: bool = False) -> dict[str, str]:
    """Headers accepted by Groq/Cloudflare for a named server-side client.

    urllib otherwise sends ``Python-urllib/<version>``, which Cloudflare can
    classify as an automated client and reject with error 1010 before it even
    evaluates the API key.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "GlacierNET-KZ/1.0 (local research dashboard)",
    }
    if content_type:
        headers["Content-Type"] = "application/json"
    return headers


def _post_json(url: str, payload: dict, api_key: str) -> dict:
    """Direct Groq request, avoiding the local LiteLLM/Pydantic incompatibility."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=_groq_headers(api_key, content_type=True),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:  # nosec B310 - fixed Groq endpoint
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        detail = _error_detail(error.read())
        status = error.code
        safe_detail = detail[:300] if detail else "request rejected"
        raise RuntimeError(f"HTTP {status}: {safe_detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError("network request failed; check internet connection") from error


def _error_detail(body: bytes) -> str:
    """Extract a safe diagnostic from a provider error without ever logging a key."""
    try:
        parsed = json.loads(body)
    except Exception:
        return body.decode("utf-8", errors="replace").strip()[:300]
    error = parsed.get("error", parsed) if isinstance(parsed, dict) else parsed
    if isinstance(error, dict):
        return str(error.get("message") or error.get("error") or error.get("code") or "")[:300]
    return str(error)[:300]


def _get_groq_models_with_key(api_key: str) -> list[dict]:
    request = urllib.request.Request(
        "https://api.groq.com/openai/v1/models",
        headers=_groq_headers(api_key),
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # nosec B310 - fixed Groq endpoint
            data = json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise RuntimeError(
            _groq_hint(f"HTTP {error.code}: {_error_detail(error.read()) or 'request rejected'}")
        ) from error
    except urllib.error.URLError as error:
        raise RuntimeError("network request failed; check internet connection") from error
    return _as_model_list(sorted([item["id"] for item in data.get("data", []) if item.get("id")]))


def _as_model_list(model_ids: list[str]) -> list[dict]:
    return [{"id": m, "name": m, "free": False} for m in model_ids]


def _fetch_groq_models() -> list[dict]:
    key = _get_api_key("groq")
    if not key:
        return _as_model_list(["llama-3.3-70b-versatile", "llama-3.1-8b-instant"])
    try:
        return _get_groq_models_with_key(key)
    except RuntimeError:
        return _as_model_list(["llama-3.3-70b-versatile", "llama-3.1-8b-instant"])


def _fetch_models_with_key(provider: str, api_key: str) -> list[dict]:
    """Fetch Groq models with a user-supplied key; reject every other provider."""
    if provider != "groq" or not api_key:
        return []
    return _get_groq_models_with_key(api_key)


def list_available() -> list[dict]:
    return [{"provider": "groq", "label": "Groq", "models": _fetch_groq_models(), "needs_key": True}]
