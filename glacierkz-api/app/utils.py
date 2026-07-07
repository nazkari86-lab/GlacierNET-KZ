import os
import sys
from pathlib import Path

from app.config import RESULTS_DIR, STATIC_URL_PREFIX


def resolve_core_dir(from_file: str) -> Path:
    core_dir = os.environ.get("CORE_DIR")
    if core_dir:
        core_path = Path(core_dir)
    else:
        core_path = Path(from_file).resolve().parent.parent.parent.parent
    str_path = str(core_path.resolve())
    if str_path not in sys.path:
        sys.path.insert(0, str_path)
    return core_path


def path_to_url(file_path: str | Path) -> str:
    p = Path(file_path)
    try:
        relative = p.relative_to(RESULTS_DIR)
        return f"{STATIC_URL_PREFIX}/static/results/{relative}"
    except ValueError:
        pass
    return str(file_path)
