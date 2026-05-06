"""Public XML sitemaps (django.contrib.sitemaps)."""
from __future__ import annotations

from typing import Optional

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from smart_blog.models import Category, Item, Tag

# Human HTML sitemap: only the N most recently created tags (newest first); XML sitemap lists all tags.
SITEMAP_HTML_TAGS_LIMIT = 50

# Whitelist: only slugs backed by templates (see pages.views.PageView).
PAGE_SLUGS_FOR_SITEMAP = ("about", "contacts")

# Human-readable labels for HTML sitemap & admin (single source with XML static section).
_PAGE_SLUG_LABELS = {"about": "About", "contacts": "Contacts"}


def static_sitemap_entries():
    """
    Shared list for StaticAndListSitemap and the public HTML sitemap page.
    Each item: (label, url_name, kwargs) — kwargs is None when empty.
    """
    entries = [
        ("Home", "pages:home", None),
        ("FAQ", "pages:faq", None),
        ("BraiNews", "smart_blog:items_list", None),
        ("In trend", "smart_blog:trending_list", None),
        ("Topics", "smart_blog:topics_list", None),
        ("Sitemap", "pages:sitemap_page", None),
    ]
    for slug in PAGE_SLUGS_FOR_SITEMAP:
        entries.append(
            (_PAGE_SLUG_LABELS.get(slug, slug.replace("-", " ").title()), "pages:page", {"slug": slug})
        )
    return entries


# Display names for PUBLIC_SITEMAPS keys (admin analytics & docs).
SITEMAP_SECTION_LABELS = {
    "static": "Static & listings",
    "posts": "Published posts",
    "topics": "Topic hubs",
    "categories": "Category post lists",
    "tags": "Tag pages",
}


def published_posts_queryset():
    """Posts included in sitemap: published, not soft-deleted."""
    return Item.objects.filter(is_published=True).order_by("-updated", "-pk")


def categories_for_sitemap():
    """Active categories (not soft-deleted)."""
    return Category.objects.all().order_by("slug")


def tags_for_sitemap():
    """Active tags (not soft-deleted)."""
    return Tag.objects.all().order_by("slug")


def tags_for_sitemap_html(limit: Optional[int] = None):
    """
    Tags shown on the public /sitemap/ page only: last `limit` tags by primary key (newest first).
    Older tags are omitted from the HTML list; XML sitemap still uses tags_for_sitemap().
    """
    lim = int(limit) if limit is not None else SITEMAP_HTML_TAGS_LIMIT
    return Tag.objects.order_by("-pk")[:lim]


class StaticAndListSitemap(Sitemap):
    """Home, FAQ, static pages, and main blog listing URLs."""

    changefreq = "daily"
    priority = 0.9

    def items(self):
        return [(name, kwargs) for _label, name, kwargs in static_sitemap_entries()]

    def location(self, obj):
        name, kwargs = obj
        if kwargs:
            return reverse(name, kwargs=kwargs)
        return reverse(name)


class PostSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return published_posts_queryset()

    def lastmod(self, obj):
        return obj.updated or obj.published_date


class TopicSitemap(Sitemap):
    """Category topic hub: /topics/<slug>/."""

    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return categories_for_sitemap()

    def location(self, obj):
        return reverse("smart_blog:topic_detail", kwargs={"slug": obj.slug})


class CategoryListSitemap(Sitemap):
    """Posts filtered by category legacy URL: /blog/brainews/category/<slug>/ (→ topic)."""

    changefreq = "weekly"
    priority = 0.65

    def items(self):
        return categories_for_sitemap()

    def location(self, obj):
        return reverse("smart_blog:category_list", kwargs={"slug": obj.slug})


class TagSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.65

    def items(self):
        return tags_for_sitemap()

    def location(self, obj):
        return reverse("smart_blog:tag_list", kwargs={"slug": obj.slug})


PUBLIC_SITEMAPS = {
    "static": StaticAndListSitemap,
    "posts": PostSitemap,
    "topics": TopicSitemap,
    "categories": CategoryListSitemap,
    "tags": TagSitemap,
}
