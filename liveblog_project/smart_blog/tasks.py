from datetime import timedelta

from celery import shared_task

from smart_blog.services.trending_service import (
    calculate_trending,
    rollup_item_stats_hourly_for_hour,
)


@shared_task
def update_trending():
    """Recalculate TrendingItem rows (schedule Celery Beat every ~12 min)."""
    return calculate_trending()


@shared_task
def rollup_hourly_stats():
    """Fill ItemStatsHourly for the last completed local hour."""
    return rollup_item_stats_hourly_for_hour()


@shared_task
def prune_view_events():
    """Delete ViewEvent rows older than 8 days (trending only looks at 7)."""
    from django.utils import timezone
    from smart_blog.models import ViewEvent

    cutoff = timezone.now() - timedelta(days=8)
    deleted, _ = ViewEvent.objects.filter(created_at__lt=cutoff).delete()
    return deleted


def save_search_history_record(user_id, query, results_count, filters_dict, from_history):
    """Write search history (sync). Use from the search view so history works without Celery."""
    from smart_blog.models import SearchHistory

    existing = SearchHistory.objects.filter(
        user_id=user_id,
        search_query__iexact=query,
        search_filters=filters_dict,
    ).first()

    if existing:
        was_clicked = existing.was_clicked
        existing.delete()
        SearchHistory.objects.create(
            user_id=user_id,
            search_query=existing.search_query if from_history else query,
            results_count=results_count,
            search_filters=filters_dict,
            was_clicked=was_clicked,
        )
    elif not from_history:
        SearchHistory.objects.create(
            user_id=user_id,
            search_query=query,
            results_count=results_count,
            search_filters=filters_dict,
            was_clicked=False,
        )

    all_ids = list(
        SearchHistory.objects.filter(user_id=user_id)
        .order_by('-created_at')
        .values_list('pk', flat=True)
    )
    if len(all_ids) > 25:
        SearchHistory.objects.filter(pk__in=all_ids[25:]).delete()


@shared_task
def save_search_history(user_id, query, results_count, filters_dict, from_history):
    """Async variant (optional); prefer save_search_history_record in request paths."""
    save_search_history_record(
        user_id, query, results_count, filters_dict, from_history
    )
