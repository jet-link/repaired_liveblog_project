"""Admin panel context processors."""
from django.contrib.auth import get_user_model
from django.core.cache import cache

User = get_user_model()

ADMIN_ONLINE_CACHE_KEY = "admin_online_count"
ADMIN_ONLINE_CACHE_TIMEOUT = 60  # seconds


def admin_online_count(request):
    """Add online_count to context for admin panel pages."""
    if not request.path.startswith('/admin/'):
        return {}
    count = cache.get(ADMIN_ONLINE_CACHE_KEY)
    if count is None:
        try:
            from login.middleware import is_user_online
            count = sum(
                1 for u in User.objects.filter(is_active=True).only('pk')
                if is_user_online(u)
            )
            cache.set(ADMIN_ONLINE_CACHE_KEY, count, timeout=ADMIN_ONLINE_CACHE_TIMEOUT)
        except Exception:
            count = 0
    return {'admin_online_count': count}
