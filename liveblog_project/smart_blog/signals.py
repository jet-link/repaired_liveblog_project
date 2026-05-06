"""Signals to keep Item.likes_count, views_count, bookmarks_count, search_vector in sync."""
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.db.models import F, Q
from django.db.models.functions import Greatest

from .models import Category, Like, Item, ItemView, Bookmark, PostRepost, Comment, Notification
from .public_listing_cache import invalidate_public_listing_caches
from .search_utils import schedule_search_vector_refresh
from smart_blog.services.trending_service import TRENDING_API_CACHE_KEY


def _drop_notifications_for_item(item_id):
    """Remove notifications tied to a post that is no longer visible to users."""
    if not item_id:
        return
    recipient_ids = list(
        Notification.objects.filter(item_id=item_id).values_list("recipient_id", flat=True)
    )
    deleted, _ = Notification.objects.filter(item_id=item_id).delete()
    if deleted:
        from smart_blog.context_processors import invalidate_notifications_cache
        for uid in set(recipient_ids):
            invalidate_notifications_cache(uid)


def _drop_notifications_for_comment(comment_id):
    """Remove notifications tied to a comment (as parent or reply) that is gone."""
    if not comment_id:
        return
    qs = Notification.objects.filter(
        Q(parent_comment_id=comment_id) | Q(reply_comment_id=comment_id)
    )
    recipient_ids = list(qs.values_list("recipient_id", flat=True))
    deleted, _ = qs.delete()
    if deleted:
        from smart_blog.context_processors import invalidate_notifications_cache
        for uid in set(recipient_ids):
            invalidate_notifications_cache(uid)


def _invalidate_trending_api_cache():
    cache.delete(TRENDING_API_CACHE_KEY)


@receiver(post_save, sender=Like)
def like_created(sender, instance, created, **kwargs):
    if created:
        Item.objects.filter(pk=instance.item_id).update(likes_count=F('likes_count') + 1)
        _invalidate_trending_api_cache()


@receiver(post_delete, sender=Like)
def like_deleted(sender, instance, **kwargs):
    Item.objects.filter(pk=instance.item_id).update(
        likes_count=Greatest(F('likes_count') - 1, 0)
    )
    _invalidate_trending_api_cache()


@receiver(post_save, sender=ItemView)
def itemview_created(sender, instance, created, **kwargs):
    if created and instance.user_id is not None:
        Item.objects.filter(pk=instance.item_id).update(views_count=F('views_count') + 1)


@receiver(post_delete, sender=ItemView)
def itemview_deleted(sender, instance, **kwargs):
    if instance.user_id is not None:
        Item.objects.filter(pk=instance.item_id).update(
            views_count=Greatest(F('views_count') - 1, 0)
        )


@receiver(post_save, sender=Bookmark)
def bookmark_created(sender, instance, created, **kwargs):
    if created:
        Item.objects.filter(pk=instance.item_id).update(bookmarks_count=F('bookmarks_count') + 1)
        _invalidate_trending_api_cache()


@receiver(post_delete, sender=Bookmark)
def bookmark_deleted(sender, instance, **kwargs):
    Item.objects.filter(pk=instance.item_id).update(
        bookmarks_count=Greatest(F('bookmarks_count') - 1, 0)
    )
    _invalidate_trending_api_cache()


@receiver(post_save, sender=PostRepost)
def repost_created(sender, instance, created, **kwargs):
    if created:
        Item.objects.filter(pk=instance.item_id).update(reposts_count=F('reposts_count') + 1)
        _invalidate_trending_api_cache()


@receiver(post_save, sender=Comment)
def comment_changed_trending_cache(sender, instance, **kwargs):
    _invalidate_trending_api_cache()
    if getattr(instance, "deleted_at", None) is not None:
        _drop_notifications_for_comment(instance.pk)


@receiver(post_delete, sender=Comment)
def comment_deleted_trending_cache(sender, instance, **kwargs):
    _invalidate_trending_api_cache()
    _drop_notifications_for_comment(instance.pk)


@receiver(post_save, sender=Item)
def item_soft_delete_drop_notifications(sender, instance, **kwargs):
    """When a post is soft-deleted (deleted_at set), drop related notifications."""
    if getattr(instance, "deleted_at", None) is not None:
        _drop_notifications_for_item(instance.pk)


_ITEM_LISTING_FIELDS = frozenset(
    {"is_published", "deleted_at", "category", "title", "text", "excerpt_plain"}
)


@receiver(post_save, sender=Item)
def item_public_listing_cache_sync(sender, instance, created, **kwargs):
    """BraiNews / Topics / trending / home strips stay in sync after admin edits."""
    update_fields = kwargs.get("update_fields")
    bump_home = True
    if created:
        invalidate_public_listing_caches(bump_home=True)
        return
    if update_fields is not None:
        if not (_ITEM_LISTING_FIELDS & set(update_fields)):
            return
        if set(update_fields) <= {"category"}:
            bump_home = False
    invalidate_public_listing_caches(bump_home=bump_home)


@receiver(post_delete, sender=Item)
def item_deleted_public_listing_cache(sender, instance, **kwargs):
    invalidate_public_listing_caches(bump_home=True)


@receiver(post_save, sender=Category)
def category_public_listing_cache_sync(sender, instance, **kwargs):
    invalidate_public_listing_caches(bump_home=False)


@receiver(post_delete, sender=Category)
def category_deleted_public_listing_cache(sender, instance, **kwargs):
    invalidate_public_listing_caches(bump_home=False)


@receiver(post_save, sender=Item)
def item_search_vector_sync(sender, instance, **kwargs):
    """Ensure search_vector is populated so new/updated posts appear in search immediately."""
    if not instance.pk:
        return
    update_fields = kwargs.get("update_fields")
    if update_fields is not None and not ({'title', 'text'} & set(update_fields)):
        return
    schedule_search_vector_refresh(instance.pk)


@receiver(m2m_changed, sender=Item.tags.through)
def item_tags_search_vector_sync(sender, instance, action, **kwargs):
    """Refresh search_vector when tags are added/removed (M2M changes after initial save)."""
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return
    item_id = getattr(instance, 'item_id', None) or getattr(instance, 'pk', None)
    if item_id:
        schedule_search_vector_refresh(item_id)
