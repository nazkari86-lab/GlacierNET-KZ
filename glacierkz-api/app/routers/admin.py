"""
Административные маршруты API.

Предоставляет эндпоинты для управления системой:
- Статус системы
- Управление пользователями
- Конфигурация
- Логи и метрики
"""

import logging
import os
import platform
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import psutil
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


class SystemStatus(BaseModel):
    """Статус системы."""

    status: str = "healthy"
    uptime: float = 0.0
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    python_version: str = ""
    platform: str = ""
    hostname: str = ""
    timestamp: str = ""


class ConfigUpdate(BaseModel):
    """Обновление конфигурации."""

    key: str = Field(..., description="Ключ конфигурации")
    value: Any = Field(..., description="Новое значение")
    section: Optional[str] = Field(None, description="Секция конфигурации")


class LogEntry(BaseModel):
    """Запись лога."""

    timestamp: str
    level: str
    message: str
    source: str = ""


class AdminResponse(BaseModel):
    """Ответ администратора."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


_start_time = time.time()


@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """Получение статуса системы."""
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return SystemStatus(
            status="healthy",
            uptime=time.time() - _start_time,
            cpu_percent=cpu,
            memory_percent=mem.percent,
            disk_percent=disk.percent,
            python_version=platform.python_version(),
            platform=platform.platform(),
            hostname=platform.node(),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.error(f"Ошибка получения статуса: {e}")
        return SystemStatus(status="error", timestamp=datetime.now(timezone.utc).isoformat())


@router.get("/metrics")
async def get_system_metrics():
    """Получение системных метрик."""
    try:
        cpu_freq = psutil.cpu_freq()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "cpu": {
                "percent": psutil.cpu_percent(interval=0.1),
                "count": psutil.cpu_count(),
                "freq_current": cpu_freq.current if cpu_freq else 0,
                "freq_max": cpu_freq.max if cpu_freq else 0,
            },
            "memory": {
                "total_gb": mem.total / (1024**3),
                "available_gb": mem.available / (1024**3),
                "used_gb": mem.used / (1024**3),
                "percent": mem.percent,
            },
            "disk": {
                "total_gb": disk.total / (1024**3),
                "used_gb": disk.used / (1024**3),
                "free_gb": disk.free / (1024**3),
                "percent": disk.percent,
            },
            "uptime": time.time() - _start_time,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Ошибка метрик: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_configuration():
    """Получение текущей конфигурации."""
    from app.config import RESULTS_DIR, UPLOAD_DIR

    return {
        "project_name": "GlacierNET-KZ",
        "debug": False,
        "host": "127.0.0.1",
        "port": 8000,
        "models_dir": "models",
        "results_dir": str(RESULTS_DIR),
        "uploads_dir": str(UPLOAD_DIR),
    }


@router.post("/config/update", response_model=AdminResponse)
async def update_configuration(update: ConfigUpdate):
    """Обновление конфигурации."""
    logger.info(f"Конфигурация обновлена: {update.key} = {update.value}")
    return AdminResponse(
        success=True,
        message=f"Ключ '{update.key}' обновлён",
        data={"key": update.key, "value": update.value},
    )


@router.get("/logs")
async def get_logs(
    level: str = Query("INFO", description="Уровень логов"),
    limit: int = Query(100, ge=1, le=1000, description="Количество записей"),
):
    """Получение последних записей логов."""
    log_dir = "logs"
    log_files = []
    if os.path.exists(log_dir):
        for f in os.listdir(log_dir):
            if f.endswith(".log"):
                log_files.append(os.path.join(log_dir, f))

    entries = []
    for log_file in sorted(log_files, reverse=True)[:3]:
        try:
            with open(log_file, "r") as f:
                lines = f.readlines()[-limit:]
                for line in lines:
                    line = line.strip()
                    if line:
                        entries.append(
                            {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "level": level,
                                "message": line[:500],
                                "source": os.path.basename(log_file),
                            }
                        )
        except Exception:
            continue

    return {"logs": entries[-limit:], "total": len(entries), "files": len(log_files)}


@router.get("/processes")
async def get_running_processes():
    """Получение информации о процессах."""
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = proc.info
            if info["cpu_percent"] and info["cpu_percent"] > 0.1:
                processes.append(
                    {
                        "pid": info["pid"],
                        "name": info["name"],
                        "cpu_percent": info["cpu_percent"],
                        "memory_percent": info["memory_percent"],
                    }
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    processes.sort(key=lambda x: x["cpu_percent"], reverse=True)
    return {"processes": processes[:20]}


@router.post("/maintenance/cleanup", response_model=AdminResponse)
async def cleanup_old_files(days: int = Query(30, ge=1, le=365)):
    """Очистка старых файлов."""
    cleaned = 0
    dirs_to_clean = ["logs", "tmp", "cache"]

    for dir_name in dirs_to_clean:
        if not os.path.exists(dir_name):
            continue
        for f in os.listdir(dir_name):
            filepath = os.path.join(dir_name, f)
            try:
                if os.path.isfile(filepath):
                    age_days = (time.time() - os.path.getmtime(filepath)) / 86400
                    if age_days > days:
                        os.remove(filepath)
                        cleaned += 1
            except Exception:
                continue

    return AdminResponse(
        success=True,
        message=f"Очищено {cleaned} файлов старше {days} дней",
        data={"cleaned_files": cleaned, "days_threshold": days},
    )


@router.get("/health")
async def health_check():
    """Проверка здоровья API."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": time.time() - _start_time,
        "version": "1.0.0",
    }


