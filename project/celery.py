import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

celery_app = Celery('project')
celery_app.config_from_object('django.conf:settings', namespace='CELERY')
celery_app.conf.task_routes = {
    'apps.parsers.tasks.amazon_model_*': {'queue': 'amazon_model_create_update_queue'},
    'apps.parsers.tasks.parse_alternative_*': {'queue': 'parse_alternative_queue'},
    'apps.parsers.tasks.amazon_sku_update': {'queue': 'amazon_sku_update_queue'},
    'apps.parsers.tasks.amazon_in_stock_update': {'queue': 'amazon_in_stock_update_queue'},
}

celery_app.conf.beat_schedule = {
    'amazon_model_update': {
        'task': 'apps.parsers.tasks.amazon_check_for_update_date',
        'options': {'queue': 'amazon_check_updated_date_queue'},
        'schedule': settings.AMAZON_MODEL_UPDATE_BEAT_INTERVAL,
    },

    'track_amazon_search_pages': {
        'task': 'apps.parsers.tasks.track_amazon_search_pages',
        'options': {'queue': 'track_amazon_search_pages_queue'},
        'schedule': settings.TRACK_AMAZON_SEARCH_PAGES_BEAT_INTERVAL,
    }
}

celery_app.autodiscover_tasks()