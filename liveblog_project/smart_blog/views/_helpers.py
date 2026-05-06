"""Shared helpers used across multiple view modules."""
from django.db.models import Exists, OuterRef

from smart_blog.feed_queryset import feed_list_optimizations
from smart_blog.models import Bookmark, Item, Like


def annotate_user_liked(qs, user):
    if user.is_authenticated:
        likes_subq = Like.objects.filter(item=OuterRef('pk'), user=user)
        return qs.annotate(user_liked=Exists(likes_subq))
    return qs


def annotate_user_bookmarked(qs, user):
    if user.is_authenticated:
        bookmarks_subq = Bookmark.objects.filter(item=OuterRef('pk'), user=user)
        return qs.annotate(user_bookmarked=Exists(bookmarks_subq))
    return qs


def annotate_feed_page_items(user, page_obj):
    """Re-fetch current page items with counters + user liked/bookmarked flags (feed listings)."""
    pks = [obj.pk for obj in page_obj.object_list]
    if not pks:
        return []
    qs = feed_list_optimizations(
        Item.objects.filter(pk__in=pks)
        .with_counters()
        .select_related("category", "author", "author__profile")
    )
    qs = annotate_user_liked(qs, user)
    qs = annotate_user_bookmarked(qs, user)
    by_pk = {obj.pk: obj for obj in qs}
    return [by_pk[pk] for pk in pks if pk in by_pk]
