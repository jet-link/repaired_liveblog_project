"""Dashboard totals: SQL aggregates only (no Python-side sum over all rows)."""
from __future__ import annotations

from datetime import date

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

User = get_user_model()


def get_dashboard_summary(today: date) -> dict:
    """
    Return total_* and *_today counters for the admin home dashboard.

    Uses Coalesce(Sum(...), 0) for denormalized counters on Item so we never
    fetch every views_count/reposts_count row into memory.
    """
    from backups.models import Backup
    from smart_blog.models import Bookmark, Comment, ContentReport, Item, Like

    item_agg = Item.objects.aggregate(
        total_posts=Count("pk"),
        total_views=Coalesce(Sum("views_count"), 0),
        total_reposts=Coalesce(Sum("reposts_count"), 0),
    )

    return {
        "total_posts": item_agg["total_posts"] or 0,
        "total_users": User._base_manager.count(),
        "total_comments": Comment.objects.filter(parent__isnull=True).count(),
        "total_likes": Like.objects.count(),
        "total_bookmarks": Bookmark.objects.count(),
        "total_replies": Comment.objects.filter(parent__isnull=False).count(),
        "total_backups": Backup.objects.count(),
        "total_views": int(item_agg["total_views"] or 0),
        "total_reposts": int(item_agg["total_reposts"] or 0),
        "posts_today": Item.objects.filter(published_date__date=today).count(),
        "users_today": User._base_manager.filter(date_joined__date=today).count(),
        "comments_today": Comment.objects.filter(created__date=today).count(),
        "reports_today": ContentReport.objects.filter(created_at__date=today).count(),
    }
