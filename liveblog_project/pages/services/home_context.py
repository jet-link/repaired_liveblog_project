"""Home page context: hero, trending, for-you preview, topics, editor picks, latest — with short-lived caches."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from django.core.cache import cache
from django.http import HttpRequest

from pages.home_content import get_home_page
from pages.models import HomePageContent, HomeQuickLink
from smart_blog.models import Item, TrendingItem
from smart_blog.feed_queryset import feed_list_optimizations
from smart_blog.services.for_you_recommendations import for_you_home_preview
from smart_blog.views_topics import _get_topics_data

logger = logging.getLogger(__name__)

HOME_QUICKLINKS_CACHE_TTL = 120
HOME_IN_TREND_CACHE_TTL = 90

IN_TREND_MAX = 6
FOR_YOU_MAX = 5
TOPICS_MAX = 8
LATEST_MAX = 10


def _in_trend_cache_key(home: HomePageContent) -> str:
    lim = min(IN_TREND_MAX, home.content_strip_limit)
    return f"pages.home.in_trend_pks:{home.cache_bump}:{lim}"


def _quicklinks_cache_key(cache_bump: int) -> str:
    return f"pages.home.quicklinks:{cache_bump}"


def _fetch_in_trend_pks(home: HomePageContent) -> List[int]:
    lim = min(IN_TREND_MAX, home.content_strip_limit)
    return list(
        TrendingItem.objects.filter(item__is_published=True)
        .order_by("-trend_score")
        .values_list("item_id", flat=True)[:lim]
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


def _ordered_editor_picks(home: HomePageContent) -> List[Item]:
    if not home.show_editor_picks:
        return []
    id_order = [
        pk
        for pk in (
            home.editor_pick_1_id,
            home.editor_pick_2_id,
            home.editor_pick_3_id,
        )
        if pk
    ]
    if not id_order:
        return []
    qs = feed_list_optimizations(
        Item.objects.filter(pk__in=id_order, is_published=True).with_counters()
    )
    by_id = {i.pk: i for i in qs}
    return [by_id[i] for i in id_order if i in by_id]


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


def _load_latest_posts(home: HomePageContent) -> List[Item]:
    if not home.show_latest_brainews:
        return []
    qs = feed_list_optimizations(
        Item.objects.filter(is_published=True)
        .with_counters()
        .order_by("-published_date", "-pk")
    )
    return list(qs[:LATEST_MAX])


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

    editor_picks = _ordered_editor_picks(home)

    for_you_posts: List[Item] = []
    if home.show_for_you_section:
        if request is not None and request.user.is_authenticated:
            for_you_posts = for_you_home_preview(request.user, limit=FOR_YOU_MAX)

    top_categories: List[Any] = []
    if home.show_explore_topics:
        top_categories = _top_categories_slice()

    latest_posts = _load_latest_posts(home)

    has_any_posts = Item.objects.filter(is_published=True).exists()

    return {
        "home": home,
        "meta_description": home.meta_description or "",
        "quick_links": quick_links,
        "strip_items": [],
        "strip_heading": "",
        "show_content_strip": False,
        "editor_picks": editor_picks,
        # New homepage
        "hero_item": hero_item,
        "in_trend_items": in_trend_grid,
        "for_you_posts": for_you_posts,
        "top_categories": top_categories,
        "latest_posts": latest_posts,
        "has_any_posts": has_any_posts,
    }
