"""
Core Django app initialization.
Loads Celery app for background task processing.
"""

from .celery import app as celery_app

__all__ = ('celery_app',)
