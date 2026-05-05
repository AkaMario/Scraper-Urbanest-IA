from celery import Celery

from app.config import settings


celery = Celery(
    "urbanest_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Bogota",
    enable_utc=False,
    imports=("app.tasks.scraping_tasks",),
    broker_connection_retry_on_startup=True,
)

celery.autodiscover_tasks(["app.tasks"], force=True)
