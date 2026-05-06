"""Report views: submit_report."""
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from smart_blog.models import Comment, ContentReport, Item
from smart_blog.services.report_limits import can_user_report
from smart_blog.services.reports import ReportService


@login_required
@require_POST
def submit_report(request):
    try:
        payload = request.POST
        if request.headers.get("Content-Type", "").startswith("application/json"):
            payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        payload = request.POST

    target_type = (payload.get("target_type") or "").strip()
    target_id = payload.get("target_id")
    reason = (payload.get("reason") or "").strip()
    reasons = payload.get("reasons") or []
    details = (payload.get("details") or "").strip()

    valid_reasons = set(dict(ContentReport.REASON_CHOICES))
    if isinstance(reasons, str):
        reasons = [reasons]
    if reasons:
        reasons = [r for r in reasons if r in valid_reasons]
        if not reasons:
            return JsonResponse({"success": False, "error": "Invalid reason."}, status=400)
        reason = reasons[0]
    elif reason:
        if reason not in valid_reasons:
            return JsonResponse({"success": False, "error": "Invalid reason."}, status=400)
        reasons = [reason]
    else:
        return JsonResponse({"success": False, "error": "Invalid reason."}, status=400)

    if reason == ContentReport.REASON_OTHER:
        details_stripped = (details or '').strip()
        if len(details_stripped) < 2 or len(details_stripped) > 300:
            return JsonResponse({"success": False, "error": "Please write other reasons."}, status=400)

    try:
        target_id = int(target_id)
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "error": "Invalid target."}, status=400)

    item = None
    comment = None
    if target_type == "item":
        item = get_object_or_404(Item.objects.filter(is_published=True), pk=target_id)
    elif target_type == "comment":
        comment = get_object_or_404(Comment.objects.filter(is_draft=False), pk=target_id)
    else:
        return JsonResponse({"success": False, "error": "Invalid target type."}, status=400)

    allowed, err = can_user_report(request.user)
    if not allowed:
        return JsonResponse({"success": False, "error": err}, status=429)

    report, err = ReportService.create_or_update_report(
        request.user, item=item, comment=comment, reason=reason, details=details
    )
    if err:
        return JsonResponse({"success": False, "error": err}, status=400)
    return JsonResponse({"success": True, "report_id": report.pk})
