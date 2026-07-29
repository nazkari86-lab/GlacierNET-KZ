import pytest

from scripts.benchmark_api import percentile, summarize


def test_percentile_uses_nearest_rank():
    assert percentile([40, 10, 20, 30], 0.5) == 20
    assert percentile([40, 10, 20, 30], 0.95) == 40


def test_percentile_rejects_empty_input():
    with pytest.raises(ValueError):
        percentile([], 0.95)


def test_summary_fails_on_any_http_error():
    result = summarize(
        [
            {"status": 200, "latency_ms": 10},
            {"status": 503, "latency_ms": 20},
        ],
        100,
    )

    assert result["success_rate"] == 0.5
    assert result["passed"] is False
