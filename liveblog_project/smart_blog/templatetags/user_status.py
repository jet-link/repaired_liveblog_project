"""Template tags for user status display: active, banned, deleted."""
from django import template

register = template.Library()


@register.simple_tag
def user_status_display(user):
    """
    Return display label: username if active, 'Banned user' if banned, 'Deleted user' if None.
    """
    if user is None:
        return "Deleted user"
    if not user.is_active:
        if getattr(user, "deleted_queue_entry", None):
            return "Deleted user"
        return "Banned user"
    return str(user.username)


@register.simple_tag
def user_status_title(user):
    """Title for hover: same label as display."""
    return user_status_display(user)
