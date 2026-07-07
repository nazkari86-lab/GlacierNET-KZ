"""Tests for monitoring routes — metrics, system info, health."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "glacierkz-api"))

from app.monitoring.health import HealthStatus, get_health_checker
from app.monitoring.metrics import MetricsCollector, get_metrics
from app.monitoring.system import get_system_info


class TestMetricsCollector:
    def test_inc_counter(self):
        c = MetricsCollector()
        c.counter("test_counter", labels={"method": "GET"})
        c.inc("test_counter", labels={"method": "GET"})
        c.inc("test_counter", labels={"method": "GET"})
        assert c.get_counter("test_counter", labels={"method": "GET"}) == 2

    def test_set_gauge(self):
        c = MetricsCollector()
        c.gauge("test_gauge")
        c.set("test_gauge", 42.5)
        assert c.get_gauge("test_gauge") == 42.5

    def test_render_output(self):
        c = MetricsCollector()
        c.counter("some_counter", labels={"a": "b"})
        c.inc("some_counter", labels={"a": "b"})
        output = c.render()
        assert "some_counter" in output
        assert "# HELP" in output
        assert "# TYPE" in output

    def test_default_counter_zero(self):
        c = MetricsCollector()
        assert c.get_counter("nonexistent") == 0

    def test_default_gauge_zero(self):
        c = MetricsCollector()
        assert c.get_gauge("nonexistent") == 0

    def test_labels_isolation(self):
        c = MetricsCollector()
        c.counter("test", labels={"method": "GET"})
        c.counter("test", labels={"method": "POST"})
        c.inc("test", labels={"method": "GET"})
        c.inc("test", labels={"method": "POST"})
        assert c.get_counter("test", labels={"method": "GET"}) == 1
        assert c.get_counter("test", labels={"method": "POST"}) == 1


class TestGetMetrics:
    def test_returns_metrics_collector(self):
        collector = get_metrics()
        assert isinstance(collector, MetricsCollector)

    def test_singleton(self):
        c1 = get_metrics()
        c2 = get_metrics()
        assert c1 is c2


class TestGetSystemInfo:
    def test_returns_dict(self):
        info = get_system_info()
        assert isinstance(info, dict)

    def test_has_platform_key(self):
        info = get_system_info()
        assert "platform" in info

    def test_has_python_version(self):
        info = get_system_info()
        assert "python_version" in info["platform"]


class TestHealthChecker:
    def test_health_checker_singleton(self):
        h1 = get_health_checker()
        h2 = get_health_checker()
        assert h1 is h2

    @pytest.mark.asyncio
    async def test_readiness_returns_report(self):
        checker = get_health_checker()
        report = await checker.readiness()
        assert hasattr(report, "status")
        assert isinstance(report.status, HealthStatus)

    @pytest.mark.asyncio
    async def test_liveness_returns_dict(self):
        checker = get_health_checker()
        result = await checker.liveness()
        assert isinstance(result, dict)
        assert "status" in result
