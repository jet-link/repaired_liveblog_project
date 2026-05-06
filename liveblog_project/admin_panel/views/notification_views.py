"""Admin: all user notifications (moderation)."""
import json

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from admin_panel.decorators import admin_required
from admin_panel.views.bulk_views import _get_ids, _redirect_with_qs
from smart_blog.context_processors import invalidate_notifications_cache
from smart_blog.models import Notification

User = get_user_model()
USER_SEARCH_PAGE_SIZE = 30

# GET ?nf= — list filter (preserved in pagination / bulk redirects)
NOTIF_FILTER_ACTIVE = "active"
NOTIF_FILTER_CLEARED = "cleared"
NOTIF_FILTER_ADMIN = "admin"


@admin_required
def notifications_list(request):
    """
    - Active only: recipient still has row in inbox sense AND not hidden by admin
      (cleared_from_inbox=False, hidden_from_admin=False). No «Cleared inbox» badge
      in this set (badge only when user cleared but not read — see template).
    - Show cleared: user cleared inbox (cleared_from_inbox) OR admin hid row (hidden_from_admin).
    """
    qs = Notification.objects.select_related(
        "recipient", "actor", "item", "parent_comment", "reply_comment"
    )

    list_filter = request.GET.get("nf", NOTIF_FILTER_ACTIVE)
    if list_filter not in (NOTIF_FILTER_ACTIVE, NOTIF_FILTER_CLEARED, NOTIF_FILTER_ADMIN):
        list_filter = NOTIF_FILTER_ACTIVE

    if list_filter == NOTIF_FILTER_CLEARED:
        qs = qs.filter(Q(cleared_from_inbox=True) | Q(hidden_from_admin=True))
    elif list_filter == NOTIF_FILTER_ADMIN:
        qs = qs.filter(
            notif_type=Notification.TYPE_FROM_ADMIN,
            cleared_from_inbox=False,
            hidden_from_admin=False,
        )
    else:
        qs = qs.filter(cleared_from_inbox=False, hidden_from_admin=False)

    qs = qs.order_by("-created_at")
    search = request.GET.get("q", "").strip()
    if search:
        qs = qs.filter(
            Q(recipient__username__icontains=search)
            | Q(actor__username__icontains=search)
            | Q(item__title__icontains=search)
            | Q(admin_theme__icontains=search)
            | Q(admin_body__icontains=search)
        )
    paginator = Paginator(qs, 30)
    page = request.GET.get("page", 1)
    rows = paginator.get_page(page)
    return render(
        request,
        "admin/moderation/notifications_list.html",
        {
            "rows": rows,
            "search": search,
            "notif_list_filter": list_filter,
            "NOTIF_FILTER_ACTIVE": NOTIF_FILTER_ACTIVE,
            "NOTIF_FILTER_CLEARED": NOTIF_FILTER_CLEARED,
            "NOTIF_FILTER_ADMIN": NOTIF_FILTER_ADMIN,
        },
    )


@admin_required
def notifications_bulk_clear(request):
    """Hide selected rows from the admin list only (hidden_from_admin=True); DB rows stay; inbox unchanged."""
    if request.method != "POST":
        return redirect("admin_panel:notifications_list")
    ids = _get_ids(request)
    valid = []
    for x in ids:
        try:
            valid.append(int(x))
        except (TypeError, ValueError):
            pass
    if valid:
        updated = Notification.objects.filter(pk__in=valid).update(hidden_from_admin=True)
        if updated:
            messages.success(
                request,
                f"{updated} notification(s) removed from the admin table (still in database).",
            )
        else:
            messages.info(request, "No matching rows were updated.")
    else:
        messages.warning(request, "Select at least one notification to clear.")
    return _redirect_with_qs("notifications_list", request)


@admin_required
def notifications_bulk_delete(request):
    """Permanently delete selected notification rows."""
    if request.method != "POST":
        return redirect("admin_panel:notifications_list")
    ids = _get_ids(request)
    valid = []
    for x in ids:
        try:
            valid.append(int(x))
        except (TypeError, ValueError):
            pass
    if valid:
        to_clear = list(
            Notification.objects.filter(pk__in=valid).values_list("recipient_id", flat=True)
        )
        n, _ = Notification.objects.filter(pk__in=valid).delete()
        for uid in set(to_clear):
            invalidate_notifications_cache(uid)
        messages.success(request, f"{n} notification row(s) removed from database.")
    else:
        messages.warning(request, "Select at least one notification to delete.")
    return _redirect_with_qs("notifications_list", request)


@admin_required
@require_GET
def notification_from_admin_detail(request, pk):
    """JSON: theme, body, recipient for a from_admin notification (view modal in admin list)."""
    n = get_object_or_404(
        Notification.objects.select_related("recipient"),
        pk=pk,
        notif_type=Notification.TYPE_FROM_ADMIN,
    )
    return JsonResponse(
        {
            "theme": n.admin_theme or "",
            "body": n.admin_body or "",
            "recipient": n.recipient.username,
        }
    )


@admin_required
@require_GET
def notification_user_search(request):
    """Typeahead: users by username (for manual notification form)."""
    q = (request.GET.get("q") or "").strip()
    if len(q) < 1:
        return JsonResponse({"results": []})
    qs = (
        User.objects.filter(username__icontains=q)
        .order_by("username")
        .values("id", "username")[:USER_SEARCH_PAGE_SIZE]
    )
    return JsonResponse({"results": list(qs)})


@admin_required
@require_POST
def notification_send_manual(request):
    """Create a from_admin notification for a single user."""
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return HttpResponseBadRequest("Invalid JSON")
    try:
        user_id = int(data.get("user_id"))
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "error": "Invalid user id."}, status=400)
    theme = (data.get("theme") or "").strip()[:200]
    body = (data.get("body") or "").strip()
    if not body:
        return JsonResponse({"success": False, "error": "Notification body is required."}, status=400)

    user = get_object_or_404(User, pk=user_id)
    n = Notification.objects.create(
        recipient=user,
        actor=request.user,
        notif_type=Notification.TYPE_FROM_ADMIN,
        item=None,
        parent_comment=None,
        reply_comment=None,
        admin_theme=theme,
        admin_body=body,
    )
    invalidate_notifications_cache(user.pk)
    return JsonResponse({"success": True, "id": n.pk})
