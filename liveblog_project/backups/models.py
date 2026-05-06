from django.db import models
from django.conf import settings


class BackupManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Backup(models.Model):
    """Модель для хранения информации о backup."""

    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]

    SCHEDULE_MANUAL = 'manual'
    SCHEDULE_DAILY = 'daily'
    SCHEDULE_WEEKLY = 'weekly'
    SCHEDULE_MONTHLY = 'monthly'
    SCHEDULE_CHOICES = [
        (SCHEDULE_MANUAL, 'Manual'),
        (SCHEDULE_DAILY, 'Daily'),
        (SCHEDULE_WEEKLY, 'Weekly'),
        (SCHEDULE_MONTHLY, 'Monthly'),
    ]

    BACKUP_TYPE_MANUAL = 'manual'
    BACKUP_TYPE_AUTO = 'auto'
    BACKUP_TYPE_PRE_DEPLOY = 'pre_deploy'
    BACKUP_TYPE_PRE_RESTORE = 'pre_restore'
    BACKUP_TYPE_CHOICES = [
        (BACKUP_TYPE_MANUAL, 'Manual'),
        (BACKUP_TYPE_AUTO, 'Auto'),
        (BACKUP_TYPE_PRE_DEPLOY, 'Pre-deploy'),
        (BACKUP_TYPE_PRE_RESTORE, 'Pre-restore'),
    ]

    CONTENT_DATABASE = 'database'
    CONTENT_MEDIA = 'media'
    CONTENT_DATABASE_MEDIA = 'database_media'
    CONTENT_FULL = 'full'
    CONTENT_SETTINGS = 'settings'
    CONTENT_MIXED = 'mixed'
    CONTENT_CHOICES = [
        (CONTENT_DATABASE, 'Database'),
        (CONTENT_MEDIA, 'Media'),
        (CONTENT_DATABASE_MEDIA, 'Database + Media'),
        (CONTENT_FULL, 'Full (DB + Media + Settings)'),
        (CONTENT_SETTINGS, 'Settings only'),
        (CONTENT_MIXED, 'Mixed selection'),
    ]

    INTEGRITY_UNKNOWN = 'unknown'
    INTEGRITY_VERIFIED = 'verified'
    INTEGRITY_CORRUPTED = 'corrupted'
    INTEGRITY_CHOICES = [
        (INTEGRITY_UNKNOWN, 'Unknown'),
        (INTEGRITY_VERIFIED, 'Verified'),
        (INTEGRITY_CORRUPTED, 'Corrupted'),
    ]

    name = models.CharField(max_length=255, verbose_name='Backup name')
    schedule_type = models.CharField(
        max_length=20,
        choices=SCHEDULE_CHOICES,
        default=SCHEDULE_MANUAL,
        verbose_name='Schedule',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    file_size = models.BigIntegerField(default=0, verbose_name='File size (bytes)')
    file_path = models.CharField(max_length=500, blank=True, verbose_name='File path')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name='Status',
    )
    error_message = models.TextField(blank=True, verbose_name='Error message')
    duration_seconds = models.FloatField(null=True, blank=True, verbose_name='Duration (sec)')
    backup_type = models.CharField(
        max_length=20,
        choices=BACKUP_TYPE_CHOICES,
        default=BACKUP_TYPE_MANUAL,
        verbose_name='Backup type',
    )
    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_CHOICES,
        default=CONTENT_DATABASE_MEDIA,
        verbose_name='Content',
    )
    include_database = models.BooleanField(default=True, verbose_name='Include database')
    include_media = models.BooleanField(default=True, verbose_name='Include media')
    include_settings = models.BooleanField(default=False, verbose_name='Include settings')
    integrity_status = models.CharField(
        max_length=20,
        choices=INTEGRITY_CHOICES,
        default=INTEGRITY_UNKNOWN,
        verbose_name='Integrity',
    )
    restore_log = models.TextField(blank=True, verbose_name='Restore log')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_backups',
        verbose_name='Created by',
    )
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='Deleted at')

    objects = BackupManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Backup'
        verbose_name_plural = 'Backups'

    def __str__(self):
        return f'{self.name} ({self.created_at})'

    def derive_content_type(self):
        """Маппинг флагов в content_type для списков и фильтров."""
        d, m, s = self.include_database, self.include_media, self.include_settings
        if d and m and s:
            return self.CONTENT_FULL
        if d and m and not s:
            return self.CONTENT_DATABASE_MEDIA
        if d and not m and not s:
            return self.CONTENT_DATABASE
        if not d and m and not s:
            return self.CONTENT_MEDIA
        if not d and not m and s:
            return self.CONTENT_SETTINGS
        return self.CONTENT_MIXED

    def save(self, *args, **kwargs):
        self.content_type = self.derive_content_type()
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            uf = list(update_fields)
            if 'content_type' not in uf:
                uf.append('content_type')
            kwargs['update_fields'] = uf
        super().save(*args, **kwargs)

    def get_components_label(self):
        """Краткая метка для UI: DB / Media / Settings."""
        parts = []
        if self.include_database:
            parts.append('DB')
        if self.include_media:
            parts.append('Media')
        if self.include_settings:
            parts.append('Settings')
        return ' / '.join(parts) if parts else '—'

    @property
    def file_size_human(self):
        """Возвращает размер файла в человекочитаемом формате."""
        size = self.file_size
        for unit in ('B', 'KB', 'MB', 'GB'):
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} TB'

    @property
    def filename_display(self):
        """Возвращает только имя файла без пути (для UI)."""
        if not self.file_path:
            return '-'
        return self.file_path.rsplit('/', 1)[-1].rsplit('\\', 1)[-1]

    @property
    def duration_human(self):
        """Возвращает длительность в формате 4.3 sec."""
        if self.duration_seconds is None:
            return '-'
        if self.duration_seconds < 60:
            return f'{self.duration_seconds:.1f} sec'
        m = int(self.duration_seconds // 60)
        s = self.duration_seconds % 60
        return f'{m}m {s:.0f}s'
