"""Create/update notifications without stacking duplicate rows after inbox clear."""
from django.utils import timezone

from .models import Notification


def _bump_notification(notif_id):
    Notification.objects.filter(pk=notif_id).update(
        is_read=False,
        cleared_from_inbox=False,
        created_at=timezone.now(),
    )


def upsert_item_like_notification(*, recipient, actor, item):
    qs = Notification.objects.filter(
        recipient=recipient,
        actor=actor,
        notif_type=Notification.TYPE_ITEM_LIKE,
        item=item,
        parent_comment__isnull=True,
        reply_comment__isnull=True,
    )
    row = qs.order_by("-created_at").first()
    if row:
        _bump_notification(row.pk)
        return row
    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notif_type=Notification.TYPE_ITEM_LIKE,
        item=item,
    )


def upsert_comment_like_notification(*, recipient, actor, item, parent_comment=None, reply_comment=None):
    qs = Notification.objects.filter(
        recipient=recipient,
        actor=actor,
        notif_type=Notification.TYPE_COMMENT_LIKE,
        item=item,
        parent_comment=parent_comment,
        reply_comment=reply_comment,
    )
    row = qs.order_by("-created_at").first()
    if row:
        _bump_notification(row.pk)
        return row
    kwargs = {
        "recipient": recipient,
        "actor": actor,
        "notif_type": Notification.TYPE_COMMENT_LIKE,
        "item": item,
    }
    if parent_comment is not None:
        kwargs["parent_comment"] = parent_comment
    if reply_comment is not None:
        kwargs["reply_comment"] = reply_comment
    return Notification.objects.create(**kwargs)
