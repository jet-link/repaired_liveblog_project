"""Human-readable sitemap: shared link trees cached; request-only URLs added in the view."""
from __future__ import annotations

from typing import Any, Dict, List

from django.contrib.sites.models import Site
from django.core.cache import cache
from django.urls import reverse

from smart_blog.models import Category, Item, Tag
from smart_blog.sitemaps import (
    categories_for_sitemap,
    published_posts_queryset,
    static_sitemap_entries,
    tags_for_sitemap_html,
)

SITEMAP_HTML_CACHE_KEY = "pages:sitemap:html:v3"
SITEMAP_HTML_TTL = 300


def _build_sitemap_cached_payload() -> Dict[str, Any]:
    static_links = []
    for label, url_name, kwargs in static_sitemap_entries():
        path = reverse(url_name, kwargs=kwargs) if kwargs else reverse(url_name)
        static_links.append({"label": label, "url": path})

    categories: List[Category] = list(categories_for_sitemap())
    topic_links = [
        {"label": c.name, "url": reverse("smart_blog:topic_detail", kwargs={"slug": c.slug})}
        for c in categories
    ]
    category_links = [
        {"label": c.name, "url": reverse("smart_blog:category_list", kwargs={"slug": c.slug})}
        for c in categories
    ]
    tags: List[Tag] = list(tags_for_sitemap_html())
    tag_links = [
        {"label": t.tag_name, "url": reverse("smart_blog:tag_list", kwargs={"slug": t.slug})}
        for t in tags
    ]

    recent_items = list(
        published_posts_queryset().only("title", "slug", "pk")[:40]
    )
    recent_links = [{"label": item.title, "url": item.get_absolute_url()} for item in recent_items]

    site = Site.objects.get_current()

    return {
        "static_links": static_links,
        "topic_links": topic_links,
        "category_links": category_links,
        "tag_links": tag_links,
        "recent_links": recent_links,
        "recent_total_shown": len(recent_links),
        "site_domain": site.domain,
        "site_name": site.name,
    }


def build_sitemap_page_context(request) -> Dict[str, Any]:
    data = cache.get(SITEMAP_HTML_CACHE_KEY)
    if data is None:
        data = _build_sitemap_cached_payload()
        cache.set(SITEMAP_HTML_CACHE_KEY, data, SITEMAP_HTML_TTL)
    topic_links = []
    for row in data["topic_links"]:
        base = row["url"]
        sep = "&" if "?" in base else "?"
        topic_links.append({**row, "url": f"{base}{sep}from=sitemap"})
    return {
        **data,
        "topic_links": topic_links,
        "sitemap_xml_url": request.build_absolute_uri(reverse("sitemap_index")),
        "robots_url": request.build_absolute_uri(reverse("robots_txt")),
    }


def invalidate_sitemap_html_cache() -> None:
    cache.delete(SITEMAP_HTML_CACHE_KEY)
