"""Invalidate public listing caches (brainstorm.news home/anon pages, Topics, trending API)."""
from __future__ import annotations

from django.core.cache import cache

# Must match historical key in views_topics._get_topics_data
TOPICS_LIST_CACHE_KEY = "topics_list_data"

ANON_BRAINEWS_VER_KEY = "public:anon_brainews_ver"


def get_anon_brainews_cache_version() -> int:
    v = cache.get(ANON_BRAINEWS_VER_KEY)
    if v is None:
        return 0
    return int(v)


def bump_anon_brainews_cache_version() -> None:
    cache.set(ANON_BRAINEWS_VER_KEY, get_anon_brainews_cache_version() + 1, None)


def invalidate_public_listing_caches(*, bump_home: bool = True) -> None:
    """Drop cached snapshots that can hide admin deletes/restores from public pages.

    The ``bump_home`` kwarg is kept for backward compat with existing callers; the dedicated
    HomePageContent cache_bump was removed alongside the HomePageContent model.
    """
    del bump_home  # kept for signature compatibility
    bump_anon_brainews_cache_version()
    cache.delete(TOPICS_LIST_CACHE_KEY)
    from smart_blog.services.trending_service import TRENDING_API_CACHE_KEY

    cache.delete(TRENDING_API_CACHE_KEY)
