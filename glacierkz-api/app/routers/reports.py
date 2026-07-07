"""
Маршруты отчётов API.

Предоставляет эндпоинты для генерации и управления отчётами:
- Отчёты по обучению
- Отчёты по инференсу
- Сводные отчёты
- Экспорт отчётов
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])


class ReportRequest(BaseModel):
    """Запрос на создание отчёта."""

    report_type: str = Field(..., description="Тип отчёта: training, inference, summary")
    project_id: Optional[str] = Field(None, description="ID проекта")
    date_from: Optional[str] = Field(None, description="Дата начала (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="Дата окончания (YYYY-MM-DD)")
    include_charts: bool = Field(True, description="Включить графики")
    format: str = Field("json", description="Формат: json, pdf, html")


class ReportResponse(BaseModel):
    """Ответ с отчётом."""

    report_id: str
    report_type: str
    created_at: str
    status: str = "completed"
    data: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None


class TrainingReport(BaseModel):
    """Отчёт по обучению."""

    model_name: str
    total_epochs: int
    final_loss: float
    best_loss: float
    training_time: float
    dataset_size: int
    metrics: Dict[str, float] = {}


class InferenceReport(BaseModel):
    """Отчёт по инференсу."""

    total_predictions: int
    avg_inference_time: float
    accuracy: Optional[float] = None
    IoU: Optional[float] = None
    predictions_summary: Dict[str, int] = {}


_report_counter = 0
_reports_store: Dict[str, Dict[str, Any]] = {}


def _generate_report_id() -> str:
    """Генерация ID отчёта."""
    global _report_counter
    _report_counter += 1
    return f"report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{_report_counter:04d}"


@router.post("/create", response_model=ReportResponse)
async def create_report(request: ReportRequest):
    """Создание нового отчёта."""
    report_id = _generate_report_id()

    report_data = {
        "report_id": report_id,
        "report_type": request.report_type,
        "project_id": request.project_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "date_range": {
            "from": request.date_from,
            "to": request.date_to,
        },
        "data": _generate_report_data(request.report_type, request.project_id),
    }

    _reports_store[report_id] = report_data

    return ReportResponse(
        report_id=report_id,
        report_type=request.report_type,
        created_at=report_data["created_at"],
        status="completed",
        data=report_data["data"],
    )


@router.get("/list")
async def list_reports(
    report_type: Optional[str] = Query(None, description="Фильтр по типу"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Получение списка отчётов."""
    reports = list(_reports_store.values())

    if report_type:
        reports = [r for r in reports if r["report_type"] == report_type]

    reports.sort(key=lambda x: x["created_at"], reverse=True)
    paginated = reports[offset : offset + limit]

    return {
        "reports": [
            {
                "report_id": r["report_id"],
                "report_type": r["report_type"],
                "created_at": r["created_at"],
                "status": r["status"],
            }
            for r in paginated
        ],
        "total": len(reports),
        "limit": limit,
        "offset": offset,
    }


@router.get("/training/latest")
async def get_latest_training_report():
    """Получение последнего отчёта по обучению."""
    training_reports = [r for r in _reports_store.values() if r["report_type"] == "training"]

    if not training_reports:
        return {"status": "no_data", "message": "Нет отчётов по обучению"}

    latest = max(training_reports, key=lambda x: x["created_at"])
    return latest


@router.get("/inference/latest")
async def get_latest_inference_report():
    """Получение последнего отчёта по инференсу."""
    inference_reports = [r for r in _reports_store.values() if r["report_type"] == "inference"]

    if not inference_reports:
        return {"status": "no_data", "message": "Нет отчётов по инференсу"}

    latest = max(inference_reports, key=lambda x: x["created_at"])
    return latest


@router.get("/summary/daily")
async def get_daily_summary(date: Optional[str] = Query(None)):
    """Дневная сводка."""
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return {
        "date": date,
        "training_runs": 0,
        "inference_predictions": 0,
        "total_reports": len(_reports_store),
        "system_uptime": 0,
        "status": "healthy",
    }


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str):
    """Получение отчёта по ID."""
    if report_id not in _reports_store:
        raise HTTPException(status_code=404, detail=f"Отчёт {report_id} не найден")

    r = _reports_store[report_id]
    return ReportResponse(
        report_id=r["report_id"],
        report_type=r["report_type"],
        created_at=r["created_at"],
        status=r["status"],
        data=r.get("data"),
    )


@router.delete("/{report_id}")
async def delete_report(report_id: str):
    """Удаление отчёта."""
    if report_id not in _reports_store:
        raise HTTPException(status_code=404, detail=f"Отчёт {report_id} не найден")

    del _reports_store[report_id]
    return {"success": True, "message": f"Отчёт {report_id} удалён"}


@router.post("/export/{report_id}")
async def export_report(
    report_id: str,
    format: str = Query("json", description="Формат экспорта: json, csv"),
):
    """Экспорт отчёта."""
    if report_id not in _reports_store:
        raise HTTPException(status_code=404, detail=f"Отчёт {report_id} не найден")

    report = _reports_store[report_id]

    if format == "json":
        export_path = f"exports/{report_id}.json"
        os.makedirs("exports", exist_ok=True)
        with open(export_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        return {"file_path": export_path, "format": format}

    elif format == "csv":
        return {"message": "CSV экспорт в разработке", "format": format}

    else:
        raise HTTPException(status_code=400, detail=f"Неподдерживаемый формат: {format}")


def _generate_report_data(report_type: str, project_id: Optional[str]) -> Dict[str, Any]:
    """Генерация данных отчёта."""
    if report_type == "training":
        return {
            "model_name": "glacier_unet",
            "total_epochs": 0,
            "final_loss": 0.0,
            "best_loss": float("inf"),
            "training_time": 0.0,
            "dataset_size": 0,
            "metrics": {"IoU": 0.0, "dice": 0.0, "accuracy": 0.0},
        }
    elif report_type == "inference":
        return {
            "total_predictions": 0,
            "avg_inference_time": 0.0,
            "accuracy": None,
            "IoU": None,
            "predictions_summary": {},
        }
    elif report_type == "summary":
        return {
            "total_models": 0,
            "total_datasets": 0,
            "total_predictions": 0,
            "storage_used_mb": 0,
        }
    return {}
