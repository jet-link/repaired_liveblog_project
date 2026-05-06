"""Shared helpers for login app views."""
import random
from collections import OrderedDict
from urllib.parse import urlparse, parse_qs

from django.urls import reverse, resolve, Resolver404
from django.utils.http import url_has_allowed_host_and_scheme

from smart_blog.models import Comment, Item, TrendingItem
from smart_blog.utils import count_convert, build_breadcrumbs, breadcrumb  # noqa: F401
from smart_blog.views._helpers import annotate_user_bookmarked, annotate_user_liked  # noqa: F401

FUNNY_NAMES = [
    "Bobby McWobble",
    "Lars von Pickle",
    "Giuseppe Spaghettini",
    "Hiroshi Banana",
    "Pierre Baguettino",
    "Olga Vodkanova",
    "Sven Snowbeard",
    "Carlos Jalapeno",
    "Nigel Wiggletop",
    "Fatima Moonshine",
    "Dmitri Thunderpants",
    "Ahmed Falafelson",
    "Hans Pretzelberg",
    "Juan Burritowski",
    "Luca Mozzarelli",
    "Ivan Gigglevich",
    "Akira Sushiroll",
    "Pedro Mangopez",
    "Tariq Sandstorm",
    "Bruno Pastaferro",
    "Yuki Bubbletea",
    "Boris Pickleman",
    "Ali Kebabzade",
    "Marco Pizzaio",
    "Satoshi Pixelman",
    "Enzo Raviolini",
    "Abdul Giggleton",
    "Diego Nachozilla",
    "Gustav Schnitzelmann",
    "Vladimir Chucklev",
]


def _random_vanished_name():
    """Return a random funny name for vanished user display."""
    return random.choice(FUNNY_NAMES)


def _safe_referer_url(request):
    """Return a validated referer URL or None."""
    referer = request.META.get("HTTP_REFERER")
    if referer and url_has_allowed_host_and_scheme(
        url=referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return referer
    return None


def _referer_breadcrumb_info(request, referer_url):
    """Return (title, url) for a breadcrumb based on HTTP referer."""
    fallback_url = reverse("smart_blog:items_list")
    if not referer_url:
        return "BraiNews", fallback_url

    parsed = urlparse(referer_url)
    path = parsed.path or "/"
    query = parse_qs(parsed.query)

    try:
        match = resolve(path)
        url_name = match.url_name or ""
        kwargs = match.kwargs or {}

        if url_name == "post_detail" and kwargs.get("slug"):
            item = Item.objects.filter(slug=kwargs["slug"]).values("title").first()
            if item:
                return item["title"], referer_url
        elif url_name == "tag_list" and kwargs.get("slug"):
            from smart_blog.models import Tag

            tag = Tag.objects.filter(slug=kwargs["slug"]).values("tag_name").first()
            if tag:
                return tag["tag_name"], referer_url
        elif url_name == "for_you_list":
            return "For you", referer_url
        elif url_name == "items_popular":
            return "Popular posts", referer_url
        elif url_name == "topics_list":
            return "Topics", referer_url
        elif url_name == "topic_detail" and kwargs.get("slug"):
            from smart_blog.models import Category

            cat = Category.objects.filter(slug=kwargs["slug"]).values("name").first()
            if cat:
                return cat["name"], referer_url
            return "Topics", referer_url
        elif url_name == "trending_list":
            return "In trend", referer_url
        elif url_name == "items_list":
            return "BraiNews", referer_url
        elif url_name == "global_search":
            q = (query.get("q") or [""])[0]
            return (f"Found - {q}" if q else "Search"), referer_url
        elif url_name == "profile" and kwargs.get("username"):
            return kwargs["username"], referer_url
        elif url_name == "profile-section" and kwargs.get("username"):
            sections = {"created": "Created", "liked": "Liked", "bookmarked": "Bookmarked"}
            section_title = sections.get(kwargs.get("section", ""), kwargs.get("section", "Section"))
            return f"{kwargs['username']} - {section_title}", referer_url
        elif url_name == "home":
            return "brainstorm.news", referer_url
        elif url_name == "comment_thread" and kwargs.get("pk"):
            qs = Comment.objects.filter(is_draft=False).select_related("item").filter(pk=kwargs["pk"])
            if kwargs.get("slug"):
                qs = qs.filter(item__slug=kwargs["slug"])
            comment = qs.values("item__title").first()
            if comment and comment.get("item__title"):
                return f"{comment['item__title']} - Replies", referer_url
            return "Replies", referer_url
    except Resolver404:
        pass

    return "BraiNews", referer_url


def build_profile_field(value, field_type, is_owner=False):
    is_empty = not value or not str(value).strip()
    return {
        "value": value if not is_empty else "not specified",
        "type": field_type,
        "is_owner": is_owner,
        "is_empty": is_empty,
    }


def build_trust_rating_field(score):
    s = float(score)
    if s >= 8:
        zone, zone_class = "Trusted", "badge_success"
    elif s >= 5:
        zone, zone_class = "Normal", "badge_muted"
    elif s >= 3:
        zone, zone_class = "Risk", "badge_warning"
    else:
        zone, zone_class = "Dangerous", "rating_badge_danger"
    return {
        "type": "trust_rating",
        "score": s,
        "zone": zone,
        "zone_class": zone_class,
        "is_empty": False,
    }


def apply_human_counts(items):
    """Attach human-readable count strings to a list of items."""
    for item in items:
        item.views_count_human = count_convert(item.views_count)
        item.likes_count_human = count_convert(item.likes_count)
        item.bookmarks_count_human = count_convert(item.bookmarks_count)
        item.comments_count_human = count_convert(item.comments_count)


def _vanished_items_qs():
    """Published items by deleted users (author=None)."""
    return (
        Item.objects
        .filter(is_published=True, author__isnull=True)
        .with_counters()
        .order_by("-published_date")
        .prefetch_related("images")
    )


def _trending_item_ids_for_items(items):
    """Item pk values that currently have a TrendingItem row (for In trend badge)."""
    ids = [i.pk for i in items if getattr(i, "pk", None)]
    if not ids:
        return []
    return list(
        TrendingItem.objects.filter(item_id__in=ids).values_list("item_id", flat=True)
    )
