"""Report API views."""

import json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django_ratelimit.decorators import ratelimit
from django.views.decorators.http import require_http_methods, require_POST
from django.shortcuts import get_object_or_404

from .models import Item, Comment, ContentReport
from .services.reports import ReportService
from .services.report_limits import can_user_report


def _parse_json_body(request):
    """Parse JSON body, return dict or empty dict."""
    try:
        if request.headers.get("Content-Type", "").startswith("application/json"):
            return json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    return {}


def _get_csrf_token(request):
    """Extract CSRF token from cookie."""
    for c in (request.COOKIES.get("csrftoken", "") or "").split("; "):
        if c.startswith("csrftoken="):
            return c.split("=", 1)[1]
    return ""


# ---------------------------------------------------------------------------
# GET report status (for modal to show "Reported by you" vs form)
# ---------------------------------------------------------------------------

@login_required
@ratelimit(key='ip', rate='90/m', method='GET', block=False)
@require_http_methods(["GET"])
def api_report_post(request, pk):
    """GET /blog/api/report/post/<pk>/ — current user's report for this post or exists: false."""
    if getattr(request, 'limited', False):
        return JsonResponse({'error': 'rate_limited'}, status=429)
    item = get_object_or_404(Item.objects.filter(is_published=True), pk=pk)
    report = ReportService.get_user_report(request.user, item=item)
    if not report:
        return JsonResponse({"exists": False})
    return JsonResponse({
        "exists": True,
        "report": {
            "id": report.pk,
            "reason": report.reason,
            "reasons": list(report.reasons) if getattr(report, "reasons", None) and report.reasons else ([report.reason] if report.reason else []),
            "details": report.details or "",
            "created_at": report.created_at.isoformat(),
            "updated_at": report.updated_at.isoformat(),
        },
    })


@login_required
@ratelimit(key='ip', rate='90/m', method='GET', block=False)
@require_http_methods(["GET"])
def api_report_comment(request, pk):
    """GET /api/report/comment/<pk>/ - return current user's report for comment or exists: false."""
    if getattr(request, 'limited', False):
        return JsonResponse({'error': 'rate_limited'}, status=429)
    comment = get_object_or_404(Comment.objects.filter(is_draft=False), pk=pk)
    report = ReportService.get_user_report(request.user, comment=comment)
    if not report:
        return JsonResponse({"exists": False})
    return JsonResponse({
        "exists": True,
        "report": {
            "id": report.pk,
            "reason": report.reason,
            "reasons": list(report.reasons) if getattr(report, "reasons", None) and report.reasons else ([report.reason] if report.reason else []),
            "details": report.details or "",
            "created_at": report.created_at.isoformat(),
            "updated_at": report.updated_at.isoformat(),
        },
    })


# ---------------------------------------------------------------------------
# POST create/update report
# ---------------------------------------------------------------------------

@login_required
@ratelimit(key='ip', rate=settings.RATELIMIT_REPORT_POST_RATE, method='POST', block=False)
@require_POST
def report_post(request, pk):
    """POST /blog/report/post/<pk>/ — create or update report for this post."""
    if getattr(request, 'limited', False):
        return JsonResponse({'success': False, 'error': 'rate_limited'}, status=429)
    item = get_object_or_404(Item.objects.filter(is_published=True), pk=pk)
    allowed, err = can_user_report(request.user)
    if not allowed:
        return JsonResponse({"success": False, "error": err}, status=429)

    payload = _parse_json_body(request)
    reasons = payload.get("reasons")
    reason = (payload.get("reason") or "").strip()
    details = (payload.get("details") or "").strip()
    if reasons and isinstance(reasons, list):
        reasons = [str(r).strip() for r in reasons if r]
    elif reason:
        reasons = [reason]

    report, err = ReportService.create_or_update_report(
        request.user, item=item, reasons=reasons, details=details
    )
    if err:
        return JsonResponse({"success": False, "error": err}, status=400)
    return JsonResponse({"success": True, "report_id": report.pk})


@login_required
@ratelimit(key='ip', rate=settings.RATELIMIT_REPORT_POST_RATE, method='POST', block=False)
@require_POST
def report_comment(request, pk):
    """POST /report/comment/<pk>/ - create or update report for comment."""
    if getattr(request, 'limited', False):
        return JsonResponse({'success': False, 'error': 'rate_limited'}, status=429)
    comment = get_object_or_404(Comment.objects.filter(is_draft=False), pk=pk)
    allowed, err = can_user_report(request.user)
    if not allowed:
        return JsonResponse({"success": False, "error": err}, status=429)

    payload = _parse_json_body(request)
    reasons = payload.get("reasons")
    reason = (payload.get("reason") or "").strip()
    details = (payload.get("details") or "").strip()
    if reasons and isinstance(reasons, list):
        reasons = [str(r).strip() for r in reasons if r]
    elif reason:
        reasons = [reason]

    report, err = ReportService.create_or_update_report(
        request.user, comment=comment, reasons=reasons, details=details
    )
    if err:
        return JsonResponse({"success": False, "error": err}, status=400)
    return JsonResponse({"success": True, "report_id": report.pk})


# ---------------------------------------------------------------------------
# DELETE cancel report
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(["DELETE", "POST"])
def cancel_report(request, pk):
    """DELETE /report/<pk>/ or POST with _method=DELETE - cancel (delete) report."""
    report = get_object_or_404(ContentReport, pk=pk)
    success, err = ReportService.cancel_report(request.user, report)
    if not success:
        return JsonResponse({"success": False, "error": err or "Forbidden"}, status=403)
    return JsonResponse({"success": True})
