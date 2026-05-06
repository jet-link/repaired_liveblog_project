"""Rate limit for reports: 30 per 24 hours per user."""

from datetime import timedelta

from django.utils import timezone

from smart_blog.models import ContentReport

REPORT_LIMIT_PER_24H = 30


def can_user_report(user):
    """
    Check if user can submit a new report (rate limit).
    Returns (allowed: bool, error_message: str | None).
    """
    if not user or not user.is_authenticated:
        return False, "Authentication required."
    since = timezone.now() - timedelta(hours=24)
    recent_count = ContentReport.objects.filter(
        reporter=user,
        created_at__gte=since,
    ).count()
    if recent_count >= REPORT_LIMIT_PER_24H:
        return False, "You have reached the report limit. Try again in 24 hours."
    return True, None
