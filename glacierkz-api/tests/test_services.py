"""
Тесты для сервисов: admin_service, notification_service, report_service, export_service
"""

import os

import numpy as np


class TestNotificationService:
    """Тесты для класса NotificationService."""

    def test_import(self):
        from app.services.notification_service import NotificationService
        assert NotificationService is not None

    def test_initialization(self):
        from app.services.notification_service import NotificationService
        ns = NotificationService()
        assert ns is not None

    def test_send_console(self):
        from app.services.notification_service import NotificationChannel, NotificationService, NotificationType
        ns = NotificationService()
        result = ns.send(
            type=NotificationType.INFO,
            title="Test",
            message="Test notification",
            channel=NotificationChannel.CONSOLE,
        )
        assert result is not None
        assert result.sent is True

    def test_send_log(self):
        from app.services.notification_service import NotificationChannel, NotificationService, NotificationType
        ns = NotificationService()
        result = ns.send(
            type=NotificationType.INFO,
            title="Log Test",
            message="Log notification",
            channel=NotificationChannel.LOG,
        )
        assert result is not None
        assert result.sent is True

    def test_send_training_complete(self):
        from app.services.notification_service import NotificationService
        ns = NotificationService()
        result = ns.send_training_complete(training_id="t1", loss=0.5, epochs=10)
        assert result is not None

    def test_send_training_failed(self):
        from app.services.notification_service import NotificationService
        ns = NotificationService()
        result = ns.send_training_failed(training_id="t2", error="OOM")
        assert result is not None

    def test_send_inference_complete(self):
        from app.services.notification_service import NotificationService
        ns = NotificationService()
        result = ns.send_inference_complete(count=42)
        assert result is not None

    def test_send_system_alert(self):
        from app.services.notification_service import NotificationService
        ns = NotificationService()
        result = ns.send_system_alert(message="High memory usage")
        assert result is not None

    def test_get_notifications(self):
        from app.services.notification_service import NotificationService, NotificationType
        ns = NotificationService()
        ns.send(type=NotificationType.INFO, title="A", message="a")
        ns.send(type=NotificationType.WARNING, title="B", message="b")
        notifications = ns.get_notifications()
        assert len(notifications) == 2

    def test_get_notifications_type_filter(self):
        from app.services.notification_service import NotificationService, NotificationType
        ns = NotificationService()
        ns.send(type=NotificationType.INFO, title="A", message="a")
        ns.send(type=NotificationType.ERROR, title="B", message="b")
        filtered = ns.get_notifications(type_filter=NotificationType.INFO)
        assert len(filtered) == 1

    def test_mark_as_read(self):
        from app.services.notification_service import NotificationService, NotificationType
        ns = NotificationService()
        notif = ns.send(type=NotificationType.INFO, title="A", message="a")
        result = ns.mark_as_read(notif.notification_id)
        assert result is True

    def test_get_stats(self):
        from app.services.notification_service import NotificationService, NotificationType
        ns = NotificationService()
        ns.send(type=NotificationType.INFO, title="A", message="a")
        stats = ns.get_stats()
        assert "total" in stats
        assert "unread" in stats
        assert stats["total"] == 1


class TestAdminService:
    """Тесты для класса AdminService."""

    def test_import(self):
        from app.services.admin_service import AdminService
        assert AdminService is not None

    def test_initialization(self):
        from app.services.admin_service import AdminService
        admin = AdminService()
        assert admin is not None

    def test_get_system_status(self):
        from app.services.admin_service import AdminService
        admin = AdminService()
        status = admin.get_system_status()
        assert "status" in status
        assert "platform" in status
        assert "metrics" in status
        assert "cpu_percent" in status["metrics"]

    def test_get_system_metrics(self):
        from app.services.admin_service import AdminService, SystemMetrics
        admin = AdminService()
        metrics = admin.get_system_metrics()
        assert isinstance(metrics, SystemMetrics)
        assert metrics.cpu_percent >= 0

    def test_health_check(self):
        from app.services.admin_service import AdminService
        admin = AdminService()
        health = admin.health_check()
        assert "status" in health
        assert health["status"] in ["healthy", "degraded", "unhealthy"]

    def test_get_metrics_history(self):
        from app.services.admin_service import AdminService
        admin = AdminService()
        admin.get_system_metrics()
        history = admin.get_metrics_history()
        assert isinstance(history, list)

    def test_cleanup_old_files(self):
        from app.services.admin_service import AdminService
        admin = AdminService()
        result = admin.cleanup_old_files(max_age_days=7)
        assert isinstance(result, dict)

    def test_get_process_info(self):
        from app.services.admin_service import AdminService
        admin = AdminService()
        processes = admin.get_process_info()
        assert isinstance(processes, list)


