"""
Celery worker for background task processing.
Currently unused — all segmentation runs synchronously in the API process.
Add @celery_app.task decorators and wire to docker-compose when async needed.
"""

from celery import Celery

from app.config import REDIS_URL

celery_app = Celery("glacierkz", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(task_track_started=True, task_serializer="json", accept_content=["json"])
celery_app.autodiscover_tasks(["app.services"])
