"""Singleton About / Contacts: model instances for editing; cached copy for public templates."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict

from django.core.cache import cache
from django.forms.models import model_to_dict

from pages.defaults_static_pages import ABOUT_DEFAULTS, CONTACTS_DEFAULTS
from pages.models import AboutPageContent, ContactsPageContent

CACHE_KEY_ABOUT = "pages:static:about:v1"
CACHE_KEY_CONTACTS = "pages:static:contacts:v1"
STATIC_PAGE_CACHE_TTL = 600


def get_about_page_instance() -> AboutPageContent:
    """ORM row for admin saves and migrations — not cached."""
    obj, _ = AboutPageContent.objects.get_or_create(pk=1, defaults=ABOUT_DEFAULTS)
    return obj


def get_contacts_page_instance() -> ContactsPageContent:
    obj, _ = ContactsPageContent.objects.get_or_create(pk=1, defaults=CONTACTS_DEFAULTS)
    return obj


def get_about_page_for_public() -> SimpleNamespace:
    """Cached read-mostly payload for PageView (invalidated on save)."""
    cached = cache.get(CACHE_KEY_ABOUT)
    if cached is not None:
        return SimpleNamespace(**cached)
    obj = get_about_page_instance()
    data: Dict[str, Any] = model_to_dict(obj)
    cache.set(CACHE_KEY_ABOUT, data, STATIC_PAGE_CACHE_TTL)
    return SimpleNamespace(**data)


def get_contacts_page_for_public() -> SimpleNamespace:
    cached = cache.get(CACHE_KEY_CONTACTS)
    if cached is not None:
        return SimpleNamespace(**cached)
    obj = get_contacts_page_instance()
    data = model_to_dict(obj)
    cache.set(CACHE_KEY_CONTACTS, data, STATIC_PAGE_CACHE_TTL)
    return SimpleNamespace(**data)


def invalidate_about_cache() -> None:
    cache.delete(CACHE_KEY_ABOUT)


def invalidate_contacts_cache() -> None:
    cache.delete(CACHE_KEY_CONTACTS)
