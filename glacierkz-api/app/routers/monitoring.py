# -*- coding: utf-8 -*-
"""System monitoring, metrics, and health-check routes.

Exposes Prometheus-compatible metrics, detailed system resource usage, and a
lightweight status endpoint suitable for liveness / readiness probes.
"""

from __future__ import annotations

import os
import time
from typing import Any

import psutil
from fastapi import APIRouter, Response

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

# Timestamp when the module (and therefore the process) was first imported.
_start_time: float = time.time()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uptime_seconds() -> float:
    """Return process uptime in seconds."""
    return time.time() - _start_time


def _fmt_bytes(n: int) -> str:
    """Format a byte count into a human-readable SI string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "/metrics",
    summary="Prometheus text-format metrics",
    response_class=Response,
)
async def prometheus_metrics() -> Response:
    """Expose key application metrics in Prometheus exposition format.

    Suitable for scraping by a Prometheus server, Grafana Agent, or any
    OpenMetrics-compatible collector.  The ``Content-Type`` header is set to
    ``text/plain; version=0.0.4`` as required by the exposition spec.
    """
    process = psutil.Process(os.getpid())
    mem = process.memory_info()
    cpu = psutil.cpu_percent(interval=0.1)

    lines = [
        "# HELP glacierkz_uptime_seconds Process uptime in seconds.",
        "# TYPE glacierkz_uptime_seconds gauge",
        f"glacierkz_uptime_seconds {_uptime_seconds():.2f}",
        "",
        "# HELP glacierkz_cpu_percent Current CPU usage percentage.",
        "# TYPE glacierkz_cpu_percent gauge",
        f"glacierkz_cpu_percent {cpu:.2f}",
        "",
        "# HELP glacierkz_memory_rss_bytes Resident set size in bytes.",
        "# TYPE glacierkz_memory_rss_bytes gauge",
        f"glacierkz_memory_rss_bytes {mem.rss}",
        "",
        "# HELP glacierkz_memory_vms_bytes Virtual memory size in bytes.",
        "# TYPE glacierkz_memory_vms_bytes gauge",
        f"glacierkz_memory_vms_bytes {mem.vms}",
        "",
        "# HELP glacierkz_open_fds Number of open file descriptors.",
        "# TYPE glacierkz_open_fds gauge",
        f"glacierkz_open_fds {process.num_fds()}",
        "",
        "# HELP glacierkz_threads Number of threads in the process.",
        "# TYPE glacierkz_threads gauge",
        f"glacierkz_threads {process.num_threads()}",
        "",
        "# HELP glacierkz_tasks_total Total number of registered tasks.",
        "# TYPE glacierkz_tasks_total gauge",
        "glacierkz_tasks_total 0",
        "",
    ]

    return Response(
        content="\n".join(lines),
        media_type="text/plain; version=0.0.4",
    )


@router.get(
    "/system",
    summary="Detailed system resource metrics",
)
async def system_metrics() -> dict[str, Any]:
    """Return system-level resource metrics (CPU, memory, disk, uptime).

    The response includes per-core CPU load averages, virtual/physical
    memory breakdown, and root-filesystem disk usage.  All byte values are
    reported in raw bytes – use the ``/metrics`` endpoint for human-friendly
    formatting if needed.
    """
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    load = os.getloadavg()
    process = psutil.Process(os.getpid())

    return {
        "uptime_seconds": round(_uptime_seconds(), 2),
        "cpu": {
            "percent": psutil.cpu_percent(interval=0.1),
            "count_logical": psutil.cpu_count(logical=True),
            "count_physical": psutil.cpu_count(logical=False),
            "load_avg_1m": load[0],
            "load_avg_5m": load[1],
            "load_avg_15m": load[2],
        },
        "memory": {
            "total_bytes": mem.total,
            "available_bytes": mem.available,
            "used_bytes": mem.used,
            "percent": mem.percent,
            "total_human": _fmt_bytes(mem.total),
            "used_human": _fmt_bytes(mem.used),
        },
        "disk": {
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
            "percent": disk.percent,
            "total_human": _fmt_bytes(disk.total),
            "used_human": _fmt_bytes(disk.used),
        },
        "process": {
            "pid": os.getpid(),
            "rss_bytes": process.memory_info().rss,
            "threads": process.num_threads(),
            "open_fds": process.num_fds(),
        },
    }


@router.get(
    "/status",
    summary="Overall system health status",
)
async def overall_status() -> dict[str, Any]:
    """Return a lightweight health summary suitable for liveness probes.

    The status is ``healthy`` when both CPU and memory usage are below 95 %;
    otherwise it is ``degraded``.

    .. note::

       This endpoint does **not** perform any external checks (database,
       object storage, etc.).  Extend as needed for deeper health probes.
    """
    mem = psutil.virtual_memory()
    cpu_pct = psutil.cpu_percent(interval=0.1)

    healthy = cpu_pct < 95 and mem.percent < 95

    return {
        "status": "healthy" if healthy else "degraded",
        "uptime_seconds": round(_uptime_seconds(), 2),
        "cpu_percent": cpu_pct,
        "memory_percent": mem.percent,
        "checks": {
            "cpu_ok": cpu_pct < 95,
            "memory_ok": mem.percent < 95,
        },
    }