class TestReportService:
    """Тесты для класса ReportService."""

    def test_import(self):
        from app.services.report_service import ReportService
        assert ReportService is not None

    def test_initialization(self, tmp_path):
        from app.services.report_service import ReportService
        rs = ReportService(reports_dir=str(tmp_path))
        assert rs is not None

    def test_create_training_report(self, tmp_path):
        from app.services.report_service import ReportService
        rs = ReportService(reports_dir=str(tmp_path))
        report = rs.create_training_report(
            model_name="test_model",
            training_config={"epochs": 10, "batch_size": 8, "learning_rate": 0.001},
            metrics={"best_epoch": 8, "training_time": 120.0},
            loss_history=[0.5, 0.4, 0.3, 0.35, 0.25],
        )
        assert report is not None
        assert "id" in report or "report_id" in report

    def test_create_inference_report(self, tmp_path):
        from app.services.report_service import ReportService
        rs = ReportService(reports_dir=str(tmp_path))
        report = rs.create_inference_report(
            model_name="test_model",
            dataset_info={"num_images": 100},
            predictions_summary={"mean_accuracy": 0.92},
        )
        assert report is not None

    def test_get_report(self, tmp_path):
        from app.services.report_service import ReportService
        rs = ReportService(reports_dir=str(tmp_path))
        report = rs.create_training_report(
            model_name="test",
            training_config={"epochs": 5},
            metrics={},
            loss_history=[0.5, 0.3],
        )
        report_id = report.get("id") or report.get("report_id")
        fetched = rs.get_report(report_id)
        assert fetched is not None

    def test_export_report_json(self, tmp_path):
        from app.services.report_service import ReportService
        rs = ReportService(reports_dir=str(tmp_path))
        report = rs.create_training_report(
            model_name="test",
            training_config={"epochs": 5},
            metrics={},
            loss_history=[0.5, 0.3],
        )
        report_id = report.get("id") or report.get("report_id")
        filepath = rs.export_report_json(report_id)
        assert filepath is not None
        assert os.path.exists(filepath)


class TestExportServiceExtended:
    """Тесты для ExportService."""

    def test_import(self):
        from app.services.export_service import ExportService
        assert ExportService is not None

    def test_initialization(self, tmp_path):
        from app.services.export_service import ExportService
        es = ExportService(exports_dir=str(tmp_path))
        assert es is not None

    def test_export_masks_numpy(self, tmp_path):
        from app.services.export_service import ExportService
        es = ExportService(exports_dir=str(tmp_path))
        masks = np.random.randint(0, 5, (4, 64, 64), dtype=np.uint8)
        result = es.export_masks_numpy(masks, project_id="p1")
        assert "export_id" in result
        assert result["format"] == "numpy"

    def test_export_masks_png(self, tmp_path):
        from app.services.export_service import ExportService
        es = ExportService(exports_dir=str(tmp_path))
        masks = np.random.randint(0, 2, (2, 32, 32), dtype=np.uint8)
        result = es.export_masks_png(masks, project_id="p1")
        assert "export_id" in result
        assert result["format"] == "png"

    def test_export_predictions_json(self, tmp_path):
        from app.services.export_service import ExportService
        es = ExportService(exports_dir=str(tmp_path))
        predictions = {"accuracy": 0.95, "loss": 0.05}
        result = es.export_predictions_json(predictions, project_id="p1")
        assert "export_id" in result

    def test_list_exports(self, tmp_path):
        from app.services.export_service import ExportService
        es = ExportService(exports_dir=str(tmp_path))
        masks = np.random.randint(0, 2, (2, 32, 32), dtype=np.uint8)
        es.export_masks_numpy(masks)
        exports = es.list_exports()
        assert len(exports) >= 1

    def test_get_export_stats(self, tmp_path):
        from app.services.export_service import ExportService
        es = ExportService(exports_dir=str(tmp_path))
        masks = np.random.randint(0, 2, (2, 32, 32), dtype=np.uint8)
        es.export_masks_numpy(masks)
        stats = es.get_export_stats()
        assert "total_exports" in stats
        assert stats["total_exports"] >= 1
