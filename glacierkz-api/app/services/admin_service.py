"""
Сервис администрирования.

Предоставляет функции для:
- Мониторинга состояния системы
- Управления ресурсами
- Очистки и обслуживания
- Сбора метрик
"""

import gc
import logging
import os
import platform
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """Системные метрики."""

    cpu_percent: float = 0.0
    memory_total_gb: float = 0.0
    memory_used_gb: float = 0.0
    memory_percent: float = 0.0
    disk_total_gb: float = 0.0
    disk_used_gb: float = 0.0
    disk_percent: float = 0.0
    uptime: float = 0.0
    timestamp: str = ""


@dataclass
class ServiceStatus:
    """Статус сервиса."""

    name: str
    status: str = "unknown"
    uptime: float = 0.0
    last_check: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


class AdminService:
    """Сервис администрирования системы."""

    def __init__(self):
        self._start_time = time.time()
        self._operations_log: List[Dict[str, Any]] = []
        self._alerts: List[Dict[str, Any]] = []
        self._metrics_history: List[SystemMetrics] = []
        self._max_history = 1000

    def get_system_metrics(self) -> SystemMetrics:
        """Сбор системных метрик."""
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            metrics = SystemMetrics(
                cpu_percent=cpu,
                memory_total_gb=mem.total / (1024**3),
                memory_used_gb=mem.used / (1024**3),
                memory_percent=mem.percent,
                disk_total_gb=disk.total / (1024**3),
                disk_used_gb=disk.used / (1024**3),
                disk_percent=disk.percent,
                uptime=time.time() - self._start_time,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            self._metrics_history.append(metrics)
            if len(self._metrics_history) > self._max_history:
                self._metrics_history = self._metrics_history[-self._max_history :]

            return metrics

        except Exception as e:
            logger.error(f"Ошибка сбора метрик: {e}")
            return SystemMetrics(timestamp=datetime.now(timezone.utc).isoformat())

    def get_system_status(self) -> Dict[str, Any]:
        """Получение полного статуса системы."""
        metrics = self.get_system_metrics()

        gpu_info = self._get_gpu_info()
        disk_io = self._get_disk_io()
        network = self._get_network_info()

        return {
            "status": "healthy",
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "python": platform.python_version(),
                "hostname": platform.node(),
            },
            "metrics": {
                "cpu_percent": metrics.cpu_percent,
                "memory": {
                    "total_gb": round(metrics.memory_total_gb, 2),
                    "used_gb": round(metrics.memory_used_gb, 2),
                    "percent": metrics.memory_percent,
                },
                "disk": {
                    "total_gb": round(metrics.disk_total_gb, 2),
                    "used_gb": round(metrics.disk_used_gb, 2),
                    "percent": metrics.disk_percent,
                },
            },
            "gpu": gpu_info,
            "disk_io": disk_io,
            "network": network,
            "uptime": metrics.uptime,
            "timestamp": metrics.timestamp,
        }

    def cleanup_old_files(
        self,
        directories: Optional[List[str]] = None,
        max_age_days: int = 30,
        extensions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Очистка старых файлов."""
        if directories is None:
            directories = ["logs", "tmp", "cache", "exports"]

        cleaned = 0
        total_size = 0
        errors = []

        for dir_name in directories:
            if not os.path.exists(dir_name):
                continue

            for root, dirs, files in os.walk(dir_name):
                for f in files:
                    filepath = os.path.join(root, f)
                    try:
                        if extensions and not any(f.endswith(ext) for ext in extensions):
                            continue

                        file_age = time.time() - os.path.getmtime(filepath)
                        if file_age > max_age_days * 86400:
                            file_size = os.path.getsize(filepath)
                            os.remove(filepath)
                            cleaned += 1
                            total_size += file_size
                    except Exception as e:
                        errors.append({"file": filepath, "error": str(e)})

        self._log_operation(
            "cleanup",
            {
                "cleaned_files": cleaned,
                "total_size_mb": total_size / (1024 * 1024),
                "max_age_days": max_age_days,
            },
        )

        return {
            "cleaned_files": cleaned,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "errors": errors,
        }

    def get_directory_stats(self, directory: str = ".") -> Dict[str, Any]:
        """Статистика директории."""
        if not os.path.exists(directory):
            return {"error": f"Директория {directory} не найдена"}

        total_files = 0
        total_size = 0
        by_extension: Dict[str, int] = {}
        by_extension_size: Dict[str, int] = {}

        for root, dirs, files in os.walk(directory):
            for f in files:
                filepath = os.path.join(root, f)
                try:
                    size = os.path.getsize(filepath)
                    total_files += 1
                    total_size += size

                    ext = os.path.splitext(f)[1].lower() or "no_ext"
                    by_extension[ext] = by_extension.get(ext, 0) + 1
                    by_extension_size[ext] = by_extension_size.get(ext, 0) + size
                except OSError:
                    continue

        top_extensions = sorted(by_extension.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "directory": directory,
            "total_files": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "top_extensions": [{"ext": ext, "count": count} for ext, count in top_extensions],
            "by_extension_size": {
                ext: round(size / (1024 * 1024), 2)
                for ext, size in sorted(by_extension_size.items(), key=lambda x: x[1], reverse=True)[:10]
            },
        }

    def get_process_info(self) -> List[Dict[str, Any]]:
        """Информация о процессах."""
        processes = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
            try:
                info = proc.info
                if info["cpu_percent"] and info["cpu_percent"] > 0.1:
                    processes.append(
                        {
                            "pid": info["pid"],
                            "name": info["name"],
                            "cpu_percent": info["cpu_percent"],
                            "memory_percent": round(info["memory_percent"] or 0, 1),
                            "status": info["status"],
                        }
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        processes.sort(key=lambda x: x["cpu_percent"], reverse=True)
        return processes[:20]

    def force_garbage_collection(self) -> Dict[str, int]:
        """Принудительная сборка мусора."""
        before = gc.get_count()
        collected = gc.collect()
        after = gc.get_count()

        return {
            "collected": collected,
            "before": list(before),
            "after": list(after),
        }

    def get_disk_io_stats(self) -> Dict[str, Any]:
        """Статистика ввода/вывода диска."""
        return self._get_disk_io()

    def get_network_stats(self) -> Dict[str, Any]:
        """Сетевая статистика."""
        return self._get_network_info()

    def add_alert(self, level: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Добавление системного оповещения."""
        alert = {
            "level": level,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._alerts.append(alert)
        if len(self._alerts) > 500:
            self._alerts = self._alerts[-500:]

        log_method = getattr(logger, level, logger.info)
        log_method(f"Alert: {message}")

    def get_alerts(self, level: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Получение оповещений."""
        alerts = list(self._alerts)
        if level:
            alerts = [a for a in alerts if a["level"] == level]
        return alerts[-limit:]

    def clear_alerts(self) -> int:
        """Очистка оповещений."""
        count = len(self._alerts)
        self._alerts.clear()
        return count

    def get_metrics_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """История метрик."""
        history = self._metrics_history[-limit:]
        return [
            {
                "cpu_percent": m.cpu_percent,
                "memory_percent": m.memory_percent,
                "disk_percent": m.disk_percent,
                "uptime": m.uptime,
                "timestamp": m.timestamp,
            }
            for m in history
        ]

    def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья системы."""
        checks = {}

        checks["cpu"] = {
            "status": "ok" if psutil.cpu_percent() < 90 else "warning",
            "value": psutil.cpu_percent(),
        }

        mem = psutil.virtual_memory()
        checks["memory"] = {
            "status": "ok" if mem.percent < 85 else "warning",
            "value": mem.percent,
        }

        disk = psutil.disk_usage("/")
        checks["disk"] = {
            "status": "ok" if disk.percent < 90 else "warning",
            "value": disk.percent,
        }

        all_ok = all(c["status"] == "ok" for c in checks.values())

        return {
            "status": "healthy" if all_ok else "degraded",
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _get_gpu_info(self) -> Dict[str, Any]:
        """Получение информации о GPU."""
        try:
            import subprocess

            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.used,memory.total,utilization.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(", ")
                if len(parts) >= 4:
                    return {
                        "name": parts[0],
                        "memory_used_mb": int(parts[1]),
                        "memory_total_mb": int(parts[2]),
                        "utilization_percent": int(parts[3]),
                        "available": True,
                    }
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass

        return {"available": False}

    def _get_disk_io(self) -> Dict[str, Any]:
        """Статистика ввода/вывода."""
        try:
            io = psutil.disk_io_counters()
            return {
                "read_mb": round(io.read_bytes / (1024 * 1024), 2) if io else 0,
                "write_mb": round(io.write_bytes / (1024 * 1024), 2) if io else 0,
                "read_count": io.read_count if io else 0,
                "write_count": io.write_count if io else 0,
            }
        except Exception:
            return {"read_mb": 0, "write_mb": 0}

    def _get_network_info(self) -> Dict[str, Any]:
        """Сетевая информация."""
        try:
            net = psutil.net_io_counters()
            return {
                "bytes_sent_mb": round(net.bytes_sent / (1024 * 1024), 2),
                "bytes_recv_mb": round(net.bytes_recv / (1024 * 1024), 2),
                "packets_sent": net.packets_sent,
                "packets_recv": net.packets_recv,
            }
        except Exception:
            return {"bytes_sent_mb": 0, "bytes_recv_mb": 0}

    def _log_operation(self, operation: str, details: Dict[str, Any]) -> None:
        """Логирование операции."""
        entry = {
            "operation": operation,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._operations_log.append(entry)
        if len(self._operations_log) > 1000:
            self._operations_log = self._operations_log[-1000:]


admin_service = AdminService()
