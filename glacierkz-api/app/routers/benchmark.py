"""CentralAsia-GlacierBench public evidence endpoints."""

from fastapi import APIRouter

from app.services.benchmark_service import benchmark_report

router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])


@router.get("")
def current_benchmark() -> dict:
    """Return separate model evaluations, reference evidence and explicit blockers."""
    return benchmark_report()


@router.get("/sources")
def benchmark_sources() -> dict:
    report = benchmark_report()
    return {
        "schema": report["schema"],
        "benchmark_name": report["benchmark_name"],
        "status": report["status"],
        "sources": report["sources"],
    }


@router.get("/tracks")
def benchmark_tracks() -> dict:
    report = benchmark_report()
    return {
        "schema": report["schema"],
        "benchmark_name": report["benchmark_name"],
        "status": report["status"],
        "tracks": report["tracks"],
    }
