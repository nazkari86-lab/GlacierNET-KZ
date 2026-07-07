"""
Сервис уведомлений.

Предоставляет функции для:
- Отправки уведомлений через разные каналы
- Управления шаблонами уведомлений
- Истории отправок
- Интеграции с внешними сервисами
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Типы уведомлений."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    TRAINING_COMPLETE = "training_complete"
    TRAINING_FAILED = "training_failed"
    INFERENCE_COMPLETE = "inference_complete"
    SYSTEM_ALERT = "system_alert"


class NotificationChannel(str, Enum):
    """Каналы доставки."""

    CONSOLE = "console"
    EMAIL = "email"
    WEBHOOK = "webhook"
    LOG = "log"


@dataclass
class NotificationMessage:
    """Сообщение уведомления."""

    notification_id: str
    type: NotificationType
    title: str
    message: str
    severity: str = "info"
    channel: NotificationChannel = NotificationChannel.CONSOLE
    metadata: Dict[str, Any] = field(default_factory=dict)
    read: bool = False
    sent: bool = False
    created_at: str = ""
    sent_at: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


class NotificationService:
    """Сервис управления уведомлениями."""

    def __init__(self):
        self._notifications: List[Dict[str, Any]] = []
        self._templates: Dict[str, str] = {
            "training_complete": "Тренировка {training_id} завершена. Лосс: {loss:.4f}",
            "training_failed": "Тренировка {training_id} завершилась с ошибкой: {error}",
            "inference_complete": "Инференс завершён. Обработано: {count} изображений",
            "system_alert": "Системное предупреждение: {message}",
            "export_complete": "Экспорт {export_id} завершён. Файл: {file_path}",
            "model_ready": "Модель {model_name} готова к использованию",
        }
        self._channels: Dict[NotificationChannel, Callable] = {
            NotificationChannel.CONSOLE: self._send_console,
            NotificationChannel.LOG: self._send_log,
        }
        self._webhook_urls: List[str] = []
        self._email_config: Optional[Dict[str, str]] = None

    def send(
        self,
        type: NotificationType,
        title: str,
        message: str,
        severity: str = "info",
        channel: NotificationChannel = NotificationChannel.CONSOLE,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NotificationMessage:
        """Отправка уведомления."""
        notification = NotificationMessage(
            notification_id=f"notif_{uuid.uuid4().hex[:12]}",
            type=type,
            title=title,
            message=message,
            severity=severity,
            channel=channel,
            metadata=metadata or {},
        )

        sender = self._channels.get(channel)
        if sender:
            try:
                sender(notification)
                notification.sent = True
                notification.sent_at = datetime.now(timezone.utc).isoformat()
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления: {e}")

        self._notifications.append(
            {
                "notification_id": notification.notification_id,
                "type": notification.type.value,
                "title": notification.title,
                "message": notification.message,
                "severity": notification.severity,
                "channel": notification.channel.value,
                "read": notification.read,
                "sent": notification.sent,
                "created_at": notification.created_at,
                "sent_at": notification.sent_at,
                "metadata": notification.metadata,
            }
        )

        return notification

    def send_from_template(
        self,
        template_key: str,
        channel: NotificationChannel = NotificationChannel.CONSOLE,
        **kwargs: Any,
    ) -> NotificationMessage:
        """Отправка уведомления по шаблону."""
        if template_key not in self._templates:
            raise ValueError(f"Шаблон '{template_key}' не найден")

        template = self._templates[template_key]
        try:
            message = template.format(**kwargs)
        except KeyError as e:
            message = f"Шаблон '{template_key}': отсутствует переменная {e}"

        type_map = {
            "training_complete": NotificationType.TRAINING_COMPLETE,
            "training_failed": NotificationType.TRAINING_FAILED,
            "inference_complete": NotificationType.INFERENCE_COMPLETE,
            "system_alert": NotificationType.SYSTEM_ALERT,
            "export_complete": NotificationType.INFO,
            "model_ready": NotificationType.SUCCESS,
        }

        notification_type = type_map.get(template_key, NotificationType.INFO)
        severity_map = {
            NotificationType.TRAINING_COMPLETE: "success",
            NotificationType.TRAINING_FAILED: "error",
            NotificationType.INFERENCE_COMPLETE: "success",
            NotificationType.SYSTEM_ALERT: "warning",
            NotificationType.INFO: "info",
            NotificationType.SUCCESS: "success",
        }

        return self.send(
            type=notification_type,
            title=template_key.replace("_", " ").title(),
            message=message,
            severity=severity_map.get(notification_type, "info"),
            channel=channel,
            metadata={"template_key": template_key, "template_vars": kwargs},
        )

    def send_training_complete(
        self,
        training_id: str,
        loss: float,
        epochs: int,
        metrics: Optional[Dict[str, float]] = None,
    ) -> NotificationMessage:
        """Уведомление о завершении тренировки."""
        return self.send_from_template(
            "training_complete",
            training_id=training_id,
            loss=loss,
        )

    def send_training_failed(self, training_id: str, error: str) -> NotificationMessage:
        """Уведомление об ошибке тренировки."""
        return self.send_from_template(
            "training_failed",
            training_id=training_id,
            error=error,
        )

    def send_inference_complete(self, count: int) -> NotificationMessage:
        """Уведомление о завершении инференса."""
        return self.send_from_template(
            "inference_complete",
            count=count,
        )

    def send_system_alert(self, message: str) -> NotificationMessage:
        """Системное предупреждение."""
        return self.send_from_template(
            "system_alert",
            message=message,
        )

    def add_webhook_url(self, url: str) -> None:
        """Добавление Webhook URL."""
        if url not in self._webhook_urls:
            self._webhook_urls.append(url)
            logger.info(f"Webhook добавлен: {url}")

    def remove_webhook_url(self, url: str) -> bool:
        """Удаление Webhook URL."""
        if url in self._webhook_urls:
            self._webhook_urls.remove(url)
            return True
        return False

    def add_template(self, key: str, template: str) -> None:
        """Добавление шаблона уведомления."""
        self._templates[key] = template

    def get_templates(self) -> Dict[str, str]:
        """Получение всех шаблонов."""
        return dict(self._templates)

    def get_notifications(
        self,
        type_filter: Optional[NotificationType] = None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Получение списка уведомлений."""
        notifications = list(self._notifications)

        if type_filter:
            notifications = [n for n in notifications if n["type"] == type_filter.value]

        if unread_only:
            notifications = [n for n in notifications if not n["read"]]

        notifications.sort(key=lambda x: x["created_at"], reverse=True)
        return notifications[:limit]

    def mark_as_read(self, notification_id: str) -> bool:
        """Отметить уведомление как прочитанное."""
        for n in self._notifications:
            if n["notification_id"] == notification_id:
                n["read"] = True
                return True
        return False

    def mark_all_as_read(self) -> int:
        """Отметить все уведомления как прочитанные."""
        count = 0
        for n in self._notifications:
            if not n["read"]:
                n["read"] = True
                count += 1
        return count

    def delete_notification(self, notification_id: str) -> bool:
        """Удаление уведомления."""
        original_count = len(self._notifications)
        self._notifications = [n for n in self._notifications if n["notification_id"] != notification_id]
        return len(self._notifications) < original_count

    def clear_all(self) -> int:
        """Очистка всех уведомлений."""
        count = len(self._notifications)
        self._notifications.clear()
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Статистика уведомлений."""
        total = len(self._notifications)
        unread = sum(1 for n in self._notifications if not n["read"])

        by_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        for n in self._notifications:
            by_type[n["type"]] = by_type.get(n["type"], 0) + 1
            by_severity[n["severity"]] = by_severity.get(n["severity"], 0) + 1

        return {
            "total": total,
            "unread": unread,
            "read": total - unread,
            "by_type": by_type,
            "by_severity": by_severity,
        }

    def _send_console(self, notification: NotificationMessage) -> None:
        """Отправка в консоль."""
        severity_icons = {
            "info": "[INFO]",
            "success": "[OK]",
            "warning": "[WARN]",
            "error": "[ERR]",
        }
        icon = severity_icons.get(notification.severity, "[?]")
        print(f"{icon} {notification.title}: {notification.message}")

    def _send_log(self, notification: NotificationMessage) -> None:
        """Отправка в лог."""
        log_methods = {
            "info": logger.info,
            "success": logger.info,
            "warning": logger.warning,
            "error": logger.error,
        }
        log_method = log_methods.get(notification.severity, logger.info)
        log_method(f"{notification.title}: {notification.message}")


notification_service = NotificationService()
