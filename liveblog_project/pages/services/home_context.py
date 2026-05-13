"""Home page context: hero, trending, mindset preview, topics — with short-lived caches."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from django.core.cache import cache
from django.db.models import ExpressionWrapper, F, FloatField
from django.http import HttpRequest

from mindset.models import Theme
from pages.home_content import get_home_page
from pages.models import HomePageContent, HomeQuickLink
from smart_blog.feed_queryset import feed_list_optimizations
from smart_blog.models import Item, TrendingItem
from smart_blog.views_topics import _get_topics_data

logger = logging.getLogger(__name__)

HOME_QUICKLINKS_CACHE_TTL = 120
HOME_IN_TREND_CACHE_TTL = 90
HOME_MINDSET_CACHE_TTL = 60

IN_TREND_MAX = 4
MINDSET_MAX = 3
TOPICS_MAX = 6


def _in_trend_cache_key(home: HomePageContent) -> str:
    return f"pages.home.in_trend_pks:{home.cache_bump}:{IN_TREND_MAX}"


def _quicklinks_cache_key(cache_bump: int) -> str:
    return f"pages.home.quicklinks:{cache_bump}"


def _mindset_cache_key(home: HomePageContent) -> str:
    return f"pages.home.mindset:{home.cache_bump}"


def _fetch_in_trend_pks(home: HomePageContent) -> List[int]:
    return list(
        TrendingItem.objects.filter(item__is_published=True)
        .order_by("-trend_score")
        .values_list("item_id", flat=True)[:IN_TREND_MAX]
    )


def _hydrate_items_ordered(pks: List[int]) -> List[Item]:
    if not pks:
        return []
    qs = feed_list_optimizations(
        Item.objects.filter(pk__in=pks).with_counters()
    )
    by_id = {i.pk: i for i in qs}
    return [by_id[i] for i in pks if i in by_id]


def _hydrate_single_item(pk: int) -> Optional[Item]:
    if not pk:
        return None
    qs = feed_list_optimizations(
        Item.objects.filter(pk=pk, is_published=True).with_counters()
    )
    return qs.first()


def _latest_single_item() -> Optional[Item]:
    """Most recent published post for hero fallback."""
    return (
        feed_list_optimizations(
            Item.objects.filter(is_published=True)
            .with_counters()
            .order_by("-published_date", "-pk")
        )
        .first()
    )


def _load_in_trend_items(home: HomePageContent) -> List[Item]:
    if not home.show_in_trend:
        return []
    cache_key = _in_trend_cache_key(home)
    pks = cache.get(cache_key)
    if pks is None:
        try:
            pks = _fetch_in_trend_pks(home)
        except Exception:
            logger.exception("home in_trend query failed")
            pks = []
        cache.set(cache_key, pks, HOME_IN_TREND_CACHE_TTL)
    return _hydrate_items_ordered(pks)


def _load_quick_links(home: HomePageContent) -> List[Any]:
    if not home.show_quick_links:
        return []
    key = _quicklinks_cache_key(home.cache_bump)
    data = cache.get(key)
    if data is not None:
        return data
    rows = list(
        HomeQuickLink.objects.filter(is_active=True)
        .order_by("order", "pk")
        .values("label", "url", "icon_class")
    )
    cache.set(key, rows, HOME_QUICKLINKS_CACHE_TTL)
    return rows


def _load_mindset_preview(home: HomePageContent) -> List[Theme]:
    """Hybrid Mindset preview: 1 freshest theme + 2 popular themes.

    Popularity score mirrors the Mindset sidebar's "Most discussed" formula
    (replies + reposts*0.5 + likes*0.2) so the home preview surfaces the same
    quality content as the dedicated page.
    """
    if not home.show_mindset_live:
        return []
    key = _mindset_cache_key(home)
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        base = Theme.objects.filter(is_deleted=False).select_related(
            "author", "author__profile"
        )
        latest = base.order_by("-created_at").first()
        pop_qs = base.annotate(
            score=ExpressionWrapper(
                F("replies_count") + F("reposts_count") * 0.5 + F("likes_count") * 0.2,
                output_field=FloatField(),
            )
        )
        if latest is not None:
            pop_qs = pop_qs.exclude(pk=latest.pk)
        popular = list(pop_qs.order_by("-score", "-created_at")[: MINDSET_MAX - 1])
        result: List[Theme] = ([latest] if latest is not None else []) + popular
    except Exception:
        logger.exception("home mindset preview query failed")
        result = []
    cache.set(key, result, HOME_MINDSET_CACHE_TTL)
    return result


def _top_categories_slice() -> List[Any]:
    try:
        data = _get_topics_data()
    except Exception:
        logger.exception("home topics data failed")
        return []
    return list(data.get("all_topics", [])[:TOPICS_MAX])


def build_home_page_context(request: Optional[HttpRequest] = None) -> Dict[str, Any]:
    home = get_home_page()
    quick_links = _load_quick_links(home)

    in_trend_items = _load_in_trend_items(home)

    hero_item: Optional[Item] = None
    if home.hero_featured_item_id:
        hero_item = _hydrate_single_item(home.hero_featured_item_id)
    if hero_item is None and in_trend_items:
        hero_item = in_trend_items[0]
    if hero_item is None:
        hero_item = _latest_single_item()

    hero_pk = hero_item.pk if hero_item else None
    in_trend_grid: List[Item] = []
    if in_trend_items:
        in_trend_grid = [x for x in in_trend_items if hero_pk is None or x.pk != hero_pk][
            :IN_TREND_MAX
        ]

    mindset_themes = _load_mindset_preview(home)

    top_categories: List[Any] = []
    if home.show_explore_topics:
        top_categories = _top_categories_slice()

    has_any_posts = Item.objects.filter(is_published=True).exists()

    return {
        "home": home,
        "meta_description": home.meta_description or "",
        "quick_links": quick_links,
        "hero_item": hero_item,
        "in_trend_items": in_trend_grid,
        "mindset_themes": mindset_themes,
        "top_categories": top_categories,
        "has_any_posts": has_any_posts,
    }
