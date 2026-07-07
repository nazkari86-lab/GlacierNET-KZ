import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import CORS_ORIGINS, RESULTS_DIR, UPLOAD_DIR
from app.middleware.admin_auth import AdminAuthMiddleware
from app.middleware.cache import CacheConfig, CacheMiddleware
from app.middleware.rate_limit import RateLimitConfig, RateLimitMiddleware
from app.middleware.request_logging import RequestLoggingConfig, RequestLoggingMiddleware
from app.middleware.security_headers import SecurityHeadersConfig, SecurityHeadersMiddleware
from app.monitoring.health import HealthStatus, get_health_checker
from app.monitoring.metrics import get_metrics
from app.monitoring.system import get_system_info
from app.routers import (
    analysis,
    area,
    compare,
    dashboard,
    data,
    datasets,
    export,
    history,
    models,
    monitoring,
    pipeline,
    segmentation,
    tasks,
    training,
    trend,
    uncertainty,
)
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.mcp import router as mcp_router
from app.routers.notifications import router as notifications_router
from app.routers.reports import router as reports_router
from app.tasks import get_task_manager
from app.ws import get_ws_manager, ws_router

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    manager = get_ws_manager()
    task_mgr = get_task_manager()
    await manager.start()
    await task_mgr.start(num_workers=3)
    yield
    await manager.stop()
    await task_mgr.stop()


app = FastAPI(
    title="GlacierNET-KZ API",
    description=(
        "REST API for glacier segmentation, temporal trend analysis, and monitoring "
        "in Kazakhstan's Zailiysky Alatau. Supports U-Net, U-Net++, Random Forest, "
        "and NDSI baselines on Sentinel-2 / Landsat imagery."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "GlacierNET-KZ",
        "url": "https://github.com/nicklaua/GlacierNET-KZ",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    tags_metadata=[
        {"name": "segmentation", "description": "Glacier mask inference from satellite imagery"},
        {"name": "trend", "description": "Multi-year area trend and forecast to 2050"},
        {"name": "models", "description": "Registered ML model registry and metadata"},
        {"name": "datasets", "description": "Training data and patch management"},
        {"name": "training", "description": "Model training job control"},
        {"name": "analysis", "description": "LLM-powered glacier analysis"},
        {"name": "admin", "description": "Administrative endpoints (authenticated)"},
        {"name": "monitoring", "description": "Health checks, metrics, and system status"},
    ],
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware, config=SecurityHeadersConfig())
app.add_middleware(
    RequestLoggingMiddleware,
    config=RequestLoggingConfig(
        exclude_paths=["/health", "/metrics", "/ws"],
    ),
)
app.add_middleware(
    CacheMiddleware,
    config=CacheConfig(
        default_ttl=60,
        exempt_paths=["/health", "/metrics", "/ws", "/docs"],
    ),
)
app.add_middleware(
    RateLimitMiddleware,
    config=RateLimitConfig(
        requests_per_minute=120,
        requests_per_hour=5000,
    ),
)
app.add_middleware(AdminAuthMiddleware)

app.mount("/static/results", StaticFiles(directory=str(RESULTS_DIR)), name="results")
app.mount("/static/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

app.include_router(models.router)
app.include_router(segmentation.router)
app.include_router(compare.router)
app.include_router(area.router)
app.include_router(uncertainty.router)
app.include_router(trend.router)
app.include_router(history.router)
app.include_router(export.router)
app.include_router(analysis.router)
app.include_router(tasks.router)
app.include_router(training.router)
app.include_router(datasets.router)
app.include_router(monitoring.router)
app.include_router(dashboard.router)
app.include_router(data.router)
app.include_router(pipeline.router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(mcp_router)
app.include_router(reports_router)
app.include_router(notifications_router)
app.include_router(ws_router)


@app.get("/")
def root():
    index = STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(str(index))
    return {"name": "GlacierNET-KZ API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
def health():
    checker = get_health_checker()
    return {
        "status": "ok",
        "version": "1.0.0",
        "service": "GlacierNET-KZ API",
        "uptime_seconds": round(time.time() - checker._start_time, 2),
    }


@app.get("/health/deep")
async def health_deep():
    checker = get_health_checker()
    report = await checker.readiness()
    status_code = (
        200 if report.status == HealthStatus.HEALTHY else (503 if report.status == HealthStatus.UNHEALTHY else 200)
    )
    return JSONResponse(content=report.to_dict(), status_code=status_code)


@app.get("/health/liveness")
async def health_liveness():
    checker = get_health_checker()
    return await checker.liveness()


@app.get("/metrics")
def metrics():
    collector = get_metrics()
    return Response(content=collector.render(), media_type="text/plain")


@app.get("/info")
def info():
    return get_system_info()


@app.get("/status")
def status():
    metrics_collector = get_metrics()
    task_mgr = get_task_manager()
    ws_mgr = get_ws_manager()
    return {
        "status": "operational",
        "version": "1.0.0",
        "tasks": task_mgr.get_stats(),
        "websocket": ws_mgr.get_stats(),
        "metrics_summary": {
            "requests_total": metrics_collector.get_counter("http_requests_total", {"method": "GET"})
            + metrics_collector.get_counter("http_requests_total", {"method": "POST"})
            + metrics_collector.get_counter("http_requests_total", {"method": "PUT"})
            + metrics_collector.get_counter("http_requests_total", {"method": "DELETE"}),
        },
    }


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    collector = get_metrics()
    collector.inc("http_requests_total", labels={"method": request.method})
    collector.inc("http_active_requests")
    response = await call_next(request)
    collector.set("http_active_requests", max(0, collector.get_gauge("http_active_requests") - 1))
    return response
