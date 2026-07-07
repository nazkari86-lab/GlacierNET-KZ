import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

API_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(API_ROOT)))
UPLOAD_DIR = DATA_DIR / "uploads"
RESULTS_DIR = DATA_DIR / "results"
HISTORY_DB_PATH = DATA_DIR / "history.db"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "200"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
TASK_TIMEOUT = int(os.getenv("TASK_TIMEOUT", "600"))
STATIC_URL_PREFIX = os.getenv("STATIC_URL_PREFIX", "")

# --- LLM Gateway ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "mistral:7b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
ANALYSIS_LANG = os.getenv("ANALYSIS_LANG", "ru")

# Optional admin API key — when set, /api/admin/* requires X-API-Key header.
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
