"""Health check system — deep checks, dependencies, readiness/liveness."""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Optional

logger = logging.getLogger("glacierkz.health")


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class CheckResult:
    name: str
    status: HealthStatus
    message: str = ""
    duration_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "duration_ms": round(self.duration_ms, 2),
        }
        if self.details:
            d["details"] = self.details
        return d


@dataclass
class HealthReport:
    status: HealthStatus
    checks: list[CheckResult]
    timestamp: float
    uptime: float

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "uptime_seconds": round(self.uptime, 2),
            "checks": [c.to_dict() for c in self.checks],
        }


class HealthChecker:
    """Manages health checks — liveness, readiness, deep checks."""

    def __init__(self):
        self._checks: dict[str, Callable[[], Coroutine] | Callable] = {}
        self._start_time = time.time()

    def register(self, name: str, check_fn: Callable[[], Coroutine] | Callable) -> None:
        self._checks[name] = check_fn

    def unregister(self, name: str) -> None:
        self._checks.pop(name, None)

    async def run_check(self, name: str) -> CheckResult:
        check_fn = self._checks.get(name)
        if not check_fn:
            return CheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check '{name}' not found",
            )
        start = time.monotonic()
        try:
            if inspect.iscoroutinefunction(check_fn):
                result = await asyncio.wait_for(check_fn(), timeout=10.0)
            else:
                result = check_fn()
            duration = (time.monotonic() - start) * 1000
            if isinstance(result, CheckResult):
                result.duration_ms = duration
                return result
            return CheckResult(
                name=name,
                status=HealthStatus.HEALTHY,
                message=str(result) if result else "OK",
                duration_ms=duration,
            )
        except asyncio.TimeoutError:
            return CheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message="Check timed out",
                duration_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as exc:
            return CheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"{type(exc).__name__}: {exc}",
                duration_ms=(time.monotonic() - start) * 1000,
            )

    async def run_all(self) -> HealthReport:
        checks = await asyncio.gather(
            *[self.run_check(name) for name in self._checks],
            return_exceptions=False,
        )
        statuses = [c.status for c in checks]
        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall = HealthStatus.UNHEALTHY
        else:
            overall = HealthStatus.DEGRADED
        return HealthReport(
            status=overall,
            checks=list(checks),
            timestamp=time.time(),
            uptime=time.time() - self._start_time,
        )

    async def liveness(self) -> dict:
        return {"status": "alive", "timestamp": time.time()}

    async def readiness(self) -> HealthReport:
        return await self.run_all()

    def register_defaults(self) -> None:
        self.register("disk_space", _check_disk_space)
        self.register("memory", _check_memory)
        self.register("asyncio_loop", _check_event_loop)
        self.register("uptime", _check_uptime)


async def _check_disk_space() -> CheckResult:
    import shutil

    usage = shutil.disk_usage("/")
    pct = (usage.used / usage.total) * 100
    status = HealthStatus.HEALTHY if pct < 90 else (HealthStatus.DEGRADED if pct < 95 else HealthStatus.UNHEALTHY)
    return CheckResult(
        name="disk_space",
        status=status,
        message=f"{pct:.1f}% used",
        details={
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "percent_used": round(pct, 1),
        },
    )


async def _check_memory() -> CheckResult:
    try:
        import psutil

        mem = psutil.virtual_memory()
        status = (
            HealthStatus.HEALTHY
            if mem.percent < 85
            else (HealthStatus.DEGRADED if mem.percent < 95 else HealthStatus.UNHEALTHY)
        )
        return CheckResult(
            name="memory",
            status=status,
            message=f"{mem.percent}% used",
            details={
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "percent_used": mem.percent,
            },
        )
    except ImportError:
        return CheckResult(
            name="memory",
            status=HealthStatus.HEALTHY,
            message="psutil not installed, skipping",
        )


async def _check_event_loop() -> CheckResult:
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        return CheckResult(name="asyncio_loop", status=HealthStatus.UNHEALTHY, message="Event loop closed")
    return CheckResult(
        name="asyncio_loop",
        status=HealthStatus.HEALTHY,
        message="Event loop running",
    )


async def _check_uptime() -> CheckResult:
    return CheckResult(
        name="uptime",
        status=HealthStatus.HEALTHY,
        message="Service operational",
    )


_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    global _checker
    if _checker is None:
        _checker = HealthChecker()
        _checker.register_defaults()
    return _checker
