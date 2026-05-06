"""Signals for admin_panel: clear ContentViolation when edited content is no longer violating."""
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from smart_blog.models import Item, Comment

from admin_panel.models import ContentViolation
from admin_panel.services.content_analyzer import recheck_and_clear_violation_if_clean


@receiver(post_save, sender=Item)
def clear_violation_on_item_edit(sender, instance, **kwargs):
    """When Item (post) is saved, recheck and remove violation if content is now clean."""
    item_id = instance.pk

    def do_recheck():
        try:
            item = Item.objects.prefetch_related('tags', 'category').get(pk=item_id)
            recheck_and_clear_violation_if_clean(item=item)
        except Item.DoesNotExist:
            pass

    transaction.on_commit(do_recheck)


@receiver(post_save, sender=Comment)
def clear_violation_on_comment_edit(sender, instance, **kwargs):
    """When Comment is saved, recheck and remove violation if content is now clean."""
    comment_id = instance.pk

    def do_recheck():
        try:
            comment = Comment.objects.get(pk=comment_id)
            recheck_and_clear_violation_if_clean(comment=comment)
        except Comment.DoesNotExist:
            pass

    transaction.on_commit(do_recheck)


@receiver(post_delete, sender=ContentViolation)
def recalc_trust_on_violation_deleted(sender, instance, **kwargs):
    """When a ContentViolation is deleted, recalculate the author's trust score."""
    user = None
    if instance.snapshot_author_id:
        user = instance.snapshot_author
    if not user and instance.item_id:
        try:
            item = Item.objects.filter(pk=instance.item_id).select_related('author').first()
            if item:
                user = item.author
        except Exception:
            pass
    if not user and instance.comment_id:
        try:
            comment = Comment.objects.filter(pk=instance.comment_id).select_related('author').first()
            if comment:
                user = comment.author
        except Exception:
            pass
    if user:
        try:
            from admin_panel.services.trust_score_service import update_user_trust_score
            update_user_trust_score(user)
        except Exception:
            pass
