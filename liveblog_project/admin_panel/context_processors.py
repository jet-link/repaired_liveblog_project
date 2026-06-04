"""Admin panel context processors."""
from django.contrib.auth import get_user_model

User = get_user_model()


def admin_online_count(request):
    """Add online_count to context for admin panel pages (live, same as users table Online column)."""
    if not request.path.startswith('/admin/'):
        return {}
    try:
        from login.middleware import is_user_online

        count = sum(
            1 for u in User.objects.filter(is_active=True).only('pk')
            if is_user_online(u)
        )
    except Exception:
        count = 0
    return {'admin_online_count': count}
