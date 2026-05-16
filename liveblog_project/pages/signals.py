from django.db.models.signals import m2m_changed, post_delete, post_save

from pages.models import AboutPageContent, ContactsPageContent, FAQItem
from pages.services.faq_list import invalidate_faq_cache
from pages.services.sitemap_html import invalidate_sitemap_html_cache
from pages.services.static_content import invalidate_about_cache, invalidate_contacts_cache

_sitemap_signals_connected = False


def about_saved(sender, instance, **kwargs):
    invalidate_about_cache()


def contacts_saved(sender, instance, **kwargs):
    invalidate_contacts_cache()


post_save.connect(about_saved, sender=AboutPageContent)
post_delete.connect(about_saved, sender=AboutPageContent)
post_save.connect(contacts_saved, sender=ContactsPageContent)
post_delete.connect(contacts_saved, sender=ContactsPageContent)


def faq_changed(sender, instance, **kwargs):
    invalidate_faq_cache()


post_save.connect(faq_changed, sender=FAQItem)
post_delete.connect(faq_changed, sender=FAQItem)


def _invalidate_sitemap_cache(**kwargs):
    invalidate_sitemap_html_cache()


def connect_sitemap_cache_invalidation():
    """Register once from AppConfig.ready (after all models load)."""
    global _sitemap_signals_connected
    if _sitemap_signals_connected:
        return
    from mindset.models import Theme
    from smart_blog.models import Category, Item, Tag

    for model in (Item, Category, Tag, Theme):
        post_save.connect(_invalidate_sitemap_cache, sender=model)
        post_delete.connect(_invalidate_sitemap_cache, sender=model)

    m2m_changed.connect(_invalidate_sitemap_cache, sender=Theme.hashtags.through)
    _sitemap_signals_connected = True