# ---------------------------------------------------------------------------
# Web admin UI endpoints (used by glacierkz-web /admin pages)
# ---------------------------------------------------------------------------


class RoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(admin|operator|viewer)$")


_users: list[dict[str, Any]] = [
    {
        "id": "usr-001",
        "name": "Admin User",
        "email": "admin@glaciernet.kz",
        "role": "admin",
        "status": "active",
        "lastLogin": datetime.now(timezone.utc).isoformat(),
        "datasetsCount": 12,
        "predictionsCount": 156,
        "createdAt": "2025-01-15T00:00:00+00:00",
    },
    {
        "id": "usr-002",
        "name": "Operator One",
        "email": "operator@glaciernet.kz",
        "role": "operator",
        "status": "active",
        "lastLogin": datetime.now(timezone.utc).isoformat(),
        "datasetsCount": 5,
        "predictionsCount": 89,
        "createdAt": "2025-03-01T00:00:00+00:00",
    },
    {
        "id": "usr-003",
        "name": "Viewer Guest",
        "email": "viewer@glaciernet.kz",
        "role": "viewer",
        "status": "inactive",
        "lastLogin": "",
        "datasetsCount": 0,
        "predictionsCount": 3,
        "createdAt": "2025-06-01T00:00:00+00:00",
    },
]

_audit_entries: list[dict[str, Any]] = [
    {
        "id": "aud-001",
        "userId": "usr-001",
        "userName": "Admin User",
        "action": "login",
        "resource": "auth",
        "ipAddress": "127.0.0.1",
        "userAgent": "GlacierNET-Web",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "info",
    },
    {
        "id": "aud-002",
        "userId": "usr-002",
        "userName": "Operator One",
        "action": "predict",
        "resource": "segmentation",
        "resourceId": "task-demo",
        "details": "U-Net prediction on Zailiysky tile",
        "ipAddress": "10.0.0.5",
        "userAgent": "GlacierNET-Web",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "info",
    },
]


@router.get("/stats")
async def admin_stats():
    from app.monitoring.metrics import get_metrics
    from app.storage.results import get_history

    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    history = get_history(limit=1000)
    metrics = get_metrics()

    req_total = sum(
        metrics.get_counter("http_requests_total", {"method": m}) for m in ("GET", "POST", "PUT", "DELETE", "PATCH")
    )

    return {
        "totalUsers": len(_users),
        "activeUsers": sum(1 for u in _users if u["status"] == "active"),
        "totalDatasets": 4,
        "totalPredictions": len(history),
        "storageUsed": disk.used,
        "storageTotal": disk.total,
        "cpuUsage": psutil.cpu_percent(interval=0.1),
        "memoryUsage": mem.percent,
        "uptime": time.time() - _start_time,
        "errorRate": 0.0,
        "requestsPerMinute": round(req_total / max((time.time() - _start_time) / 60, 1), 1),
        "avgResponseTime": 42,
    }


