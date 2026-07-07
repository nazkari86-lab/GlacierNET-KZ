"""Tests for app/monitoring/health.py — HealthChecker, HealthReport, CheckResult, HealthStatus."""

from __future__ import annotations

import asyncio

import pytest

from app.monitoring.health import (
    CheckResult,
    HealthChecker,
    HealthReport,
    HealthStatus,
    _check_disk_space,
    _check_event_loop,
    _check_memory,
    _check_uptime,
    get_health_checker,
)


class TestHealthStatus:
    def test_healthy_value(self):
        assert HealthStatus.HEALTHY.value == "healthy"

    def test_degraded_value(self):
        assert HealthStatus.DEGRADED.value == "degraded"

    def test_unhealthy_value(self):
        assert HealthStatus.UNHEALTHY.value == "unhealthy"


class TestCheckResult:
    def test_to_dict_basic(self):
        r = CheckResult(name="test", status=HealthStatus.HEALTHY, message="ok")
        d = r.to_dict()
        assert d["name"] == "test"
        assert d["status"] == "healthy"
        assert d["message"] == "ok"
        assert "details" not in d

    def test_to_dict_with_details(self):
        r = CheckResult(name="test", status=HealthStatus.HEALTHY, details={"key": "val"})
        d = r.to_dict()
        assert d["details"] == {"key": "val"}

    def test_to_dict_duration(self):
        r = CheckResult(name="test", status=HealthStatus.HEALTHY, duration_ms=12.345)
        d = r.to_dict()
        assert d["duration_ms"] == 12.35


class TestHealthReport:
    def test_to_dict(self):
        checks = [CheckResult(name="c1", status=HealthStatus.HEALTHY)]
        report = HealthReport(
            status=HealthStatus.HEALTHY,
            checks=checks,
            timestamp=1000.0,
            uptime=500.0,
        )
        d = report.to_dict()
        assert d["status"] == "healthy"
        assert d["timestamp"] == 1000.0
        assert d["uptime_seconds"] == 500.0
        assert len(d["checks"]) == 1


class TestHealthChecker:
    @pytest.mark.asyncio
    async def test_register_and_run_check(self):
        checker = HealthChecker()

        async def ok_check():
            return CheckResult(name="ok", status=HealthStatus.HEALTHY, message="fine")

        checker.register("ok", ok_check)
        result = await checker.run_check("ok")
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_run_check_not_found(self):
        checker = HealthChecker()
        result = await checker.run_check("nonexistent")
        assert result.status == HealthStatus.UNHEALTHY
        assert "not found" in result.message

    @pytest.mark.asyncio
    async def test_run_check_returns_string(self):
        checker = HealthChecker()

        def str_check():
            return "all good"

        checker.register("str_check", str_check)
        result = await checker.run_check("str_check")
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "all good"

    @pytest.mark.asyncio
    async def test_run_check_returns_none(self):
        checker = HealthChecker()

        def none_check():
            return None

        checker.register("none_check", none_check)
        result = await checker.run_check("none_check")
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "OK"

    @pytest.mark.asyncio
    async def test_run_check_raises_exception(self):
        checker = HealthChecker()

        def bad_check():
            raise ValueError("boom")

        checker.register("bad", bad_check)
        result = await checker.run_check("bad")
        assert result.status == HealthStatus.UNHEALTHY
        assert "ValueError" in result.message

    @pytest.mark.asyncio
    async def test_run_check_timeout(self):
        checker = HealthChecker()

        async def slow_check():
            await asyncio.sleep(100)

        checker.register("slow", slow_check)
        result = await checker.run_check("slow")
        assert result.status == HealthStatus.UNHEALTHY
        assert "timed out" in result.message

    @pytest.mark.asyncio
    async def test_unregister(self):
        checker = HealthChecker()

        def ok_check():
            return "ok"

        checker.register("ok", ok_check)
        checker.unregister("ok")
        result = await checker.run_check("ok")
        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_unregister_nonexistent(self):
        checker = HealthChecker()
        checker.unregister("nonexistent")

    @pytest.mark.asyncio
    async def test_run_all_healthy(self):
        checker = HealthChecker()

        async def ok1():
            return CheckResult(name="ok1", status=HealthStatus.HEALTHY)

        async def ok2():
            return CheckResult(name="ok2", status=HealthStatus.HEALTHY)

        checker.register("ok1", ok1)
        checker.register("ok2", ok2)
        report = await checker.run_all()
        assert report.status == HealthStatus.HEALTHY
        assert len(report.checks) == 2

    @pytest.mark.asyncio
    async def test_run_all_degraded(self):
        checker = HealthChecker()

        async def ok():
            return CheckResult(name="ok", status=HealthStatus.HEALTHY)

        async def degraded():
            return CheckResult(name="degraded", status=HealthStatus.DEGRADED)

        checker.register("ok", ok)
        checker.register("degraded", degraded)
        report = await checker.run_all()
        assert report.status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_run_all_unhealthy(self):
        checker = HealthChecker()

        async def ok():
            return CheckResult(name="ok", status=HealthStatus.HEALTHY)

        async def bad():
            return CheckResult(name="bad", status=HealthStatus.UNHEALTHY)

        checker.register("ok", ok)
        checker.register("bad", bad)
        report = await checker.run_all()
        assert report.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_liveness(self):
        checker = HealthChecker()
        result = await checker.liveness()
        assert result["status"] == "alive"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_readiness(self):
        checker = HealthChecker()

        async def ok():
            return CheckResult(name="ok", status=HealthStatus.HEALTHY)

        checker.register("ok", ok)
        report = await checker.readiness()
        assert isinstance(report, HealthReport)

    @pytest.mark.asyncio
    async def test_register_defaults(self):
        checker = HealthChecker()
        checker.register_defaults()
        assert "disk_space" in checker._checks
        assert "memory" in checker._checks
        assert "asyncio_loop" in checker._checks
        assert "uptime" in checker._checks


class TestDefaultChecks:
    @pytest.mark.asyncio
    async def test_check_disk_space(self):
        result = await _check_disk_space()
        assert result.name == "disk_space"
        assert result.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY)
        assert "total_gb" in result.details

    @pytest.mark.asyncio
    async def test_check_memory(self):
        result = await _check_memory()
        assert result.name == "memory"

    @pytest.mark.asyncio
    async def test_check_event_loop(self):
        result = await _check_event_loop()
        assert result.name == "asyncio_loop"
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_uptime(self):
        result = await _check_uptime()
        assert result.name == "uptime"
        assert result.status == HealthStatus.HEALTHY


class TestGetHealthChecker:
    def test_singleton(self):
        c1 = get_health_checker()
        c2 = get_health_checker()
        assert c1 is c2

    def test_has_defaults(self):
        checker = get_health_checker()
        assert len(checker._checks) >= 4
