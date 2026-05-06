try:
    from .celery import app as celery_app
except ImportError:  # celery optional until dependencies installed
    celery_app = None

__all__ = ("celery_app",)
