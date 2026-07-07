"""Tests for app/monitoring/metrics.py — MetricsCollector (additional branches)."""

from __future__ import annotations

from app.monitoring.metrics import MetricsCollector, get_metrics


class TestMetricsCollectorAdditional:
    def test_counter_inc_with_labels(self):
        mc = MetricsCollector()
        mc.counter("req_count", "Request count", labels={"method": ""})
        mc.inc("req_count", labels={"method": "GET"})
        mc.inc("req_count", labels={"method": "GET"})
        assert mc.get_counter("req_count", {"method": "GET"}) == 2

    def test_counter_inc_default(self):
        mc = MetricsCollector()
        mc.counter("total", "Total")
        mc.inc("total")
        mc.inc("total")
        assert mc.get_counter("total") == 2

    def test_gauge_set(self):
        mc = MetricsCollector()
        mc.gauge("queue_size", "Queue size")
        mc.set("queue_size", 42)
        assert mc.get_gauge("queue_size") == 42

    def test_gauge_set_with_labels(self):
        mc = MetricsCollector()
        mc.gauge("mem", "Memory", labels={"host": ""})
        mc.set("mem", 100, labels={"host": "a"})
        assert mc.get_gauge("mem", {"host": "a"}) == 100

    def test_histogram_observe(self):
        mc = MetricsCollector()
        mc.histogram("latency", "Latency", buckets=[0.1, 0.5, 1.0])
        mc.observe("latency", 0.3)
        mc.observe("latency", 0.8)
        mc.observe("latency", 1.5)
        assert mc.get_histogram("latency")["count"] == 3

    def test_histogram_observe_with_labels(self):
        mc = MetricsCollector()
        mc.histogram("lat", "Latency", labels={"path": ""}, buckets=[0.1, 1.0])
        mc.observe("lat", 0.5, labels={"path": "/api"})
        mc.observe("lat", 0.8, labels={"path": "/api"})
        assert mc.get_histogram("lat", {"path": "/api"})["count"] == 2

    def test_render_empty(self):
        mc = MetricsCollector()
        output = mc.render()
        assert "process_uptime_seconds" in output

    def test_render_with_metrics(self):
        mc = MetricsCollector()
        mc.counter("req", "Requests")
        mc.inc("req")
        output = mc.render()
        assert "# HELP req" in output
        assert "# TYPE req counter" in output

    def test_get_counter_unknown(self):
        mc = MetricsCollector()
        assert mc.get_counter("unknown") == 0

    def test_get_gauge_unknown(self):
        mc = MetricsCollector()
        assert mc.get_gauge("unknown") == 0

    def test_get_histogram_unknown(self):
        mc = MetricsCollector()
        h = mc.get_histogram("unknown")
        assert h["count"] == 0
        assert h["sum"] == 0

    def test_info_register_and_render(self):
        mc = MetricsCollector()
        mc.info("app_info", {"version": "1.0.0"}, "Application info")
        output = mc.render()
        assert "app_info" in output

    def test_set_info_no_labels(self):
        mc = MetricsCollector()
        mc.info("app_info", {"version": "1.0.0"}, "Application info")
        output = mc.render()
        assert "app_info" in output


class TestGetMetrics:
    def test_singleton(self):
        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2

    def test_type(self):
        m = get_metrics()
        assert isinstance(m, MetricsCollector)
