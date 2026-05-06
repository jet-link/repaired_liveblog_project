"""Assistant (AI content moderation) views."""
import threading
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from admin_panel.decorators import admin_required
from admin_panel.models import AnalysisRun
from admin_panel.services.content_analyzer import run_content_analysis


@admin_required
@require_GET
def assistant_view(request):
    """Assistant page: Analyze button, progress, logs."""
    if not request.user.is_superuser:
        return render(request, 'admin/assistant/assistant.html', {'access_denied': True})
    recent_runs = list(
        AnalysisRun.objects.order_by('-started_at').select_related('started_by')[:30]
    )
    return render(request, 'admin/assistant/assistant.html', {
        'recent_runs': recent_runs,
    })


@admin_required
@require_POST
def assistant_analyze(request):
    """Start content analysis. Returns analysis_id for polling."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    schedule = request.POST.get('schedule', 'now')
    if schedule not in ('now', 'hourly', 'daily'):
        schedule = 'now'

    analysis_run = AnalysisRun.objects.create(
        schedule=schedule,
        status=AnalysisRun.STATUS_RUNNING,
        progress=0,
        started_by=request.user,
    )

    def run_in_background():
        run_content_analysis(schedule=schedule, analysis_run=analysis_run)

    thread = threading.Thread(target=run_in_background, daemon=True)
    thread.start()

    return JsonResponse({
        'success': True,
        'analysis_id': analysis_run.pk,
    })


@admin_required
@require_GET
def assistant_status(request, pk):
    """Return analysis run status for polling."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False}, status=403)
    run = AnalysisRun.objects.filter(pk=pk).select_related('started_by').first()
    if not run:
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)
    violations_count = run.violations.count() if run.pk else 0
    return JsonResponse({
        'success': True,
        'analysis_id': run.pk,
        'status': run.status,
        'progress': run.progress,
        'log_lines': run.log_lines or [],
        'violations_count': violations_count,
        'started_at': run.started_at.isoformat() if run.started_at else None,
        'started_by': run.started_by.username if run.started_by else None,
    })


@admin_required
@require_GET
def assistant_check_running(request):
    """Return running analysis id if any (for page load recovery)."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False}, status=403)
    run = AnalysisRun.objects.filter(status=AnalysisRun.STATUS_RUNNING).order_by('-started_at').first()
    if run:
        return JsonResponse({
            'success': True,
            'running': True,
            'analysis_id': run.pk,
        })
    return JsonResponse({'success': True, 'running': False})


@admin_required
@require_POST
def assistant_clear_history(request):
    """Delete all analysis run history."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False}, status=403)
    deleted = AnalysisRun.objects.all().delete()[0]
    return JsonResponse({'success': True, 'deleted': deleted})
