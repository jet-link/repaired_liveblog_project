"""
Admin для Backup. Доступ только superuser.
Кнопка Create Backup, скачивание, Restore, удаление.
"""
import logging
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.contrib import messages
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Backup
from .services import create_backup_async, create_backup_sync

logger = logging.getLogger('backups')


@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'backup_type', 'created_at', 'file_size_display', 'duration_display',
        'content_type_display', 'status_display', 'integrity_display', 'actions_column',
    )
    list_filter = ('status', 'schedule_type', 'backup_type', 'created_at')
    readonly_fields = (
        'name', 'schedule_type', 'backup_type', 'content_type', 'include_database', 'include_media',
        'include_settings', 'created_at',
        'file_size', 'file_path_display', 'status', 'duration_seconds', 'integrity_status',
        'error_message', 'restore_log', 'created_by',
    )
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_module_permission(self, request):
        return request.user.is_superuser

    def delete_model(self, request, obj):
        if obj.file_path and Path(obj.file_path).exists():
            try:
                Path(obj.file_path).unlink()
                logger.info('Backup file deleted by %s: %s', request.user, obj.file_path)
            except OSError as e:
                logger.warning('Could not delete backup file %s: %s', obj.file_path, e)
        logger.info('Backup record deleted by %s: %s', request.user, obj.name)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            if obj.file_path and Path(obj.file_path).exists():
                try:
                    Path(obj.file_path).unlink()
                    logger.info('Backup file deleted by %s: %s', request.user, obj.file_path)
                except OSError as e:
                    logger.warning('Could not delete backup file %s: %s', obj.file_path, e)
            logger.info('Backup record deleted by %s: %s', request.user, obj.name)
        super().delete_queryset(request, queryset)

    def file_size_display(self, obj):
        return obj.file_size_human if obj.file_size else '-'

    file_size_display.short_description = 'Size'

    def duration_display(self, obj):
        return obj.duration_human if hasattr(obj, 'duration_human') else '-'

    duration_display.short_description = 'Duration'

    def content_type_display(self, obj):
        if obj is None:
            return '-'
        return obj.get_components_label()

    content_type_display.short_description = 'Content'

    def status_display(self, obj):
        status = obj.status
        label = dict(Backup.STATUS_CHOICES).get(status, status)
        if status == Backup.STATUS_RUNNING:
            label = 'Running...'
        css = {'pending': 'pending', 'running': 'running', 'completed': 'completed', 'failed': 'failed'}.get(status, '')
        return format_html('<span class="backup-status backup-status-{}">{}</span>', css, label)

    status_display.short_description = 'Status'

    def integrity_display(self, obj):
        status = getattr(obj, 'integrity_status', None) or ''
        if not status or status == 'unknown':
            return '-'
        label = dict(Backup.INTEGRITY_CHOICES).get(status, status)
        css = {'unknown': '', 'verified': 'verified', 'corrupted': 'corrupted'}.get(status, '')
        if css:
            return format_html('<span class="backup-integrity backup-integrity-{}">{}</span>', css, label)
        return label

    integrity_display.short_description = 'Integrity'

    def file_path_display(self, obj):
        if not obj.file_path:
            return '-'
        return obj.filename_display

    file_path_display.short_description = 'File'

    def actions_column(self, obj):
        download_url = reverse('admin:backups_backup_download', args=[obj.pk])
        restore_url = reverse('admin:backups_backup_restore', args=[obj.pk])
        delete_url = reverse('admin:backups_backup_delete', args=[obj.pk])
        can_restore = obj.status == Backup.STATUS_COMPLETED and obj.file_path and Path(obj.file_path).exists()
        can_download = can_restore
        parts = []
        if can_download:
            parts.append(format_html('<li><a href="{}">Download</a></li>', download_url))
        if can_restore:
            parts.append(format_html('<li><a href="{}">Restore</a></li>', restore_url))
        parts.append(format_html('<li><a href="{}" class="delete-link">Delete</a></li>', delete_url))
        menu = mark_safe(''.join(str(p) for p in parts))
        return format_html(
            '<details class="backup-actions-dropdown">'
            '<summary class="button">Actions ▾</summary>'
            '<ul class="backup-actions-menu">{}</ul>'
            '</details>',
            menu,
        )

    actions_column.short_description = 'Actions'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_create_backup'] = request.user.is_superuser
        return super().changelist_view(request, extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('create/', self.admin_site.admin_view(self.create_backup_view), name='backups_backup_create'),
            path('<int:pk>/download/', self.admin_site.admin_view(self.download_backup_view), name='backups_backup_download'),
            path('<int:pk>/restore/', self.admin_site.admin_view(self.restore_backup_view), name='backups_backup_restore'),
        ]
        return custom + urls

    def create_backup_view(self, request):
        if not request.user.is_superuser:
            raise Http404
        backup = create_backup_async(user=request.user)
        logger.info('Backup creation started by %s: %s', request.user, backup.name)
        url = reverse('admin:backups_backup_changelist')
        return HttpResponseRedirect(url)

    def download_backup_view(self, request, pk):
        if not request.user.is_superuser:
            raise Http404
        backup = get_object_or_404(Backup, pk=pk)
        if backup.status != Backup.STATUS_COMPLETED or not backup.file_path:
            raise Http404('Backup not available for download')
        path = Path(backup.file_path)
        if not path.exists():
            raise Http404('Backup file not found')
        try:
            return FileResponse(
                path.open('rb'),
                as_attachment=True,
                filename=path.name,
                content_type='application/gzip',
            )
        except OSError as e:
            logger.error('Download failed for backup %s: %s', backup.pk, e)
            raise Http404('Could not open backup file')

    def restore_backup_view(self, request, pk):
        if not request.user.is_superuser:
            raise Http404
        backup = get_object_or_404(Backup, pk=pk)
        if backup.status != Backup.STATUS_COMPLETED or not backup.file_path:
            raise Http404('Backup not available for restore')
        path = Path(backup.file_path)
        if not path.exists():
            raise Http404('Backup file not found')

        confirm_ok = (
            request.method == 'POST'
            and request.POST.get('confirm') == 'yes'
            and request.POST.get('confirm_text', '').strip().upper() == 'RESTORE'
        )
        if confirm_ok:
            # Safety backup before restore (optional)
            if request.POST.get('backup_before_restore') == 'yes':
                try:
                    safety = create_backup_sync(backup_type='pre_restore', user=request.user)
                    messages.info(request, f'Safety backup created: {safety.name}')
                except Exception as e:
                    logger.exception('Safety backup failed: %s', e)
                    messages.error(request, f'Cannot create safety backup: {e}. Restore cancelled.')
                    return HttpResponseRedirect(reverse('admin:backups_backup_restore', args=[pk]))

            manage_py = Path(settings.BASE_DIR) / 'manage.py'
            cmd = [sys.executable, str(manage_py), 'restore_backup', str(path.resolve()), '--no-input']
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600, cwd=str(settings.BASE_DIR))
                if result.returncode == 0:
                    logger.info('Restore completed by %s: %s', request.user, backup.name)
                    msg = 'Restore completed. Restart the server to use the restored data.'
                    if result.stdout.strip():
                        msg += f' Log: {result.stdout.strip()}'
                    messages.success(request, msg)
                else:
                    logger.error('Restore failed: %s', result.stderr or result.stdout)
                    messages.error(request, f'Restore failed: {result.stderr or result.stdout}')
            except subprocess.TimeoutExpired:
                messages.error(request, 'Restore timed out.')
            except Exception as e:
                logger.exception('Restore failed: %s', e)
                messages.error(request, f'Restore failed: {str(e)}')
            return HttpResponseRedirect(reverse('admin:backups_backup_changelist'))

        context = {
            'title': 'Confirm Restore',
            'backup': backup,
            'backup_before_restore': True,
            'opts': self.model._meta,
        }
        return render(request, 'admin/backups/backup/restore_confirm.html', context)
