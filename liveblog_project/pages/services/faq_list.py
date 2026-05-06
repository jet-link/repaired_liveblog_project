"""Public FAQ list (active only), cached."""
from __future__ import annotations

from typing import List

from django.core.cache import cache

from pages.models import FAQItem

FAQ_CACHE_KEY = "pages:faq:active:v1"
FAQ_CACHE_TTL = 300


def get_public_faq_items() -> List[FAQItem]:
    items = cache.get(FAQ_CACHE_KEY)
    if items is not None:
        return items
    items = list(FAQItem.objects.filter(is_active=True).order_by("order", "pk"))
    cache.set(FAQ_CACHE_KEY, items, FAQ_CACHE_TTL)
    return items


def invalidate_faq_cache() -> None:
    cache.delete(FAQ_CACHE_KEY)
