"""Query helpers for smart_blog."""

from smart_blog.models import ContentReport


def has_user_reported_item(user, item):
    """Return True if user has reported this item."""
    if not user or not user.is_authenticated or not item:
        return False
    return ContentReport.objects.filter(item=item, reporter=user).exists()


def has_user_reported_comment(user, comment):
    """Return True if user has reported this comment."""
    if not user or not user.is_authenticated or not comment:
        return False
    return ContentReport.objects.filter(comment=comment, reporter=user).exists()
