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


def mindset_theme_annotation(theme, *, max_len=100):
    """Plain snippet of theme body for notification body (target ~70–100 chars)."""
    if theme is None:
        return ""
    text = (getattr(theme, "body_text", None) or "").strip()
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def notify_mindset_theme_reply(*, theme, reply):
    """Notify theme author when someone posts a reply on their theme."""
    from smart_blog.context_processors import invalidate_notifications_cache

    if theme.author_id == reply.author_id:
        return None
    n = Notification.objects.create(
        recipient_id=theme.author_id,
        actor_id=reply.author_id,
        notif_type=Notification.TYPE_MINDSET_THEME_REPLY,
        mindset_theme=theme,
        mindset_reply=reply,
    )
    invalidate_notifications_cache(theme.author_id)
    return n


def notify_or_bump_mindset_theme_repost(*, theme, actor_user):
    """Notify theme author when someone reposts their theme (dedupe/bump like item likes)."""
    from smart_blog.context_processors import invalidate_notifications_cache

    if theme.author_id == actor_user.id:
        return None
    qs = Notification.objects.filter(
        recipient_id=theme.author_id,
        actor_id=actor_user.id,
        notif_type=Notification.TYPE_MINDSET_THEME_REPOST,
        mindset_theme=theme,
    )
    row = qs.order_by("-created_at").first()
    if row:
        _bump_notification(row.pk)
        invalidate_notifications_cache(theme.author_id)
        return row
    n = Notification.objects.create(
        recipient_id=theme.author_id,
        actor_id=actor_user.id,
        notif_type=Notification.TYPE_MINDSET_THEME_REPOST,
        mindset_theme=theme,
    )
    invalidate_notifications_cache(theme.author_id)
    return n
