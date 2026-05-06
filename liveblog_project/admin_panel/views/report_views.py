"""Report moderation views."""
from urllib.parse import urlencode
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q, Subquery, OuterRef, Case, When, Value, IntegerField

from admin_panel.decorators import admin_required
from smart_blog.models import ContentReport, Item, Comment
from django.contrib.auth import get_user_model

User = get_user_model()

# Subqueries for target reports count (exclude admin_hidden and soft-deleted)
_item_reports_subq = ContentReport.objects.filter(
    item_id=OuterRef('item_id'), admin_hidden=False, deleted_at__isnull=True,
).values('item_id').annotate(cnt=Count('id')).values('cnt')[:1]
_comment_reports_subq = ContentReport.objects.filter(
    comment_id=OuterRef('comment_id'), admin_hidden=False, deleted_at__isnull=True,
).values('comment_id').annotate(cnt=Count('id')).values('cnt')[:1]


@admin_required
def reports_list(request):
    """List content reports with filters and sorting."""
    qs = ContentReport.objects.select_related('reporter', 'item', 'comment')
    qs = qs.filter(deleted_at__isnull=True)
    qs = qs.exclude(admin_hidden=True)
    qs = qs.exclude(item__is_published=False).exclude(comment__is_draft=True)

    # Type filter (Posts / Comments)
    target = request.GET.get('target')
    if target == 'item':
        qs = qs.filter(item__isnull=False)
    elif target == 'comment':
        qs = qs.filter(comment__isnull=False)

    # Reason filter
    reason = request.GET.get('reason')
    if reason:
        qs = qs.filter(Q(reason=reason) | Q(reasons__contains=[reason]))

    # Annotate target reports count
    qs = qs.annotate(
        target_reports_count=Case(
            When(item_id__isnull=False, then=Subquery(_item_reports_subq)),
            When(comment_id__isnull=False, then=Subquery(_comment_reports_subq)),
            default=Value(0),
            output_field=IntegerField(),
        )
    )

    # Sort: date (default) or reports count
    sort = request.GET.get('sort', 'date')
    if sort == 'reports':
        qs = qs.order_by('-target_reports_count', '-created_at')
    else:
        qs = qs.order_by('-created_at')

    paginator = Paginator(qs, 30)
    page = request.GET.get('page', 1)
    reports = paginator.get_page(page)

    # Build query string for filter persistence on redirects
    filter_params = {}
    if target:
        filter_params['target'] = target
    if reason:
        filter_params['reason'] = reason
    if sort and sort != 'date':
        filter_params['sort'] = sort
    page_num = request.GET.get('page')
    if page_num:
        filter_params['page'] = page_num
    filter_qs = urlencode(filter_params) if filter_params else ''

    context = {
        'reports': reports,
        'current_target': target,
        'current_reason': reason,
        'current_sort': sort,
        'filter_qs': filter_qs,
    }
    return render(request, 'admin/reports/reports_list.html', context)


def _reports_redirect_with_filters(request):
    """Redirect to reports list preserving filter params."""
    qs = request.GET.urlencode()
    url = reverse('admin_panel:reports_list')
    return redirect(f'{url}?{qs}' if qs else url)


@admin_required
def report_resolve(request, pk):
    """Mark report as Resolved."""
    report = get_object_or_404(ContentReport, pk=pk)
    if request.method == 'POST':
        report.status = ContentReport.STATUS_RESOLVED
        report.save()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True, "new_status": "resolved"})
        messages.success(request, 'Report marked as resolved.')
        return _reports_redirect_with_filters(request)
    return _reports_redirect_with_filters(request)


@admin_required
def report_dismiss(request, pk):
    """Dismiss report (mark as Ignored)."""
    report = get_object_or_404(ContentReport, pk=pk)
    if request.method == 'POST':
        report.status = ContentReport.STATUS_IGNORED
        report.save()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True, "new_status": "ignored"})
        messages.success(request, 'Report dismissed.')
        return _reports_redirect_with_filters(request)
    return _reports_redirect_with_filters(request)


@admin_required
def report_delete_content(request, pk):
    """Delete reported content (item or comment)."""
    report = get_object_or_404(ContentReport, pk=pk)
    if request.method == 'POST':
        if report.item:
            report.item.delete()
            messages.success(request, 'Reported post deleted.')
        elif report.comment:
            report.comment.delete()
            messages.success(request, 'Reported comment deleted.')
        # Report is CASCADE-deleted with content; do not save
        return _reports_redirect_with_filters(request)
    next_qs = request.GET.urlencode()
    return render(request, 'admin/reports/report_confirm_delete_content.html', {
        'report': report,
        'next_qs': next_qs,
    })


@admin_required
def report_ban_user(request, pk):
    """Ban user from report (reported content author)."""
    report = get_object_or_404(ContentReport, pk=pk)
    user = None
    if report.item and report.item.author:
        user = report.item.author
    elif report.comment and report.comment.author:
        user = report.comment.author
    if not user:
        messages.error(request, 'No user to ban.')
        return _reports_redirect_with_filters(request)
    if request.method == 'POST':
        if user == request.user:
            messages.error(request, 'You cannot ban yourself.')
        elif user.is_superuser:
            messages.error(request, 'Cannot ban superuser.')
        else:
            user.is_active = False
            user.save()
            messages.success(request, f'User {user.username} has been banned.')
        report.status = ContentReport.STATUS_RESOLVED
        report.save()
        return _reports_redirect_with_filters(request)
    next_qs = request.GET.urlencode()
    return render(request, 'admin/reports/report_confirm_ban.html', {
        'report': report,
        'user_obj': user,
        'next_qs': next_qs,
    })
