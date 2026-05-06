"""Middleware to track user online status via cache."""
from django.core.cache import cache

ONLINE_CACHE_KEY = "user_online_{pk}"
ONLINE_TIMEOUT = 60  # 1 minute — после минуты без запросов считаем офлайн


def set_user_online(user):
    """Mark user as online (called on each request)."""
    if user and user.is_authenticated and user.is_active:
        cache.set(ONLINE_CACHE_KEY.format(pk=user.pk), "1", timeout=ONLINE_TIMEOUT)


def is_user_online(user):
    """Check if user is currently online."""
    if not user or not user.pk:
        return False
    return cache.get(ONLINE_CACHE_KEY.format(pk=user.pk)) is not None


def clear_user_online(user):
    """Clear online status (e.g. on logout)."""
    if user and user.pk:
        cache.delete(ONLINE_CACHE_KEY.format(pk=user.pk))


class UserOnlineMiddleware:
    """Update user's online status in cache on each request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            set_user_online(request.user)
        return self.get_response(request)
