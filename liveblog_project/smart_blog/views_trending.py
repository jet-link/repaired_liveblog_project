"""Trending page and JSON API (velocity ranking)."""
from django.conf import settings
from django.core.cache import cache
from django_ratelimit.decorators import ratelimit
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse

from smart_blog.models import TrendingItem
from smart_blog.services.trending_service import TRENDING_API_CACHE_KEY
from smart_blog.utils import count_convert

HOT_LIMIT = 5
RISING_LIMIT = 10
FEED_PER_PAGE = 20
API_CACHE_TTL = settings.TRENDING_API_CACHE_SECONDS


def _preview_from_list_excerpt(item, max_len=220):
    s = (item.list_excerpt or "").strip()
    if len(s) <= max_len:
        return s
    return s[:max_len].rsplit(" ", 1)[0] + " …"


def _base_qs():
    return (
        TrendingItem.objects.filter(
            item__deleted_at__isnull=True,
            item__is_published=True,
        )
        .select_related(
            "item",
            "item__category",
            "item__author",
            "item__author__profile",
        )
        .prefetch_related("item__images")
    )


def _get_trending_page_data(page=1):
    """Returns (hot_rows, rising_rows, feed_page) from a single base queryset."""
    all_by_score = list(_base_qs().order_by("-trend_score")[:200])

    hot_rows = [t for t in all_by_score if t.views_last_hour >= 1][:HOT_LIMIT]
    if len(hot_rows) < HOT_LIMIT:
        hot_rows = all_by_score[:HOT_LIMIT]

    rising_rows = sorted(all_by_score, key=lambda t: t.growth_rate, reverse=True)[:RISING_LIMIT]

    paginator = Paginator(all_by_score, FEED_PER_PAGE)
    feed_page = paginator.get_page(page)
    return hot_rows, rising_rows, feed_page


def _serialize_item(request, t: TrendingItem, rank=None):
    """Serialize a TrendingItem with both real-time totals and 24h/1h trending windows."""
    item = t.item
    img = item.images.first()
    thumb = img.get_thumbnail_url() if img else ""
    url = item.get_absolute_url()
    abs_url = request.build_absolute_uri(url) if request else url
    return {
        "rank": rank,
        "slug": item.slug,
        "title": item.title,
        "url": abs_url,
        "path": url,
        "preview": _preview_from_list_excerpt(item),
        "category": item.category.name if item.category else None,
        "trend_score": round(t.trend_score, 6),
        # Real-time totals (updated instantly via signals)
        "total_views": item.views_count,
        "total_likes": item.likes_count,
        "total_bookmarks": item.bookmarks_count,
        "total_reposts": item.reposts_count,
        "total_views_h": count_convert(item.views_count),
        "total_likes_h": count_convert(item.likes_count),
        "total_bookmarks_h": count_convert(item.bookmarks_count),
        "total_reposts_h": count_convert(item.reposts_count),
        # 24h/1h trending windows (refreshed every 12 min by Celery)
        "views_24h": t.views_24h,
        "likes_24h": t.likes_24h,
        "comments_24h": t.comments_24h,
        "bookmarks_24h": t.bookmarks_24h,
        "reposts_24h": t.reposts_24h,
        "growth_rate": round(t.growth_rate, 4),
        "views_last_hour": t.views_last_hour,
        "likes_1h": t.likes_1h,
        "comments_1h": t.comments_1h,
        "thumbnail": thumb,
        "author": item.author.username if item.author else None,
    }


def _payload(request, feed_page=1):
    hot_rows, rising_rows, page_obj = _get_trending_page_data(feed_page)
    paginator = page_obj.paginator

    hot_json = [_serialize_item(request, t, rank=i + 1) for i, t in enumerate(hot_rows)]
    rising_json = [_serialize_item(request, t, rank=i + 1) for i, t in enumerate(rising_rows)]
    feed_json = [_serialize_item(request, t, rank=None) for t in page_obj.object_list]

    return {
        "hot": hot_json,
        "rising": rising_json,
        "feed": feed_json,
        "feed_page": page_obj.number,
        "feed_total_pages": paginator.num_pages,
        "feed_has_next": page_obj.has_next(),
        "feed_has_previous": page_obj.has_previous(),
    }


def trending_list(request):
    try:
        page = int(request.GET.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    page = max(1, page)

    hot_rows, rising_rows, feed_page = _get_trending_page_data(page)
    has_trending_content = bool(
        hot_rows or rising_rows or feed_page.object_list
    )

    return render(
        request,
        "smart_blog/trending_list.html",
        {
            "hot_rows": hot_rows,
            "rising_rows": rising_rows,
            "feed_page": feed_page,
            "has_trending_content": has_trending_content,
            "trending_api_url": reverse("smart_blog:api_trending"),
        },
    )


@ratelimit(key='ip', rate=settings.RATELIMIT_TRENDING_RATE, method='GET', block=False)
def trending_api(request):
    if getattr(request, 'limited', False):
        return JsonResponse({'error': 'rate_limited', 'ok': False}, status=429)
    try:
        page = int(request.GET.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    page = max(1, page)

    cached = cache.get(TRENDING_API_CACHE_KEY)
    if cached is not None and page == 1:
        out = dict(cached)
        out.setdefault("ok", True)
        return JsonResponse(out)

    data = _payload(request, feed_page=page)
    data["ok"] = True
    if page == 1:
        cache.set(TRENDING_API_CACHE_KEY, data, API_CACHE_TTL)
    return JsonResponse(data)
