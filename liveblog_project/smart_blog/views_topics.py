from datetime import timedelta
from urllib.parse import urlencode

from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Count, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from smart_blog.models import Category, Item, TrendingItem
from smart_blog.public_listing_cache import TOPICS_LIST_CACHE_KEY
from smart_blog.utils import breadcrumb, build_breadcrumbs
from smart_blog.views import (
    annotate_user_bookmarked,
    annotate_user_liked,
    feed_list_optimizations,
)

TOPICS_CACHE_TTL = 600

LIST_PER_PAGE = 40
FEATURED_COUNT = 6


def _trending_category_ids(limit=40):
    return set(
        TrendingItem.objects.filter(
            item__deleted_at__isnull=True,
            item__is_published=True,
            item__category__isnull=False,
        )
        .order_by("-trend_score")[:limit]
        .values_list("item__category_id", flat=True)
    )


def _get_topics_data():
    """Cached topics list data (heavy aggregation query)."""
    cache_key = TOPICS_LIST_CACHE_KEY
    data = cache.get(cache_key)
    if data is not None:
        return data

    latest_title = Subquery(
        Item.objects.filter(category_id=OuterRef("pk"), is_published=True)
        .order_by("-published_date")
        .values("title")[:1]
    )

    qs = (
        Category.objects.annotate(
            posts_count=Count("items", filter=Q(items__is_published=True)),
            recent_7d=Count(
                "items",
                filter=Q(
                    items__is_published=True,
                    items__published_date__gte=timezone.now() - timedelta(days=7),
                ),
            ),
            latest_post_title=latest_title,
        )
        .filter(posts_count__gt=0)
        .order_by("-posts_count", "-recent_7d", "name")
    )

    all_topics = list(qs)
    trending_cat_ids = _trending_category_ids()

    data = {"all_topics": all_topics, "trending_category_ids": trending_cat_ids}
    cache.set(cache_key, data, TOPICS_CACHE_TTL)
    return data


def topics_list(request):
    data = _get_topics_data()
    all_topics = data["all_topics"]
    featured = all_topics[:FEATURED_COUNT]

    breadcrumbs = build_breadcrumbs(
        breadcrumb("Topics", None),
    )

    return render(
        request,
        "smart_blog/topics_list.html",
        {
            "topics_featured": featured,
            "topics_all": all_topics,
            "trending_category_ids": data["trending_category_ids"],
            "breadcrumbs": breadcrumbs,
        },
    )


_VALID_TOPIC_SORT = frozenset({"latest", "liked", "discussed"})


def _topic_listing_source_url(request, category_slug, sort, *, from_sitemap=False):
    path = reverse("smart_blog:topic_detail", kwargs={"slug": category_slug})
    q = {}
    if from_sitemap:
        q["from"] = "sitemap"
    if sort != "latest":
        q["sort"] = sort
    if q:
        path = f"{path}?{urlencode(q)}"
    return request.build_absolute_uri(path)


def _topic_extra_qs(sort, *, from_sitemap=False):
    q = {}
    if from_sitemap:
        q["from"] = "sitemap"
    if sort != "latest":
        q["sort"] = sort
    if not q:
        return ""
    return urlencode(q) + "&"


def topic_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    from_sitemap = request.GET.get("from") == "sitemap"
    sort = (request.GET.get("sort") or "latest").lower()
    if sort not in _VALID_TOPIC_SORT:
        sort = "latest"

    qs = feed_list_optimizations(
        Item.objects.filter(is_published=True, category=category)
        .with_counters()
        .select_related("category", "author", "author__profile")
        .prefetch_related("tags")
    )
    qs = annotate_user_liked(qs, request.user)
    qs = annotate_user_bookmarked(qs, request.user)

    if sort == "liked":
        qs = qs.order_by("-likes_count", "-published_date", "-pk")
    elif sort == "discussed":
        qs = qs.order_by("-comments_count", "-published_date", "-pk")
    else:
        qs = qs.order_by("-published_date", "-pk")

    paginator = Paginator(qs, LIST_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))
    page_range = paginator.get_elided_page_range(
        number=page_obj.number,
        on_each_side=1,
        on_ends=1,
    )

    if from_sitemap:
        mid = breadcrumb("Sitemap", reverse("pages:sitemap_page"))
    else:
        mid = breadcrumb("Topics", reverse("smart_blog:topics_list"))
    breadcrumbs = build_breadcrumbs(
        mid,
        breadcrumb(category.name, None),
    )

    ctx = {
        "category": category,
        "topic_sort": sort,
        "from_sitemap": from_sitemap,
        "page_obj": page_obj,
        "page_range": page_range,
        "items": page_obj.object_list,
        "breadcrumbs": breadcrumbs,
        "listing_source_url": _topic_listing_source_url(
            request, category.slug, sort, from_sitemap=from_sitemap
        ),
        "topic_extra_qs": _topic_extra_qs(sort, from_sitemap=from_sitemap),
    }

    if request.GET.get("partial") == "1":
        return render(request, "smart_blog/includes/topic_hub_feed.html", ctx)

    return render(request, "smart_blog/topic_hub.html", ctx)
