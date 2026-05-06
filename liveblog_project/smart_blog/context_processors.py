from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q, Count
from django.utils import timezone

from .models import Notification, Category, Item
from smart_blog.feed_queryset import feed_list_optimizations
from .search_utils import apply_popular_filter

NOTIFICATIONS_CACHE_TIMEOUT = 30  # seconds
NOTIFICATIONS_CACHE_KEY = "notifications_count_{user_id}"


def invalidate_notifications_cache(user_id):
    """Call after creating/reading notifications to refresh count on next request."""
    cache.delete(NOTIFICATIONS_CACHE_KEY.format(user_id=user_id))


def notifications_context(request):
    if not request.user.is_authenticated:
        return {"notifications_count": 0, "notifications_count_label": ""}

    cache_key = NOTIFICATIONS_CACHE_KEY.format(user_id=request.user.pk)
    count = cache.get(cache_key)
    if count is None:
        count = (
            Notification.objects
            .filter(recipient=request.user, is_read=False, cleared_from_inbox=False)
            .filter(Q(item__isnull=False) | Q(notif_type=Notification.TYPE_FROM_ADMIN))
            .exclude(
                Q(notif_type=Notification.TYPE_REPLY, reply_comment__isnull=True) |
                Q(notif_type=Notification.TYPE_REPLY, parent_comment__isnull=True) |
                Q(notif_type=Notification.TYPE_COMMENT_LIKE, parent_comment__isnull=True, reply_comment__isnull=True)
            )
            .count()
        )
        cache.set(cache_key, count, timeout=NOTIFICATIONS_CACHE_TIMEOUT)
    label = ""
    if count > 0:
        label = "10+" if count >= 10 else str(count)
    return {
        "notifications_count": count,
        "notifications_count_label": label,
    }


def spellcheck_context(request):
    """Add spellcheck_lang for templates (used by data-spellcheck-lang)."""
    if request.path.startswith("/admin/"):
        return {"spellcheck_lang": "en"}
    return {"spellcheck_lang": getattr(settings, "SPELLCHECK_LANG", "en")}


NAV_CATEGORIES_CACHE_KEY = "nav_categories_ctx"
NAV_CATEGORIES_CACHE_TTL = 300  # 5 minutes


def invalidate_nav_categories_cache():
    """Call after category/item create/delete to refresh navigation data."""
    cache.delete(NAV_CATEGORIES_CACHE_KEY)


def _build_nav_categories_data():
    ranked = (
        Category.objects.annotate(
            posts_count=Count("items", filter=Q(items__is_published=True)),
        )
        .order_by("-posts_count", "name")
    )
    nav_categories_all = list(ranked)
    nav_categories_first = nav_categories_all[:12]
    nav_categories_rest = nav_categories_all[12:]

    top_categories = (
        Category.objects.annotate(
            posts_count=Count("items", filter=Q(items__is_published=True)),
        )
        .filter(posts_count__gt=0)
        .order_by("-posts_count", "name")[:6]
    )

    since = timezone.now() - timedelta(days=15)
    categories_modal_popular_cards = []

    for cat in top_categories:
        scoped = feed_list_optimizations(
            Item.objects.filter(
                category=cat,
                is_published=True,
                published_date__gte=since,
            )
            .with_counters()
            .select_related("category", "author", "author__profile")
        )
        popular_item = apply_popular_filter(scoped).first()
        if not popular_item:
            popular_item = (
                feed_list_optimizations(
                    Item.objects.filter(category=cat, is_published=True)
                    .with_counters()
                    .select_related("category", "author", "author__profile")
                )
                .order_by("-published_date", "-pk")
                .first()
            )
        if popular_item:
            categories_modal_popular_cards.append(
                {
                    "category": cat,
                    "posts_count": cat.posts_count,
                    "item": popular_item,
                }
            )

    return {
        "nav_categories": nav_categories_all,
        "nav_categories_first": nav_categories_first,
        "nav_categories_rest": nav_categories_rest,
        "categories_modal_popular_cards": categories_modal_popular_cards,
    }


def nav_categories_context(request):
    """
    Header modal: categories ordered by popularity; first 12 chips + show more in same grid;
    up to 6 cards — one popular post per top category.
    Cached for NAV_CATEGORIES_CACHE_TTL seconds to avoid ~8-14 DB queries per request.
    """
    data = cache.get(NAV_CATEGORIES_CACHE_KEY)
    if data is None:
        data = _build_nav_categories_data()
        cache.set(NAV_CATEGORIES_CACHE_KEY, data, NAV_CATEGORIES_CACHE_TTL)
    return data
