"""Sitemap URL counts and health checks (aligned with smart_blog.sitemaps)."""
from smart_blog.models import Item
from smart_blog.sitemaps import (
    StaticAndListSitemap,
    categories_for_sitemap,
    published_posts_queryset,
    tags_for_sitemap,
)


def get_sitemap_summary():
    """
    Segment counts matching public sitemap.xml index sections.
    Total = static/list + posts + topic pages + category list pages + tag pages.
    """
    static_n = len(StaticAndListSitemap().items())
    posts_qs = published_posts_queryset()
    posts_n = posts_qs.count()
    cat_n = categories_for_sitemap().count()
    tags_n = tags_for_sitemap().count()
    topics_n = cat_n
    category_lists_n = cat_n

    total_urls = static_n + posts_n + topics_n + category_lists_n + tags_n

    published_in_sitemap = posts_n
    published_live = Item.objects.filter(is_published=True).count()
    drafts = Item.objects.filter(is_published=False).count()
    trashed = Item.all_objects.filter(deleted_at__isnull=False).count()

    counts_match = published_in_sitemap == published_live

    return {
        "static_and_list": static_n,
        "posts": posts_n,
        "topics": topics_n,
        "category_lists": category_lists_n,
        "tags": tags_n,
        "total_urls": total_urls,
        "published_in_sitemap": published_in_sitemap,
        "published_live": published_live,
        "drafts": drafts,
        "trashed_posts": trashed,
        "counts_match": counts_match,
    }
