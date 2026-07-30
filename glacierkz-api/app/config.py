import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

API_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(API_ROOT)))
UPLOAD_DIR = DATA_DIR / "uploads"
RESULTS_DIR = DATA_DIR / "results"
HISTORY_DB_PATH = DATA_DIR / "history.db"
OPERATIONS_DB_PATH = Path(os.getenv("OPERATIONS_DB_PATH", str(DATA_DIR / "operations.db")))

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_configured_cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        ("http://localhost:3000,http://127.0.0.1:3000,http://localhost:3100,http://127.0.0.1:3100"),
    ).split(",")
    if origin.strip()
]


def _with_loopback_aliases(origins: list[str]) -> list[str]:
    """Treat localhost and 127.0.0.1 as the same local development origin."""
    expanded = list(origins)
    for origin in origins:
        if origin.startswith("http://localhost:"):
            expanded.append(origin.replace("http://localhost:", "http://127.0.0.1:", 1))
        elif origin.startswith("http://127.0.0.1:"):
            expanded.append(origin.replace("http://127.0.0.1:", "http://localhost:", 1))
    return list(dict.fromkeys(expanded))


CORS_ORIGINS = _with_loopback_aliases(_configured_cors_origins)
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "200"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
TASK_TIMEOUT = int(os.getenv("TASK_TIMEOUT", "600"))
STATIC_URL_PREFIX = os.getenv("STATIC_URL_PREFIX", "")

# --- Groq-only evidence assistant ---
LLM_PROVIDER = "groq"
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))
ANALYSIS_LANG = os.getenv("ANALYSIS_LANG", "ru")

# Optional admin API key — when set, /api/admin/* requires X-API-Key header.
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

# MCP is used by the presentation AI for read-only evidence retrieval.  Running
# segmentation through a generic agent endpoint consumes significant compute
# and writes artifacts, so it requires an explicit deployment opt-in.
MCP_INFERENCE_ENABLED = os.getenv("MCP_INFERENCE_ENABLED", "false").strip().lower() in {
    "1",
    "true",
    "yes",
}
