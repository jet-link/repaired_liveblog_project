"""Personalized recommendations for the For You feed (signed-in users).

Scored by liked/bookmarked/viewed categories and tags.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from smart_blog.models import Bookmark, Item, ItemView, Like, TrendingItem
from smart_blog.feed_queryset import feed_list_optimizations

FORYOU_CACHE_TTL = 300

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


CANDIDATE_DAYS = 90
FRESH_DAYS = 7
MAX_POOL = 800
MAX_CONSECUTIVE_SAME_CATEGORY = 3


def _base_item_filter(since):
    return (
        Item.objects.filter(is_published=True, published_date__gte=since)
        .filter(Q(author__isnull=True) | Q(author__is_active=True))
        .exclude(author__profile__trust_banned=True)
    )


def _tag_ids_for_item_ids(item_ids):
    if not item_ids:
        return set()
    through = Item.tags.through
    return set(through.objects.filter(item_id__in=item_ids).values_list("tag_id", flat=True))


def _collect_interest_sets(user):
    liked_item_ids = set(Like.objects.filter(user=user).values_list("item_id", flat=True))
    liked_cat = set(
        c for c in Like.objects.filter(user=user).values_list("item__category_id", flat=True) if c
    )
    liked_tags = _tag_ids_for_item_ids(liked_item_ids)

    bm_item_ids = set(Bookmark.objects.filter(user=user).values_list("item_id", flat=True))
    bm_cat = set(
        c for c in Bookmark.objects.filter(user=user).values_list("item__category_id", flat=True) if c
    )
    bm_tags = _tag_ids_for_item_ids(bm_item_ids)

    viewed_cat = set(
        c for c in ItemView.objects.filter(user=user).values_list("item__category_id", flat=True) if c
    )
    viewed_item_ids = set(ItemView.objects.filter(user=user).values_list("item_id", flat=True))
    viewed_tags = _tag_ids_for_item_ids(viewed_item_ids)

    return liked_cat, liked_tags, bm_cat, bm_tags, viewed_cat, viewed_tags


def score_item_for_user(
    item, *,
    liked_cat, liked_tags, bm_cat, bm_tags,
    viewed_cat, viewed_tags,
    trending_ids, read_ids, now,
):
    s = 0
    cid = item.category_id

    if cid and cid in liked_cat:
        s += 3
    if cid and cid in bm_cat:
        s += 3
    if cid and cid in viewed_cat:
        s += 1

    item_tag_ids = {t.pk for t in item.tags.all()}
    interest_tags = liked_tags | bm_tags
    if item_tag_ids and (item_tag_ids & interest_tags):
        s += 2
    if item_tag_ids and (item_tag_ids & viewed_tags):
        s += 1

    if item.pk in trending_ids:
        s += 2

    if (now - item.published_date) <= timedelta(days=FRESH_DAYS):
        s += 1

    if item.pk in read_ids:
        s -= 2

    return s


@dataclass
class ForYouResult:
    items: list
    low_personal_signal: bool


def _apply_category_diversity(scored_items):
    """Reorder so no more than MAX_CONSECUTIVE_SAME_CATEGORY items from the same category appear consecutively."""
    if not scored_items:
        return scored_items

    result = []
    remaining = list(scored_items)

    while remaining:
        placed = False
        for i, item in enumerate(remaining):
            cat_id = item.category_id
            recent_cats = [r.category_id for r in result[-MAX_CONSECUTIVE_SAME_CATEGORY:]]
            if len(recent_cats) < MAX_CONSECUTIVE_SAME_CATEGORY or not all(c == cat_id for c in recent_cats):
                result.append(remaining.pop(i))
                placed = True
                break

        if not placed:
            result.append(remaining.pop(0))

    return result


def _compute_for_you(user):
    """Heavy scoring computation — result is cached per user."""
    now = timezone.now()
    since = now - timedelta(days=CANDIDATE_DAYS)
    liked_cat, liked_tags, bm_cat, bm_tags, viewed_cat, viewed_tags = _collect_interest_sets(user)
    trending_ids = set(TrendingItem.objects.values_list("item_id", flat=True))
    read_ids = set(ItemView.objects.filter(user=user).values_list("item_id", flat=True))

    has_interaction = Like.objects.filter(user=user).exists() or Bookmark.objects.filter(
        user=user
    ).exists()

    qs = feed_list_optimizations(
        _base_item_filter(since)
        .select_related("category", "author", "author__profile")
        .prefetch_related("tags")
        .order_by("-published_date", "-pk")
    )

    pool = list(qs[:MAX_POOL])

    scored = []
    for item in pool:
        sc = score_item_for_user(
            item,
            liked_cat=liked_cat,
            liked_tags=liked_tags,
            bm_cat=bm_cat,
            bm_tags=bm_tags,
            viewed_cat=viewed_cat,
            viewed_tags=viewed_tags,
            trending_ids=trending_ids,
            read_ids=read_ids,
            now=now,
        )
        scored.append((sc, item))

    scored.sort(key=lambda x: (-x[0], -x[1].published_date.timestamp(), -x[1].pk))

    ordered_items = [it for _, it in scored]
    ordered_items = _apply_category_diversity(ordered_items)
    ordered_ids = [it.pk for it in ordered_items]

    top_score = scored[0][0] if scored else 0
    low_personal_signal = (not has_interaction) or (has_interaction and top_score < 2)

    return ordered_ids, low_personal_signal


def invalidate_foryou_cache(user_pk):
    cache.delete(f"foryou:{user_pk}")


def for_you_home_preview(user, limit: int = 5):
    """Return at most `limit` items for the home page (signed-in only). Uses the same ID cache as For You without hydrating the full list."""
    if not user.is_authenticated:
        return []
    cache_key = f"foryou:{user.pk}"
    cached = cache.get(cache_key)
    if cached is None:
        ordered_ids, low_personal_signal = _compute_for_you(user)
        cache.set(cache_key, (ordered_ids, low_personal_signal), FORYOU_CACHE_TTL)
    else:
        ordered_ids, _ = cached
    if not ordered_ids:
        return []
    take = ordered_ids[:limit]
    qs = feed_list_optimizations(
        Item.objects.filter(pk__in=take, is_published=True)
        .with_counters()
        .select_related("category", "author", "author__profile")
    )
    by_id = {it.pk: it for it in qs}
    return [by_id[pk] for pk in take if pk in by_id]


def for_you_items_for_authenticated_user(user: AbstractUser) -> ForYouResult:
    cache_key = f"foryou:{user.pk}"
    cached = cache.get(cache_key)
    if cached is not None:
        ordered_ids, low_personal_signal = cached
    else:
        ordered_ids, low_personal_signal = _compute_for_you(user)
        cache.set(cache_key, (ordered_ids, low_personal_signal), FORYOU_CACHE_TTL)

    if not ordered_ids:
        return ForYouResult(items=[], low_personal_signal=low_personal_signal)

    items_by_pk = {
        it.pk: it
        for it in feed_list_optimizations(
            Item.objects.filter(pk__in=ordered_ids, is_published=True)
            .select_related("category", "author", "author__profile")
        )
    }
    ordered = [items_by_pk[pk] for pk in ordered_ids if pk in items_by_pk]

    return ForYouResult(items=ordered, low_personal_signal=low_personal_signal)
