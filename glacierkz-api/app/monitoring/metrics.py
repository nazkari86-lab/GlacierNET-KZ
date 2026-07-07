"""Prometheus-compatible metrics collector — counters, histograms, gauges."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class _Metric:
    name: str
    metric_type: str
    help_text: str
    labels: dict[str, str] = field(default_factory=dict)
    value: float = 0.0
    _buckets: dict[float, float] = field(default_factory=dict)
    _count: int = 0
    _sum: float = 0.0


class MetricsCollector:
    """Simple Prometheus-compatible metrics collector."""

    def __init__(self):
        self._metrics: dict[str, _Metric] = {}
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = defaultdict(float)
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._info: dict[str, dict] = {}
        self._start_time = time.time()

    def counter(
        self,
        name: str,
        help_text: str = "",
        labels: dict[str, str] | None = None,
    ) -> None:
        key = self._key(name, labels)
        self._metrics[key] = _Metric(name=name, metric_type="counter", help_text=help_text, labels=labels or {})

    def gauge(
        self,
        name: str,
        help_text: str = "",
        labels: dict[str, str] | None = None,
    ) -> None:
        key = self._key(name, labels)
        self._metrics[key] = _Metric(name=name, metric_type="gauge", help_text=help_text, labels=labels or {})

    def histogram(
        self,
        name: str,
        help_text: str = "",
        labels: dict[str, str] | None = None,
        buckets: list[float] | None = None,
    ) -> None:
        key = self._key(name, labels)
        m = _Metric(name=name, metric_type="histogram", help_text=help_text, labels=labels or {})
        if buckets:
            m._buckets = {b: 0.0 for b in sorted(buckets)}
        self._metrics[key] = m

    def info(self, name: str, data: dict, help_text: str = "") -> None:
        self._info[name] = {"data": data, "help": help_text}

    def inc(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        key = self._key(name, labels)
        self._counters[key] += value

    def set(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        key = self._key(name, labels)
        self._gauges[key] = value

    def observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        key = self._key(name, labels)
        self._histograms[key].append(value)

    def time(self, name: str, labels: dict[str, str] | None = None):
        return _TimerContext(self, name, labels)

    def render(self) -> str:
        lines = []
        for key, metric in self._metrics.items():
            lines.append(f"# HELP {metric.name} {metric.help_text}")
            lines.append(f"# TYPE {metric.name} {metric.metric_type}")
            label_str = self._format_labels(metric.labels)
            if metric.metric_type == "counter":
                val = self._counters.get(key, 0.0)
                lines.append(f"{metric.name}{label_str} {val}")
            elif metric.metric_type == "gauge":
                val = self._gauges.get(key, metric.value)
                lines.append(f"{metric.name}{label_str} {val}")
            elif metric.metric_type == "histogram":
                values = self._histograms.get(key, [])
                if values:
                    lines.append(f"{metric.name}_sum{label_str} {sum(values)}")
                    lines.append(f"{metric.name}_count{label_str} {len(values)}")
                    sorted_vals = sorted(values)
                    for bucket, count in metric._buckets.items():
                        c = sum(1 for v in sorted_vals if v <= bucket)
                        b_label = {**metric.labels, "le": str(bucket)}
                        b_str = self._format_labels(b_label)
                        lines.append(f"{metric.name}_bucket{b_str} {c}")
                    lines.append(f'{metric.name}{{...,"+Inf"}} {len(values)}')

        for name, info in self._info.items():
            lines.append(f"# HELP {name}_info {info['help']}")
            lines.append(f"# TYPE {name}_info gauge")
            for k, v in info["data"].items():
                lines.append(f'{name}_info{{{k}="{v}"}} 1')

        lines.append("# HELP process_uptime_seconds Process uptime in seconds")
        lines.append("# TYPE process_uptime_seconds gauge")
        lines.append(f"process_uptime_seconds {time.time() - self._start_time:.2f}")
        return "\n".join(lines) + "\n"

    def get_counter(self, name: str, labels: dict[str, str] | None = None) -> float:
        return self._counters.get(self._key(name, labels), 0.0)

    def get_gauge(self, name: str, labels: dict[str, str] | None = None) -> float:
        return self._gauges.get(self._key(name, labels), 0.0)

    def get_histogram(self, name: str, labels: dict[str, str] | None = None) -> dict:
        values = self._histograms.get(self._key(name, labels), [])
        if not values:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0}
        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }

    def reset(self) -> None:
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._info.clear()
        self._metrics.clear()

    def _key(self, name: str, labels: dict[str, str] | None) -> str:
        if labels:
            sorted_labels = sorted(labels.items())
            label_str = ",".join(f"{k}={v}" for k, v in sorted_labels)
            return f"{name}{{{label_str}}}"
        return name

    @staticmethod
    def _format_labels(labels: dict[str, str]) -> str:
        if not labels:
            return ""
        parts = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        return "{" + ",".join(parts) + "}"


class _TimerContext:
    def __init__(self, collector: MetricsCollector, name: str, labels: dict[str, str] | None):
        self.collector = collector
        self.name = name
        self.labels = labels
        self.start: float = 0

    def __enter__(self):
        self.start = time.monotonic()
        return self

    def __exit__(self, *args):
        elapsed = time.monotonic() - self.start
        self.collector.observe(self.name, elapsed, self.labels)


_metrics: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
        _metrics.counter("http_requests_total", "Total HTTP requests", {"method": "GET"})
        _metrics.counter("http_requests_total", "Total HTTP requests", {"method": "POST"})
        _metrics.counter("http_requests_total", "Total HTTP requests", {"method": "PUT"})
        _metrics.counter("http_requests_total", "Total HTTP requests", {"method": "DELETE"})
        _metrics.histogram(
            "http_request_duration_seconds",
            "Request duration",
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )
        _metrics.gauge("http_active_requests", "Currently active requests")
        _metrics.counter("segmentation_requests_total", "Segmentation requests")
        _metrics.counter("segmentation_errors_total", "Segmentation errors")
        _metrics.histogram("segmentation_duration_seconds", "Segmentation duration")
        _metrics.gauge("model_loaded", "Model loaded status")
        _metrics.counter("upload_total", "File uploads")
        _metrics.counter("export_total", "Exports")
        _metrics.gauge("ws_connections", "WebSocket connections")
        _metrics.gauge("task_queue_size", "Task queue size")
        _metrics.gauge("cache_entries", "Cache entries")
        _metrics.info("app", {"version": "1.0.0", "name": "glacierkz-api"})
    return _metrics
