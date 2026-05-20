"""Daily post publication limit for non-admin users (5 posts per 24 hours)."""

import math
from datetime import timedelta

from django.utils import timezone

from smart_blog.models import Item

DAILY_POST_LIMIT = 5
DAILY_POST_LIMIT_MESSAGE = "The post publishing limit has been reached!"
BLOCK_RESET_HOURS = 24


def _posts_in_rolling_window_qs(user):
    since = timezone.now() - timedelta(hours=BLOCK_RESET_HOURS)
    return Item.objects.filter(
        author=user,
        deleted_at__isnull=True,
        published_date__gte=since,
    )


def count_user_posts_in_rolling_window(user) -> int:
    return _posts_in_rolling_window_qs(user).count()


def get_daily_post_limit_reset_at(user):
    """
    When the user may post again: 24 hours after the oldest post
    in the current rolling window (once 5 posts were published in 24h).
    """
    qs = _posts_in_rolling_window_qs(user).order_by("published_date")
    if qs.count() < DAILY_POST_LIMIT:
        return None
    oldest = qs.first()
    return oldest.published_date + timedelta(hours=BLOCK_RESET_HOURS)


def can_user_publish_post_today(user):
    """
    Returns (allowed: bool, error_message: str | None).
    Staff and superusers are exempt.
    """
    if not user or not user.is_authenticated:
        return False, DAILY_POST_LIMIT_MESSAGE
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return True, None
    reset_at = get_daily_post_limit_reset_at(user)
    if reset_at and timezone.now() < reset_at:
        return False, DAILY_POST_LIMIT_MESSAGE
    return True, None


def format_reset_countdown_hours(reset_at) -> str:
    """Whole hours remaining until reset_at (ceil, for display)."""
    if not reset_at:
        return "0"
    remaining = max(0, int((reset_at - timezone.now()).total_seconds()))
    if remaining == 0:
        return "0"
    return str(min(BLOCK_RESET_HOURS, math.ceil(remaining / 3600)))


def get_daily_post_limit_ui_context(user):
    """Template/JSON context for blocked state and countdown target."""
    if not user or not user.is_authenticated:
        return {
            "post_daily_limit_reached": False,
            "post_daily_limit_blocked": False,
            "post_daily_limit_message": "",
            "post_daily_limit_reset_at": "",
            "post_daily_limit_timer_initial": "",
        }
    allowed, msg = can_user_publish_post_today(user)
    blocked = not allowed
    reset_at = get_daily_post_limit_reset_at(user) if blocked else None
    return {
        "post_daily_limit_reached": blocked,
        "post_daily_limit_blocked": blocked,
        "post_daily_limit_message": msg if blocked else "",
        "post_daily_limit_reset_at": reset_at.isoformat() if reset_at else "",
        "post_daily_limit_timer_initial": format_reset_countdown_hours(reset_at) if reset_at else "",
    }
