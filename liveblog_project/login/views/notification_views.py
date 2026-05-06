"""Notification views: list, mark read, delete, check target."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from smart_blog.models import Notification
from smart_blog.utils import strip_mention_tokens


@login_required
def notifications_view(request, username):
    if request.user.username != username and not request.user.is_staff:
        raise PermissionDenied

    invalid_q = (
        Q(item__isnull=True) & ~Q(notif_type=Notification.TYPE_FROM_ADMIN)
        | Q(notif_type=Notification.TYPE_REPLY, reply_comment__isnull=True)
        | Q(notif_type=Notification.TYPE_REPLY, parent_comment__isnull=True)
        | Q(notif_type=Notification.TYPE_COMMENT_LIKE, parent_comment__isnull=True, reply_comment__isnull=True)
    )
    Notification.objects.filter(recipient=request.user).filter(invalid_q).delete()

    notifications = (
        Notification.objects
        .filter(recipient=request.user, cleared_from_inbox=False)
        .filter(Q(item__isnull=False) | Q(notif_type=Notification.TYPE_FROM_ADMIN))
        .exclude(
            Q(notif_type=Notification.TYPE_REPLY, reply_comment__isnull=True)
            | Q(notif_type=Notification.TYPE_REPLY, parent_comment__isnull=True)
            | Q(notif_type=Notification.TYPE_COMMENT_LIKE, parent_comment__isnull=True, reply_comment__isnull=True)
        )
        .select_related("item", "actor", "reply_comment", "parent_comment", "reply_comment__author")
        .order_by("-created_at")
    )
    for notif in notifications:
        notif.actor_name = getattr(notif.actor, "username", "")
        if notif.notif_type == Notification.TYPE_FROM_ADMIN:
            notif.body_text = (notif.admin_body or "").strip()
        elif notif.notif_type == Notification.TYPE_REPLY:
            notif.header_text = "replied comment in post"
            notif.body_text = strip_mention_tokens(getattr(notif.reply_comment, "text", ""))
        elif notif.notif_type == Notification.TYPE_COMMENT_LIKE:
            notif.header_text = "liked comment in post"
            liked_comment = notif.parent_comment or notif.reply_comment
            notif.body_text = strip_mention_tokens(getattr(liked_comment, "text", ""))
        else:
            notif.header_text = "liked post"
            notif.body_text = ""
    unread_count = notifications.filter(is_read=False).count()
    return render(request, "accounts/notifications.html", {
        "notifications": notifications,
        "unread_count": unread_count,
    })


def _invalidate_cache(user_pk):
    from smart_blog.context_processors import invalidate_notifications_cache
    invalidate_notifications_cache(user_pk)


@login_required
@require_POST
def mark_notification_read(request):
    notif_id = request.POST.get("notification_id")
    try:
        notif_id = int(notif_id)
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "error": "Invalid id."}, status=400)

    notif = get_object_or_404(Notification, pk=notif_id, recipient=request.user)
    notif.is_read = True
    notif.save(update_fields=["is_read"])
    _invalidate_cache(request.user.pk)
    return JsonResponse({"success": True})


@login_required
@require_POST
def mark_all_notifications_read(request):
    Notification.objects.filter(
        recipient=request.user, is_read=False, cleared_from_inbox=False,
    ).update(is_read=True)
    _invalidate_cache(request.user.pk)
    return JsonResponse({"success": True})


@login_required
@require_POST
def delete_notifications(request):
    mode = request.POST.get("mode")
    qs = Notification.objects.filter(recipient=request.user, cleared_from_inbox=False)
    if mode == "last5":
        ids = list(qs.order_by("-created_at").values_list("id", flat=True)[:5])
        Notification.objects.filter(id__in=ids).update(cleared_from_inbox=True)
    else:
        qs.update(cleared_from_inbox=True)
    _invalidate_cache(request.user.pk)
    return JsonResponse({"success": True})


@login_required
@require_POST
def check_notification_target(request):
    """Check whether a notification's target (post/comment) still exists."""
    notif_id = request.POST.get("notification_id")
    try:
        notif_id = int(notif_id)
    except (TypeError, ValueError):
        return JsonResponse({"exists": False})

    try:
        notif = Notification.objects.select_related(
            "item", "parent_comment", "reply_comment",
        ).get(pk=notif_id, recipient=request.user)
    except Notification.DoesNotExist:
        return JsonResponse({"exists": False})

    if notif.notif_type == Notification.TYPE_FROM_ADMIN:
        return JsonResponse({"exists": True})

    if not notif.item_id:
        return JsonResponse({"exists": False})

    return JsonResponse({"exists": True})
