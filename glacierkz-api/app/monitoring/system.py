"""System information — platform, Python, GPU, disk, processes."""

from __future__ import annotations

import os
import platform
import sys
from typing import Any


def get_system_info() -> dict[str, Any]:
    """Collect system information for /info endpoint."""
    info: dict[str, Any] = {
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor() or "unknown",
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
        },
        "process": {
            "pid": os.getpid(),
            "ppid": os.getppid(),
            "cwd": os.getcwd(),
            "user": os.getenv("USER", os.getenv("LOGNAME", "unknown")),
        },
        "python": {
            "version": sys.version,
            "executable": sys.executable,
            "prefix": sys.prefix,
            "path": sys.path[:5],
        },
        "environment": {
            "env_count": len(os.environ),
            "has_cuda": os.getenv("CUDA_VISIBLE_DEVICES") is not None,
            "conda_env": os.getenv("CONDA_DEFAULT_ENV"),
            "virtual_env": os.getenv("VIRTUAL_ENV"),
        },
        "limits": {
            "open_files_limit": _get_open_files_limit(),
            "virtual_memory_limit": _get_virtual_memory_limit(),
        },
    }

    try:
        import psutil

        proc = psutil.Process()
        mem = proc.memory_info()
        info["process"].update(
            {
                "memory_rss_mb": round(mem.rss / (1024 * 1024), 2),
                "memory_vms_mb": round(mem.vms / (1024 * 1024), 2),
                "num_threads": proc.num_threads(),
                "cpu_percent": proc.cpu_percent(interval=0.1),
                "create_time": proc.create_time(),
            }
        )
        info["cpu"] = {
            "count_logical": psutil.cpu_count(logical=True),
            "count_physical": psutil.cpu_count(logical=False),
            "percent": psutil.cpu_percent(interval=0.1),
            "freq_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else None,
        }
        info["memory"] = {
            "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "percent_used": psutil.virtual_memory().percent,
        }
        info["disk"] = {
            "total_gb": round(psutil.disk_usage("/").total / (1024**3), 2),
            "free_gb": round(psutil.disk_usage("/").free / (1024**3), 2),
        }
        info["network"] = {
            "interfaces": list(psutil.net_if_addrs().keys())[:10],
        }
    except ImportError:
        pass

    try:
        import tensorflow as tf

        gpus = tf.config.list_physical_devices("GPU")
        info["gpu"] = {
            "available": len(gpus) > 0,
            "count": len(gpus),
            "devices": [{"name": g.name, "memory_limit": g.memory_limit} for g in gpus],
        }
    except Exception:
        info["gpu"] = {"available": False, "count": 0, "devices": []}

    return info


def _get_open_files_limit() -> int | None:
    try:
        import resource

        soft, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
        return soft
    except Exception:
        return None


def _get_virtual_memory_limit() -> int | None:
    try:
        import resource

        soft, _ = resource.getrlimit(resource.RLIMIT_AS)
        return soft
    except Exception:
        return None
