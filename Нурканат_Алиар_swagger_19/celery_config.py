from celery import Celery
import os


celery_app = Celery(
    "worker",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    include=["tests.tasks"]  # Исправлено: указываем правильный путь к tasks
)


celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_serializer_kwargs={
        'ensure_ascii': False
    }
)

celery_app.conf.result_expires = 3600