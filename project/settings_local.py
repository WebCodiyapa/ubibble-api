# -*- coding: utf-8 -*-

import os

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
    # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle', 'django.contrib.gis.db.backends.postgis'
        'NAME': 'plof',  # Or path to database file if using sqlite3.
        'USER': 'plof',  # Not used with sqlite3.
        'PASSWORD': 'plof',  # Not used with sqlite3.
        'HOST': 'localhost',  # Set to empty string for localhost. Not used with sqlite3.
        'PORT': 5432,  # Set to empty string for default. Not used with sqlite3.
        # 'OPTIONS': {
        #    'use_unicode': True,
        #    'charset': 'utf8',
        #    'init_command': "SET storage_engine = InnoDB, NAMES 'utf8' COLLATE 'utf8_unicode_ci', SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED",
        # }
    }
}

# SERVER_EMAIL = ''
# DEFAULT_FROM_EMAIL = ''
# EMAIL_HOST = ''
# EMAIL_PORT = 587
# EMAIL_HOST_USER = ''
# EMAIL_HOST_PASSWORD = ''
# EMAIL_USE_TLS = True


TIME_ZONE = 'Europe/Moscow'

LANGUAGE_CODE = 'en-US'

SITE_ID = 1

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['*']

USE_I18N = True
USE_L10N = True

SECRET_KEY = 'jblf0vrn*0#c28os-fpb)3t#6l&k2^0t0-o0wn4s#ls8x-enja'

THUMBNAIL_DEBUG = DEBUG

CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'
CELERY_BEAT_SCHEDULE = {
    'amazon_model_update': {
        'task': 'apps.parsers.tasks.amazon_check_for_update_date',
        'options': {'queue': 'amazon_check_updated_date_queue'},
        'schedule': 10,
    },

    'track_amazon_search_pages': {
        'task': 'apps.parsers.tasks.track_amazon_search_pages',
        'options': {'queue': 'track_amazon_search_pages_queue'},
        'schedule': 1000,
    }
}
