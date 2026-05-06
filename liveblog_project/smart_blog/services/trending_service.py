"""
Velocity-based trending for published Items.

Score uses a Reddit/HN-inspired formula with velocity bonus (see Phase 3).
All aggregation uses batch SQL (3-5 queries total, not per-item).
ViewEvent provides non-unique page-view counts for real velocity.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone

from smart_blog.models import (
    Bookmark, Comment, Item, ItemStatsHourly, Like,
    PostRepost, TrendingItem, ViewEvent,
)

TRENDING_API_CACHE_KEY = "trending:api_snapshot"

TRUST_SCORE_MIN = 3.0
ACTIVE_DAYS = 7


def _author_trust_ok(item: Item) -> bool:
    author = item.author
    if author is None:
        return True
    score = float(getattr(getattr(author, "profile", None), "trust_score", 10.0))
    return score >= TRUST_SCORE_MIN


def _published_anchor(item: Item):
    return item.published_date or item.created


def local_hour_floor(dt):
    """Start of calendar hour in TIME_ZONE as aware datetime."""
    tz = timezone.get_current_timezone()
    local = timezone.localtime(dt, tz)
    return local.replace(minute=0, second=0, microsecond=0)


def previous_completed_hour_bounds(now=None):
    """Return (hour_start, hour_end) for the last fully closed local hour."""
    now = now or timezone.now()
    cur_floor = local_hour_floor(now)
    hour_start = cur_floor - timedelta(hours=1)
    hour_end = cur_floor
    return hour_start, hour_end


# ---------------------------------------------------------------------------
# Scoring formulas (Phase 3)
# ---------------------------------------------------------------------------

def trend_score_from_stats(
    views: int, likes: int, comments: int,
    bookmarks: int, reposts: int,
    hours_since_post: float,
    engagement_1h: float = 0,
    engagement_prev_1h: float = 0,
) -> float:
    """Reddit/HN-inspired score with velocity bonus.

    base = log10(max(views*0.5 + likes*3 + comments*5 + bookmarks*4 + reposts*6, 1))
    velocity_bonus = engagement_1h / max(engagement_prev_1h, 1)   capped at 3.0
    score = (base * (1 + 0.3 * min(velocity_bonus, 3.0))) / age_penalty
    """
    raw = views * 0.5 + likes * 3.0 + comments * 5.0 + bookmarks * 4.0 + reposts * 6.0
    base = math.log10(max(raw, 1))
    age_penalty = math.pow(max(hours_since_post, 0.0) + 2.0, 1.5)
    velocity_bonus = engagement_1h / max(engagement_prev_1h, 1) if engagement_prev_1h >= 0 else 0
    score = (base * (1.0 + 0.3 * min(velocity_bonus, 3.0))) / age_penalty
    return score


def growth_rate_from_engagement(
    views_1h: int, likes_1h: int, comments_1h: int,
    bookmarks_1h: int, reposts_1h: int,
    views_prev: int, likes_prev: int, comments_prev: int,
    bookmarks_prev: int, reposts_prev: int,
) -> float:
    """Engagement velocity: combined weighted engagement in last hour vs previous."""
    eng_1h = views_1h + likes_1h * 3 + comments_1h * 5 + bookmarks_1h * 4 + reposts_1h * 6
    eng_prev = views_prev + likes_prev * 3 + comments_prev * 5 + bookmarks_prev * 4 + reposts_prev * 6
    return float(eng_1h) / float(max(eng_prev, 1))


def _engagement_total(views, likes, comments, bookmarks, reposts):
    return views + likes * 3 + comments * 5 + bookmarks * 4 + reposts * 6


# ---------------------------------------------------------------------------
# Batch aggregation helpers
# ---------------------------------------------------------------------------

def _aggregate_view_events(since_24h, since_1h, since_2h):
    """Aggregate ViewEvent counts per item for 24h, 1h, and prev-1h windows."""
    qs = (
        ViewEvent.objects.filter(created_at__gte=since_24h)
        .values("item_id")
        .annotate(
            views_24h=Count("id"),
            views_1h=Count("id", filter=Q(created_at__gte=since_1h)),
            views_prev_1h=Count("id", filter=Q(
                created_at__gte=since_2h, created_at__lt=since_1h
            )),
        )
    )
    result = {}
    for row in qs:
        result[row["item_id"]] = {
            "views_24h": row["views_24h"],
            "views_1h": row["views_1h"],
            "views_prev_1h": row["views_prev_1h"],
        }
    return result


def _aggregate_likes(since_24h, since_1h, since_2h):
    qs = (
        Like.objects.filter(created_at__gte=since_24h)
        .values("item_id")
        .annotate(
            likes_24h=Count("id"),
            likes_1h=Count("id", filter=Q(created_at__gte=since_1h)),
            likes_prev_1h=Count("id", filter=Q(
                created_at__gte=since_2h, created_at__lt=since_1h
            )),
        )
    )
    result = {}
    for row in qs:
        result[row["item_id"]] = {
            "likes_24h": row["likes_24h"],
            "likes_1h": row["likes_1h"],
            "likes_prev_1h": row["likes_prev_1h"],
        }
    return result


def _aggregate_comments(since_24h, since_1h, since_2h):
    qs = (
        Comment.objects.filter(is_draft=False, created__gte=since_24h)
        .values("item_id")
        .annotate(
            comments_24h=Count("id"),
            comments_1h=Count("id", filter=Q(created__gte=since_1h)),
            comments_prev_1h=Count("id", filter=Q(
                created__gte=since_2h, created__lt=since_1h
            )),
        )
    )
    result = {}
    for row in qs:
        result[row["item_id"]] = {
            "comments_24h": row["comments_24h"],
            "comments_1h": row["comments_1h"],
            "comments_prev_1h": row["comments_prev_1h"],
        }
    return result


def _aggregate_bookmarks(since_24h, since_1h, since_2h):
    qs = (
        Bookmark.objects.filter(created_at__gte=since_24h)
        .values("item_id")
        .annotate(
            bookmarks_24h=Count("id"),
            bookmarks_1h=Count("id", filter=Q(created_at__gte=since_1h)),
            bookmarks_prev_1h=Count("id", filter=Q(
                created_at__gte=since_2h, created_at__lt=since_1h
            )),
        )
    )
    result = {}
    for row in qs:
        result[row["item_id"]] = {
            "bookmarks_24h": row["bookmarks_24h"],
            "bookmarks_1h": row["bookmarks_1h"],
            "bookmarks_prev_1h": row["bookmarks_prev_1h"],
        }
    return result


def _aggregate_reposts(since_24h, since_1h, since_2h):
    qs = (
        PostRepost.objects.filter(created_at__gte=since_24h)
        .values("item_id")
        .annotate(
            reposts_24h=Count("id"),
            reposts_1h=Count("id", filter=Q(created_at__gte=since_1h)),
            reposts_prev_1h=Count("id", filter=Q(
                created_at__gte=since_2h, created_at__lt=since_1h
            )),
        )
    )
    result = {}
    for row in qs:
        result[row["item_id"]] = {
            "reposts_24h": row["reposts_24h"],
            "reposts_1h": row["reposts_1h"],
            "reposts_prev_1h": row["reposts_prev_1h"],
        }
    return result


# ---------------------------------------------------------------------------
# Main trending calculation
# ---------------------------------------------------------------------------

_ZERO_VIEWS = {"views_24h": 0, "views_1h": 0, "views_prev_1h": 0}
_ZERO_LIKES = {"likes_24h": 0, "likes_1h": 0, "likes_prev_1h": 0}
_ZERO_COMMENTS = {"comments_24h": 0, "comments_1h": 0, "comments_prev_1h": 0}
_ZERO_BOOKMARKS = {"bookmarks_24h": 0, "bookmarks_1h": 0, "bookmarks_prev_1h": 0}
_ZERO_REPOSTS = {"reposts_24h": 0, "reposts_1h": 0, "reposts_prev_1h": 0}


def calculate_trending(now=None) -> int:
    """
    Recompute TrendingItem for all eligible posts using batch SQL aggregation.
    Returns number of TrendingItem rows written.
    """
    now = now or timezone.now()
    since_24h = now - timedelta(hours=24)
    since_1h = now - timedelta(hours=1)
    since_2h = now - timedelta(hours=2)
    since_days = now - timedelta(days=ACTIVE_DAYS)

    items = list(
        Item.objects.filter(is_published=True, published_date__gte=since_days)
        .select_related("author", "author__profile")
        .only("pk", "published_date", "created", "author_id",
              "author__id", "author__profile__trust_score")
    )

    view_stats = _aggregate_view_events(since_24h, since_1h, since_2h)
    like_stats = _aggregate_likes(since_24h, since_1h, since_2h)
    comment_stats = _aggregate_comments(since_24h, since_1h, since_2h)
    bookmark_stats = _aggregate_bookmarks(since_24h, since_1h, since_2h)
    repost_stats = _aggregate_reposts(since_24h, since_1h, since_2h)

    written = 0
    seen_ids: list[int] = []

    for item in items:
        if not _author_trust_ok(item):
            continue

        iid = item.pk
        v = view_stats.get(iid, _ZERO_VIEWS)
        l = like_stats.get(iid, _ZERO_LIKES)
        c = comment_stats.get(iid, _ZERO_COMMENTS)
        b = bookmark_stats.get(iid, _ZERO_BOOKMARKS)
        r = repost_stats.get(iid, _ZERO_REPOSTS)

        anchor = _published_anchor(item)
        hours = (now - anchor).total_seconds() / 3600.0

        eng_1h = _engagement_total(
            v["views_1h"], l["likes_1h"], c["comments_1h"],
            b["bookmarks_1h"], r["reposts_1h"],
        )
        eng_prev_1h = _engagement_total(
            v["views_prev_1h"], l["likes_prev_1h"], c["comments_prev_1h"],
            b["bookmarks_prev_1h"], r["reposts_prev_1h"],
        )

        score = trend_score_from_stats(
            v["views_24h"], l["likes_24h"], c["comments_24h"],
            b["bookmarks_24h"], r["reposts_24h"],
            hours, eng_1h, eng_prev_1h,
        )

        growth = growth_rate_from_engagement(
            v["views_1h"], l["likes_1h"], c["comments_1h"],
            b["bookmarks_1h"], r["reposts_1h"],
            v["views_prev_1h"], l["likes_prev_1h"], c["comments_prev_1h"],
            b["bookmarks_prev_1h"], r["reposts_prev_1h"],
        )

        TrendingItem.objects.update_or_create(
            item=item,
            defaults={
                "trend_score": score,
                "views_24h": v["views_24h"],
                "likes_24h": l["likes_24h"],
                "comments_24h": c["comments_24h"],
                "bookmarks_24h": b["bookmarks_24h"],
                "reposts_24h": r["reposts_24h"],
                "growth_rate": growth,
                "views_last_hour": v["views_1h"],
                "likes_1h": l["likes_1h"],
                "comments_1h": c["comments_1h"],
                "bookmarks_1h": b["bookmarks_1h"],
                "reposts_1h": r["reposts_1h"],
                "views_prev_hour": v["views_prev_1h"],
                "likes_prev_1h": l["likes_prev_1h"],
                "comments_prev_1h": c["comments_prev_1h"],
                "bookmarks_prev_1h": b["bookmarks_prev_1h"],
                "reposts_prev_1h": r["reposts_prev_1h"],
            },
        )
        written += 1
        seen_ids.append(iid)

    if seen_ids:
        TrendingItem.objects.exclude(item_id__in=seen_ids).delete()
    else:
        TrendingItem.objects.all().delete()

    cache.delete(TRENDING_API_CACHE_KEY)
    return written


# ---------------------------------------------------------------------------
# Hourly rollup (uses ViewEvent for view counts)
# ---------------------------------------------------------------------------

def rollup_item_stats_hourly_for_hour(hour_start_local=None, now=None) -> int:
    """
    Fill ItemStatsHourly for one hour bucket [hour_start, hour_start+1h).
    Uses ViewEvent (non-unique) for view counts.
    Returns number of rows upserted.
    """
    now = now or timezone.now()
    if hour_start_local is None:
        hour_start_local, hour_end_local = previous_completed_hour_bounds(now)
    else:
        hour_end_local = hour_start_local + timedelta(hours=1)

    view_agg = dict(
        ViewEvent.objects.filter(
            created_at__gte=hour_start_local, created_at__lt=hour_end_local
        ).values("item_id").annotate(cnt=Count("id")).values_list("item_id", "cnt")
    )

    like_agg = dict(
        Like.objects.filter(
            created_at__gte=hour_start_local, created_at__lt=hour_end_local
        ).values("item_id").annotate(cnt=Count("id")).values_list("item_id", "cnt")
    )

    comment_agg = dict(
        Comment.objects.filter(
            is_draft=False,
            created__gte=hour_start_local, created__lt=hour_end_local,
        ).values("item_id").annotate(cnt=Count("id")).values_list("item_id", "cnt")
    )

    item_ids = set(view_agg) | set(like_agg) | set(comment_agg)

    count = 0
    for iid in item_ids:
        ItemStatsHourly.objects.update_or_create(
            item_id=iid,
            hour_start=hour_start_local,
            defaults={
                "views": view_agg.get(iid, 0),
                "likes": like_agg.get(iid, 0),
                "comments": comment_agg.get(iid, 0),
            },
        )
        count += 1
    return count
