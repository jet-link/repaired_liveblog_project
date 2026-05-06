"""Backup management views."""
import subprocess
import sys
from pathlib import Path

from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import FileResponse, Http404, JsonResponse
from django.conf import settings
from django.utils.dateparse import parse_date

from admin_panel.decorators import admin_required
from admin_panel.utils import redirect_preserve_query
from backups.models import Backup
from backups.services import create_backup_async, create_backup_sync


@admin_required
def backups_list(request):
    """List backups with optional date range filter (YYYY-MM-DD)."""
    if not request.user.is_superuser:
        raise PermissionDenied
    qs = Backup.objects.select_related('created_by').order_by('-created_at')
    date_from_raw = (request.GET.get('date_from') or '').strip()
    date_to_raw = (request.GET.get('date_to') or '').strip()
    df = parse_date(date_from_raw) if date_from_raw else None
    dt = parse_date(date_to_raw) if date_to_raw else None
    if df is not None:
        qs = qs.filter(created_at__date__gte=df)
    if dt is not None:
        qs = qs.filter(created_at__date__lte=dt)
    total_count = qs.count()
    return render(
        request,
        'admin/backups/backups_list.html',
        {
            'backups': qs,
            'total_count': total_count,
            'date_from': date_from_raw,
            'date_to': date_to_raw,
        },
    )


@admin_required
def backup_status(request):
    """Return backup status as JSON for polling. GET ?ids=1,2,3"""
    if not request.user.is_superuser:
        raise PermissionDenied
    ids_str = request.GET.get('ids', '')
    ids = []
    for x in ids_str.split(','):
        try:
            ids.append(int(x.strip()))
        except (ValueError, TypeError):
            pass
    backups = Backup.objects.filter(pk__in=ids)
    data = [
        {
            'id': b.pk,
            'status': b.status,
            'display': dict(Backup.STATUS_CHOICES).get(b.status, b.status),
            'has_file': bool(b.file_path),
            'file_size': b.file_size,
            'file_size_human': b.file_size_human if b.file_size else '—',
        }
        for b in backups
    ]
    return JsonResponse({'backups': data})


@admin_required
def backup_create(request):
    """Create new backup (POST): include_database, include_media, include_settings checkboxes."""
    if not request.user.is_superuser:
        raise PermissionDenied
    if request.method != 'POST':
        return redirect('admin_panel:backups_list')
    include_database = request.POST.get('include_database') == 'on'
    include_media = request.POST.get('include_media') == 'on'
    include_settings = request.POST.get('include_settings') == 'on'
    if not include_database and not include_media and not include_settings:
        messages.error(request, 'Select at least one: Database, Media, or Settings.')
        return redirect('admin_panel:backups_list')
    backup = create_backup_async(
        user=request.user,
        include_database=include_database,
        include_media=include_media,
        include_settings=include_settings,
    )
    messages.success(request, f'Backup "{backup.name}" started. It will complete in background.')
    return redirect('admin_panel:backups_list')


@admin_required
def backup_download(request, pk):
    """Download backup file."""
    if not request.user.is_superuser:
        raise PermissionDenied
    backup = get_object_or_404(Backup, pk=pk)
    if backup.status != Backup.STATUS_COMPLETED or not backup.file_path:
        raise Http404('Backup not available for download')
    path = Path(backup.file_path)
    if not path.exists():
        raise Http404('Backup file not found')
    return FileResponse(
        path.open('rb'),
        as_attachment=True,
        filename=path.name,
        content_type='application/gzip',
    )


@admin_required
def backup_restore(request, pk):
    """Restore from backup."""
    if not request.user.is_superuser:
        raise PermissionDenied
    backup = get_object_or_404(Backup, pk=pk)
    if backup.status != Backup.STATUS_COMPLETED or not backup.file_path:
        raise Http404('Backup not available for restore')
    path = Path(backup.file_path)
    if not path.exists():
        raise Http404('Backup file not found')

    if request.method == 'POST':
        confirm = request.POST.get('confirm') == 'yes'
        confirm_text = request.POST.get('confirm_text', '').strip().upper()
        if confirm and confirm_text == 'RESTORE':
            if request.POST.get('backup_before_restore') == 'yes':
                try:
                    safety = create_backup_sync(backup_type='pre_restore', user=request.user)
                    messages.info(request, f'Safety backup created: {safety.name}')
                except Exception as e:
                    messages.error(request, f'Cannot create safety backup: {e}. Restore cancelled.')
                    return redirect('admin_panel:backup_restore', pk=backup.pk)
            manage_py = Path(settings.BASE_DIR) / 'manage.py'
            cmd = [sys.executable, str(manage_py), 'restore_backup', str(path.resolve()), '--no-input']
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600, cwd=str(settings.BASE_DIR))
                if result.returncode == 0:
                    messages.success(request, 'Restore completed. Restart the server to use the restored data.')
                else:
                    messages.error(request, f'Restore failed: {result.stderr or result.stdout}')
            except subprocess.TimeoutExpired:
                messages.error(request, 'Restore timed out.')
            except Exception as e:
                messages.error(request, f'Restore failed: {str(e)}')
            return redirect('admin_panel:backups_list')

    return render(request, 'admin/backups/backup_restore_confirm.html', {'backup': backup})


@admin_required
def backup_delete(request, pk):
    """Delete backup."""
    if not request.user.is_superuser:
        raise PermissionDenied
    backup = get_object_or_404(Backup, pk=pk)
    if request.method == "POST":
        from django.utils import timezone

        backup.deleted_at = timezone.now()
        backup.save(update_fields=["deleted_at"])
        messages.success(request, "Backup moved to Recent deleted.")
        return redirect_preserve_query(request, "backups_list")
    return render(request, 'admin/backups/backup_confirm_delete.html', {'backup': backup})
