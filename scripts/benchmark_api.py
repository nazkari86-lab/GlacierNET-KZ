#!/usr/bin/env python3
"""Bounded, read-only latency benchmark for presentation-critical API routes."""

from __future__ import annotations

import argparse
import json
import math
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ENDPOINTS = {
    "/health": 250,
    "/api/dashboard/stats": 750,
    "/api/glaciers?limit=5": 750,
    "/api/operations/overview": 1000,
    "/api/risk-twin/readiness": 1000,
    "/api/ml/readiness": 2000,
}


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    ordered = sorted(values)
    index = max(0, math.ceil(quantile * len(ordered)) - 1)
    return ordered[index]


def summarize(samples: list[dict[str, Any]], p95_limit_ms: float) -> dict[str, Any]:
    successful = [sample for sample in samples if sample["status"] == 200]
    latencies = [float(sample["latency_ms"]) for sample in successful]
    p95 = percentile(latencies, 0.95) if latencies else None
    return {
        "requests": len(samples),
        "successful": len(successful),
        "errors": len(samples) - len(successful),
        "success_rate": round(len(successful) / len(samples), 4) if samples else 0,
        "median_ms": round(percentile(latencies, 0.5), 2) if latencies else None,
        "p95_ms": round(p95, 2) if p95 is not None else None,
        "max_ms": round(max(latencies), 2) if latencies else None,
        "p95_limit_ms": p95_limit_ms,
        "passed": bool(latencies) and len(successful) == len(samples) and p95 <= p95_limit_ms,
    }


def request_once(url: str, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310 - local benchmark URL
            response.read()
            status = response.status
            error = None
    except urllib.error.HTTPError as exc:
        status = exc.code
        error = str(exc)
    except (OSError, TimeoutError) as exc:
        status = 0
        error = str(exc)
    return {
        "status": status,
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "error": error,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    # Six endpoints × (8 measured + 1 warm-up) = 54 requests, deliberately
    # below the API's 60-token burst policy.
    parser.add_argument("--requests", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "performance_benchmark.json")
    args = parser.parse_args()
    if not 1 <= args.requests <= 200 or not 1 <= args.concurrency <= 20:
        parser.error("requests must be 1..200 and concurrency 1..20")

    endpoint_results: dict[str, Any] = {}
    for endpoint, limit in ENDPOINTS.items():
        url = f"{args.base_url.rstrip('/')}{endpoint}"
        request_once(url, args.timeout)
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            samples = list(executor.map(lambda _: request_once(url, args.timeout), range(args.requests)))
        endpoint_results[endpoint] = summarize(samples, limit)

    passed = all(result["passed"] for result in endpoint_results.values())
    report = {
        "schema": "glaciernet-kz.api-performance.v1",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "base_url": args.base_url,
        "method": {
            "read_only": True,
            "requests_per_endpoint": args.requests,
            "concurrency": args.concurrency,
            "warmup_requests_per_endpoint": 1,
        },
        "status": "passed" if passed else "failed",
        "endpoints": endpoint_results,
        "limitations": [
            "Localhost latency is a regression baseline, not internet or multi-user capacity evidence.",
            "This bounded check does not exercise write-heavy training or inference routes.",
        ],
    }
    rendered = json.dumps(report, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
