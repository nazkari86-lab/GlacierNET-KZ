"""
Сервис отчётов.

Предоставляет функции для:
- Генерации отчётов по обучению и инференсу
- Агрегации метрик
- Экспорта отчётов в различные форматы
- Управления шаблонами отчётов
"""

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReportType(str, Enum):
    """Типы отчётов."""

    TRAINING = "training"
    INFERENCE = "inference"
    SUMMARY = "summary"
    PERFORMANCE = "performance"
    SECURITY = "security"


@dataclass
class ReportSection:
    """Секция отчёта."""

    title: str
    content: str = ""
    data: Optional[Dict[str, Any]] = None
    charts: List[Dict[str, Any]] = field(default_factory=list)


class ReportService:
    """Сервис генерации отчётов."""

    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = reports_dir
        os.makedirs(reports_dir, exist_ok=True)
        self._reports: Dict[str, Dict[str, Any]] = {}
        self._templates: Dict[str, Dict[str, Any]] = self._init_templates()

    def _init_templates(self) -> Dict[str, Dict[str, Any]]:
        """Инициализация шаблонов отчётов."""
        return {
            "training": {
                "title": "Отчёт по обучению",
                "sections": ["model_info", "training_params", "metrics", "loss_history", "conclusions"],
            },
            "inference": {
                "title": "Отчёт по инференсу",
                "sections": ["model_info", "dataset_info", "predictions_summary", "accuracy_metrics"],
            },
            "summary": {
                "title": "Сводный отчёт",
                "sections": ["overview", "training_summary", "inference_summary", "recommendations"],
            },
            "performance": {
                "title": "Отчёт производительности",
                "sections": ["latency", "throughput", "resource_usage", "bottlenecks"],
            },
        }

    def create_training_report(
        self,
        model_name: str,
        training_config: Dict[str, Any],
        metrics: Dict[str, Any],
        loss_history: List[float],
        dataset_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Создание отчёта по обучению."""
        report_id = f"report_{uuid.uuid4().hex[:12]}"

        best_epoch = metrics.get("best_epoch", 0)
        final_loss = loss_history[-1] if loss_history else 0.0
        best_loss = min(loss_history) if loss_history else 0.0
        training_time = metrics.get("training_time", 0.0)

        sections = {
            "model_info": {
                "title": "Информация о модели",
                "data": {"model_name": model_name, "parameters": training_config.get("parameters", 0)},
            },
            "training_params": {
                "title": "Параметры обучения",
                "data": {
                    "epochs": training_config.get("epochs", 0),
                    "batch_size": training_config.get("batch_size", 0),
                    "learning_rate": training_config.get("learning_rate", 0.0),
                    "optimizer": training_config.get("optimizer", "adam"),
                },
            },
            "metrics": {
                "title": "Метрики",
                "data": {
                    "final_loss": final_loss,
                    "best_loss": best_loss,
                    "best_epoch": best_epoch,
                    "training_time_hours": training_time / 3600 if training_time else 0,
                },
            },
            "loss_history": {
                "title": "История лосса",
                "data": {
                    "total_epochs": len(loss_history),
                    "loss_values": loss_history,
                },
            },
            "conclusions": {
                "title": "Выводы",
                "data": {
                    "status": "completed" if loss_history else "no_data",
                    "convergence": "достигнута" if best_epoch > 0 else "не определена",
                },
            },
        }

        report = {
            "report_id": report_id,
            "report_type": "training",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model_name": model_name,
            "sections": sections,
            "summary": {
                "model_name": model_name,
                "total_epochs": len(loss_history),
                "final_loss": final_loss,
                "best_loss": best_loss,
                "training_time": training_time,
                "dataset_info": dataset_info or {},
            },
        }

        self._reports[report_id] = report
        logger.info(f"Отчёт по обучению создан: {report_id}")
        return report

    def create_inference_report(
        self,
        model_name: str,
        dataset_info: Dict[str, Any],
        predictions_summary: Dict[str, Any],
        performance_metrics: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Создание отчёта по инференсу."""
        report_id = f"report_{uuid.uuid4().hex[:12]}"

        total_predictions = predictions_summary.get("total", 0)
        class_distribution = predictions_summary.get("class_distribution", {})

        sections = {
            "model_info": {
                "title": "Информация о модели",
                "data": {"model_name": model_name},
            },
            "dataset_info": {
                "title": "Информация о датасете",
                "data": dataset_info,
            },
            "predictions_summary": {
                "title": "Сводка предсказаний",
                "data": {
                    "total_predictions": total_predictions,
                    "class_distribution": class_distribution,
                },
            },
            "accuracy_metrics": {
                "title": "Метрики точности",
                "data": performance_metrics or {},
            },
        }

        report = {
            "report_id": report_id,
            "report_type": "inference",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model_name": model_name,
            "sections": sections,
            "summary": {
                "total_predictions": total_predictions,
                "num_classes": len(class_distribution),
                "performance_metrics": performance_metrics or {},
            },
        }

        self._reports[report_id] = report
        logger.info(f"Отчёт по инференсу создан: {report_id}")
        return report

    def create_summary_report(
        self,
        training_reports: Optional[List[Dict[str, Any]]] = None,
        inference_reports: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Создание сводного отчёта."""
        report_id = f"report_{uuid.uuid4().hex[:12]}"

        training_reports = training_reports or []
        inference_reports = inference_reports or []

        total_training_runs = len(training_reports)
        total_predictions = sum(r.get("summary", {}).get("total_predictions", 0) for r in inference_reports)
        avg_loss = 0.0
        if training_reports:
            losses = [r.get("summary", {}).get("final_loss", 0) for r in training_reports]
            avg_loss = sum(losses) / len(losses) if losses else 0.0

        sections = {
            "overview": {
                "title": "Обзор",
                "data": {
                    "total_training_runs": total_training_runs,
                    "total_inference_reports": len(inference_reports),
                    "total_predictions": total_predictions,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
            },
            "training_summary": {
                "title": "Сводка по обучению",
                "data": {
                    "total_runs": total_training_runs,
                    "average_loss": avg_loss,
                },
            },
            "inference_summary": {
                "title": "Сводка по инференсу",
                "data": {
                    "total_reports": len(inference_reports),
                    "total_predictions": total_predictions,
                },
            },
            "recommendations": {
                "title": "Рекомендации",
                "data": self._generate_recommendations(total_training_runs, avg_loss, total_predictions),
            },
        }

        report = {
            "report_id": report_id,
            "report_type": "summary",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sections": sections,
            "summary": {
                "total_training_runs": total_training_runs,
                "total_predictions": total_predictions,
                "average_loss": avg_loss,
            },
        }

        self._reports[report_id] = report
        logger.info(f"Сводный отчёт создан: {report_id}")
        return report

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Получение отчёта по ID."""
        return self._reports.get(report_id)

    def list_reports(
        self,
        report_type: Optional[ReportType] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Список отчётов."""
        reports = list(self._reports.values())

        if report_type:
            reports = [r for r in reports if r["report_type"] == report_type.value]

        reports.sort(key=lambda x: x["created_at"], reverse=True)
        return reports[:limit]

    def delete_report(self, report_id: str) -> bool:
        """Удаление отчёта."""
        if report_id in self._reports:
            del self._reports[report_id]
            return True
        return False

    def export_report_json(self, report_id: str) -> Optional[str]:
        """Экспорт отчёта в JSON."""
        report = self._reports.get(report_id)
        if not report:
            return None

        filepath = os.path.join(self.reports_dir, f"{report_id}.json")
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2, default=str)

        return filepath

    def export_report_markdown(self, report_id: str) -> Optional[str]:
        """Экспорт отчёта в Markdown."""
        report = self._reports.get(report_id)
        if not report:
            return None

        md_lines = [
            f"# {report.get('report_type', '').title()} Report",
            "",
            f"**ID:** {report['report_id']}",
            f"**Created:** {report['created_at']}",
            "",
        ]

        for section_id, section in report.get("sections", {}).items():
            md_lines.append(f"## {section.get('title', section_id)}")
            md_lines.append("")

            data = section.get("data", {})
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, (list, dict)):
                        md_lines.append(f"- **{key}:** {json.dumps(value, default=str)}")
                    else:
                        md_lines.append(f"- **{key}:** {value}")
            elif isinstance(data, str):
                md_lines.append(data)

            md_lines.append("")

        filepath = os.path.join(self.reports_dir, f"{report_id}.md")
        with open(filepath, "w") as f:
            f.write("\n".join(md_lines))

        return filepath

    def get_report_stats(self) -> Dict[str, Any]:
        """Статистика отчётов."""
        total = len(self._reports)
        by_type: Dict[str, int] = {}
        for r in self._reports.values():
            rt = r.get("report_type", "unknown")
            by_type[rt] = by_type.get(rt, 0) + 1

        return {
            "total_reports": total,
            "by_type": by_type,
        }

    @staticmethod
    def _generate_recommendations(
        training_runs: int,
        avg_loss: float,
        total_predictions: int,
    ) -> Dict[str, Any]:
        """Генерация рекомендаций на основе отчёта."""
        recommendations = []

        if training_runs == 0:
            recommendations.append("Начните обучение модели для получения результатов")
        elif training_runs < 5:
            recommendations.append("Рекомендуется провести больше экспериментов")

        if avg_loss > 0.5:
            recommendations.append("Высокий лосс — рассмотрите увеличение эпох или изменение lr")

        if total_predictions == 0:
            recommendations.append("Запустите инференс для оценки качества модели")

        if not recommendations:
            recommendations.append("Система работает в штатном режиме")

        return {
            "count": len(recommendations),
            "items": recommendations,
        }


report_service = ReportService()