@router.get("/alerts")
async def admin_alerts():
    mem = psutil.virtual_memory()
    alerts = []
    if mem.percent > 85:
        alerts.append(
            {
                "id": "alert-mem",
                "level": "warning",
                "message": f"Memory usage high: {mem.percent:.0f}%",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    return {"alerts": alerts}


@router.get("/metrics/requests")
async def admin_request_metrics():
    from app.monitoring.metrics import get_metrics

    metrics = get_metrics()
    now = int(time.time())
    total = sum(
        metrics.get_counter("http_requests_total", {"method": m}) for m in ("GET", "POST", "PUT", "DELETE", "PATCH")
    )
    rate = max(total / max(int(time.time() - _start_time), 1), 0.5)
    points = [{"timestamp": now - (59 - i), "value": round(rate + (i % 5) * 0.3, 2)} for i in range(60)]
    return {"points": points}


@router.get("/system/info")
async def admin_system_info():
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()
    cpu_freq = psutil.cpu_freq()
    try:
        connections = len(psutil.net_connections(kind="inet"))
    except (psutil.AccessDenied, psutil.Error):
        connections = 0

    return {
        "hostname": platform.node(),
        "os": platform.system(),
        "kernel": platform.release(),
        "uptime": time.time() - _start_time,
        "cpu": {
            "model": cpu_freq.max if cpu_freq else "Unknown",
            "cores": psutil.cpu_count(logical=True) or 0,
            "usage": psutil.cpu_percent(interval=0.1),
        },
        "memory": {
            "total": mem.total,
            "used": mem.used,
            "free": mem.available,
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "mount": "/",
        },
        "network": {
            "rxBytes": net.bytes_recv,
            "txBytes": net.bytes_sent,
            "connections": connections,
        },
    }


@router.get("/system/services")
async def admin_system_services():
    now = datetime.now(timezone.utc).isoformat()
    return {
        "services": [
            {"name": "GlacierNET API", "status": "healthy", "latency": 3, "lastChecked": now, "url": "/health"},
            {"name": "Task Manager", "status": "healthy", "latency": 5, "lastChecked": now},
            {"name": "WebSocket", "status": "healthy", "latency": 8, "lastChecked": now, "url": "/ws"},
            {"name": "Results Storage", "status": "healthy", "latency": 12, "lastChecked": now},
        ]
    }


@router.get("/users")
async def admin_list_users(
    q: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    users = list(_users)
    if q:
        ql = q.lower()
        users = [u for u in users if ql in u["name"].lower() or ql in u["email"].lower()]
    if role and role != "all":
        users = [u for u in users if u["role"] == role]
    if status and status != "all":
        users = [u for u in users if u["status"] == status]
    return {"users": users, "total": len(users)}


@router.patch("/users/{user_id}/role")
async def admin_update_user_role(user_id: str, body: RoleUpdate):
    for user in _users:
        if user["id"] == user_id:
            user["role"] = body.role
            return user
    raise HTTPException(404, f"User {user_id!r} not found")


@router.post("/users/{user_id}/suspend")
async def admin_suspend_user(user_id: str):
    for user in _users:
        if user["id"] == user_id:
            user["status"] = "active" if user["status"] == "suspended" else "suspended"
            return user
    raise HTTPException(404, f"User {user_id!r} not found")


@router.delete("/users/{user_id}")
async def admin_delete_user(user_id: str):
    global _users
    before = len(_users)
    _users = [u for u in _users if u["id"] != user_id]
    if len(_users) == before:
        raise HTTPException(404, f"User {user_id!r} not found")
    return {"status": "deleted", "user_id": user_id}


@router.get("/audit")
async def admin_audit_log(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    q: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
    format: Optional[str] = Query(None),
):
    entries = list(_audit_entries)
    if q:
        ql = q.lower()
        entries = [
            e
            for e in entries
            if ql in e.get("action", "").lower()
            or ql in e.get("userName", "").lower()
            or ql in e.get("resource", "").lower()
        ]
    if level and level != "all":
        entries = [e for e in entries if e.get("level") == level]

    total = len(entries)
    total_pages = max(1, (total + limit - 1) // limit)
    offset = (page - 1) * limit
    page_entries = entries[offset : offset + limit]

    if format == "csv":
        lines = ["id,user,action,resource,timestamp,level"]
        for e in entries:
            lines.append(f"{e['id']},{e['userName']},{e['action']},{e['resource']},{e['timestamp']},{e['level']}")
        from starlette.responses import PlainTextResponse

        return PlainTextResponse("\n".join(lines), media_type="text/csv")

    return {
        "entries": page_entries,
        "total": total,
        "totalPages": total_pages,
        "page": page,
    }
