from celery import Celery
from celery.schedules import crontab

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
    worker_prefetch_multiplier=1,
    beat_schedule={
        "refresh-property-inventory-every-day-at-3am": {
            "task": "app.tasks.scraping_tasks.refresh_property_inventory",
            "schedule": crontab(hour=3, minute=0),
        },
    },
)

celery.autodiscover_tasks(["app.tasks"], force=True)
