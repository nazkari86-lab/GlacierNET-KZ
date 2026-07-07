"""
Маршруты уведомлений API.

Предоставляет эндпоинты для управления уведомлениями:
- Настройка уведомлений
- Отправка уведомлений
- История уведомлений
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationConfig(BaseModel):
    """Настройки уведомления."""

    enabled: bool = Field(True, description="Включить уведомления")
    email: Optional[str] = Field(None, description="Email для уведомлений")
    webhook_url: Optional[str] = Field(None, description="Webhook URL")
    notify_on_complete: bool = Field(True, description="Уведомлять о завершении")
    notify_on_error: bool = Field(True, description="Уведомлять об ошибках")
    notify_on_milestone: bool = Field(True, description="Уведомлять о вехах")


class Notification(BaseModel):
    """Уведомление."""

    notification_id: str
    type: str
    title: str
    message: str
    severity: str = "info"
    read: bool = False
    created_at: str = ""
    metadata: Dict[str, Any] = {}


class SendNotificationRequest(BaseModel):
    """Запрос на отправку уведомления."""

    type: str = Field("info", description="Тип: info, warning, error, success")
    title: str = Field(..., description="Заголовок")
    message: str = Field(..., description="Сообщение")
    severity: str = Field("info", description="Важность: low, medium, high, critical")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Метаданные")


_notifications_store: List[Dict[str, Any]] = []
_config_store: Dict[str, Dict[str, Any]] = {}


@router.get("/config")
async def get_notification_config():
    """Получение настроек уведомлений."""
    default_config = {
        "enabled": True,
        "email": None,
        "webhook_url": None,
        "notify_on_complete": True,
        "notify_on_error": True,
        "notify_on_milestone": True,
    }
    return _config_store.get("default", default_config)


@router.post("/config")
async def update_notification_config(config: NotificationConfig):
    """Обновление настроек уведомлений."""
    _config_store["default"] = config.model_dump()
    return {"success": True, "config": _config_store["default"]}


@router.post("/send", response_model=Notification)
async def send_notification(request: SendNotificationRequest):
    """Отправка уведомления."""
    notification = Notification(
        notification_id=f"notif_{uuid.uuid4().hex[:12]}",
        type=request.type,
        title=request.title,
        message=request.message,
        severity=request.severity,
        read=False,
        created_at=datetime.now(timezone.utc).isoformat(),
        metadata=request.metadata or {},
    )

    _notifications_store.append(notification.model_dump())
    logger.info(f"Уведомление отправлено: {notification.title}")

    return notification


@router.get("/list")
async def list_notifications(
    type: Optional[str] = Query(None, description="Фильтр по типу"),
    unread_only: bool = Query(False, description="Только непрочитанные"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Список уведомлений."""
    notifications = list(_notifications_store)

    if type:
        notifications = [n for n in notifications if n["type"] == type]

    if unread_only:
        notifications = [n for n in notifications if not n["read"]]

    notifications.sort(key=lambda x: x["created_at"], reverse=True)
    paginated = notifications[offset : offset + limit]

    return {
        "notifications": paginated,
        "total": len(notifications),
        "unread_count": sum(1 for n in _notifications_store if not n["read"]),
    }


@router.get("/{notification_id}")
async def get_notification(notification_id: str):
    """Получение уведомления по ID."""
    for n in _notifications_store:
        if n["notification_id"] == notification_id:
            return n

    raise HTTPException(status_code=404, detail=f"Уведомление {notification_id} не найдено")


@router.put("/{notification_id}/read")
async def mark_as_read(notification_id: str):
    """Отметить уведомление как прочитанное."""
    for n in _notifications_store:
        if n["notification_id"] == notification_id:
            n["read"] = True
            return {"success": True, "notification_id": notification_id}

    raise HTTPException(status_code=404, detail=f"Уведомление {notification_id} не найдено")


@router.put("/read-all")
async def mark_all_as_read():
    """Отметить все уведомления как прочитанные."""
    count = 0
    for n in _notifications_store:
        if not n["read"]:
            n["read"] = True
            count += 1

    return {"success": True, "marked_count": count}


@router.delete("/{notification_id}")
async def delete_notification(notification_id: str):
    """Удаление уведомления."""
    global _notifications_store
    original_count = len(_notifications_store)
    _notifications_store = [n for n in _notifications_store if n["notification_id"] != notification_id]

    if len(_notifications_store) == original_count:
        raise HTTPException(status_code=404, detail=f"Уведомление {notification_id} не найдено")

    return {"success": True, "message": f"Уведомление {notification_id} удалено"}


@router.delete("/clear")
async def clear_all_notifications():
    """Очистка всех уведомлений."""
    count = len(_notifications_store)
    _notifications_store.clear()
    return {"success": True, "cleared_count": count}


@router.get("/stats/summary")
async def get_notification_stats():
    """Статистика уведомлений."""
    total = len(_notifications_store)
    unread = sum(1 for n in _notifications_store if not n["read"])
    by_type = {}
    by_severity = {}

    for n in _notifications_store:
        by_type[n["type"]] = by_type.get(n["type"], 0) + 1
        by_severity[n["severity"]] = by_severity.get(n["severity"], 0) + 1

    return {
        "total": total,
        "unread": unread,
        "read": total - unread,
        "by_type": by_type,
        "by_severity": by_severity,
    }


@router.post("/training/{training_id}/notify")
async def notify_training_complete(
    training_id: str,
    success: bool = Query(True),
    metrics: Optional[str] = Query(None, description="JSON метрик"),
):
    """Уведомление о завершении обучения."""
    import json

    metrics_dict = {}
    if metrics:
        try:
            metrics_dict = json.loads(metrics)
        except json.JSONDecodeError:
            pass

    severity = "success" if success else "error"
    title = "Обучение завершено" if success else "Обучение завершено с ошибкой"
    message = f"Тренировка {training_id} {'успешно завершена' if success else 'завершилась с ошибкой'}"

    notification = Notification(
        notification_id=f"notif_{uuid.uuid4().hex[:12]}",
        type="training",
        title=title,
        message=message,
        severity=severity,
        read=False,
        created_at=datetime.now(timezone.utc).isoformat(),
        metadata={"training_id": training_id, "success": success, "metrics": metrics_dict},
    )

    _notifications_store.append(notification.model_dump())
    return notification
