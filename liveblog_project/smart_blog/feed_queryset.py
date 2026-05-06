"""Lightweight queryset tweaks for feed-style listings (no views package imports)."""
from django.db.models import Exists, OuterRef, Prefetch


def feed_list_optimizations(qs):
    """
    Listing cards: defer content_json; prefetch images/videos for feed card thumbnails;
    annotate has_photos/has_videos for media hints.
    """
    from smart_blog.models import ItemImage, ItemVideo
    img_qs = ItemImage.objects.order_by("sort_order", "pk")
    vid_qs = ItemVideo.objects.order_by("sort_order", "pk")
    return (
        qs
        .defer("content_json")
        .prefetch_related(
            Prefetch("images", queryset=img_qs),
            Prefetch("videos", queryset=vid_qs),
        )
        .annotate(
            has_photos=Exists(ItemImage.objects.filter(item=OuterRef("pk"))),
            has_videos=Exists(ItemVideo.objects.filter(item=OuterRef("pk"))),
        )
    )
