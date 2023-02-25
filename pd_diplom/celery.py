import os
from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pd_diplom.settings")
app = Celery("pd_diplom")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()