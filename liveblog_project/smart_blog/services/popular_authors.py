"""Popular authors sidebar for the BraiNews home feed."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Count, ExpressionWrapper, F, FloatField, Q, Sum
from django.db.models.functions import Coalesce
from django.templatetags.static import static
from django.urls import reverse

from smart_blog.utils import count_convert

POPULAR_AUTHORS_CACHE_KEY = "brainews:popular_authors_sidebar:v2"
POPULAR_AUTHORS_CACHE_TTL = 60
POPULAR_AUTHORS_LIMIT = 10
USERNAME_DISPLAY_MAX = 35

User = get_user_model()


def _truncate_username(username: str, max_len: int = USERNAME_DISPLAY_MAX) -> str:
    if len(username) <= max_len:
        return username
    if max_len <= 1:
        return "…"
    return username[: max_len - 1] + "…"


def _user_status_label(user) -> str:
    if user is None:
        return "Deleted user"
    if not user.is_active:
        if getattr(user, "deleted_queue_entry", None):
            return "Deleted user"
        return "Banned user"
    return str(user.username)


def _resolve_avatar_url(path: str | None) -> str:
    if not path:
        return static("img/no_avatar.svg")
    if path.startswith(("http://", "https://", "/")):
        return path
    return static(path)


def _author_entry(user) -> dict:
    post_count = int(user.post_count or 0)
    total_likes = int(user.total_likes or 0)
    total_views = int(user.total_views or 0)
    total_comments = int(user.total_comments or 0)
    avg_likes = round(total_likes / post_count) if post_count else 0
    avg_views = round(total_views / post_count) if post_count else 0
    avg_comments = round(total_comments / post_count) if post_count else 0

    if user.is_active:
        profile_url = reverse("login_app:profile", kwargs={"username": user.username})
        username_label = str(user.username)
        try:
            avatar_url = _resolve_avatar_url(user.profile.get_avatar())
        except Exception:
            avatar_url = static("img/no_avatar.svg")
    else:
        profile_url = reverse("login_app:vanished")
        username_label = _user_status_label(user)
        avatar_url = static("img/user-deleted.webp")

    return {
        "id": user.pk,
        "username": user.username,
        "username_display": _truncate_username(username_label),
        "username_title": username_label,
        "profile_url": profile_url,
        "avatar_url": avatar_url,
        "is_active": bool(user.is_active),
        "post_count": post_count,
        "post_count_human": count_convert(post_count),
        "avg_likes": avg_likes,
        "avg_likes_human": count_convert(avg_likes),
        "avg_views": avg_views,
        "avg_views_human": count_convert(avg_views),
        "avg_comments": avg_comments,
        "avg_comments_human": count_convert(avg_comments),
    }


def get_popular_authors_payload(limit: int = POPULAR_AUTHORS_LIMIT) -> list[dict]:
    cached = cache.get(POPULAR_AUTHORS_CACHE_KEY)
    if cached is not None:
        return cached[:limit]

    published_filter = Q(items__is_published=True)
    comment_filter = published_filter & Q(
        items__comments__parent__isnull=True,
        items__comments__is_draft=False,
        items__comments__deleted_at__isnull=True,
    )
    authors = (
        User.objects.filter(items__is_published=True)
        .select_related("profile")
        .annotate(
            post_count=Count("items", filter=published_filter, distinct=True),
            total_likes=Coalesce(Sum("items__likes_count", filter=published_filter), 0),
            total_views=Coalesce(Sum("items__views_count", filter=published_filter), 0),
            total_reposts=Coalesce(Sum("items__reposts_count", filter=published_filter), 0),
            total_bookmarks=Coalesce(Sum("items__bookmarks_count", filter=published_filter), 0),
            total_comments=Coalesce(Count("items__comments", filter=comment_filter, distinct=True), 0),
        )
        .filter(post_count__gt=0)
        .annotate(
            popular_score=ExpressionWrapper(
                F("post_count") * 100
                + F("total_likes") * 10
                + F("total_reposts") * 50
                + F("total_views") * 1
                + F("total_bookmarks") * 15,
                output_field=FloatField(),
            )
        )
        .order_by("-popular_score", "-post_count", "-pk")[:limit]
    )

    payload = [_author_entry(user) for user in authors]
    cache.set(POPULAR_AUTHORS_CACHE_KEY, payload, POPULAR_AUTHORS_CACHE_TTL)
    return payload
