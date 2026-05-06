"""
Сервис создания backup: опционально pg_dump, media, settings в tar.gz.
Выполняется асинхронно в отдельном потоке.
"""
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
import threading
from pathlib import Path

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('backups')


BACKUPS_ROOT = getattr(settings, 'BACKUPS_ROOT', None) or (Path(settings.BASE_DIR) / 'backups')
MAX_BACKUPS = getattr(settings, 'BACKUP_MAX_COUNT', 20)
BACKUP_DAILY_COUNT = getattr(settings, 'BACKUP_DAILY_COUNT', 7)
BACKUP_WEEKLY_COUNT = getattr(settings, 'BACKUP_WEEKLY_COUNT', 4)
BACKUP_MONTHLY_COUNT = getattr(settings, 'BACKUP_MONTHLY_COUNT', 12)


def _ensure_backups_dir():
    """Создаёт директорию backups если её нет."""
    BACKUPS_ROOT.mkdir(parents=True, exist_ok=True)


def _dir_has_files(path):
    """True если в дереве есть хотя бы один файл."""
    p = Path(path)
    if not p.exists():
        return False
    return any(f.is_file() for f in p.rglob('*'))


def _run_pg_dump(db_settings, output_path):
    """Выполняет pg_dump и сохраняет в output_path."""
    env = os.environ.copy()
    env['PGPASSWORD'] = db_settings.get('PASSWORD', '')
    cmd = [
        'pg_dump',
        '-h', db_settings.get('HOST', 'localhost'),
        '-p', str(db_settings.get('PORT', '5432')),
        '-U', db_settings.get('USER', 'postgres'),
        '-d', db_settings.get('NAME', ''),
        '-F', 'p',  # plain SQL
        '-f', str(output_path),
        '--no-owner',
        '--no-acl',
        '--clean',  # add DROP statements for restore
    ]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=3600)
    if result.returncode != 0:
        raise RuntimeError(f'pg_dump failed: {result.stderr or result.stdout}')


def _verify_tar_integrity(archive_path):
    """Проверяет целостность tar.gz архива."""
    try:
        result = subprocess.run(
            ['tar', '-tzf', str(archive_path)],
            capture_output=True, timeout=60, cwd=str(archive_path.parent),
        )
        return result.returncode == 0
    except Exception:
        return False


def _copy_settings_snapshot(tmpdir):
    """
    Копирует снимок настроек в tmpdir/settings_snapshot/.
    Секреты из .env попадают в архив — только для осознанного суперпользователя.
    """
    snap = tmpdir / 'settings_snapshot'
    snap.mkdir(parents=True, exist_ok=True)
    base = Path(settings.BASE_DIR)
    proj_settings = base / 'liveblog_project' / 'settings.py'
    if proj_settings.exists():
        dest = snap / 'liveblog_project' / 'settings.py'
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(proj_settings, dest)
        logger.info('Settings snapshot: %s', dest)
    env_parent = base.parent / '.env'
    if env_parent.is_file():
        shutil.copy2(env_parent, snap / '.env')
        logger.info('Copied .env into settings snapshot')
    return snap


def _create_backup_archive(backup_obj):
    """
    Создаёт backup по флагам include_*: database.sql, media/, settings_snapshot/ в tar.gz.
    Обновляет backup_obj по ходу выполнения.
    """
    from backups.models import Backup

    import time
    start_time = time.time()

    include_database = getattr(backup_obj, 'include_database', True)
    include_media = getattr(backup_obj, 'include_media', True)
    include_settings = getattr(backup_obj, 'include_settings', False)

    if not include_database and not include_media and not include_settings:
        backup_obj.status = Backup.STATUS_FAILED
        backup_obj.error_message = 'Select at least one of: database, media, settings.'
        backup_obj.save(update_fields=['status', 'error_message'])
        return

    backup_obj.status = Backup.STATUS_RUNNING
    if backup_obj.backup_type in (Backup.BACKUP_TYPE_MANUAL, ''):
        backup_obj.backup_type = 'manual' if backup_obj.schedule_type == Backup.SCHEDULE_MANUAL else 'auto'
    backup_obj.save(update_fields=['status', 'backup_type', 'content_type'])

    tmpdir = None
    try:
        tmpdir = Path(tempfile.mkdtemp())
        db_sql = tmpdir / 'database.sql'
        media_dest = tmpdir / 'media'
        content_blocks = []

        db_settings = settings.DATABASES['default']
        media_root = Path(settings.MEDIA_ROOT)

        if include_database:
            _run_pg_dump(db_settings, db_sql)
            logger.info('Database dump created: %s', db_sql)
            if db_sql.exists() and db_sql.stat().st_size > 0:
                content_blocks.append('database')
            else:
                raise RuntimeError('database.sql is empty after pg_dump')

        if include_media:
            if media_root.exists() and _dir_has_files(media_root):
                shutil.copytree(media_root, media_dest, dirs_exist_ok=True)
                logger.info('Media copied to %s', media_dest)
                content_blocks.append('media')
            else:
                logger.warning('MEDIA_ROOT missing or has no files; media not included in archive')

        if include_settings:
            snap = _copy_settings_snapshot(tmpdir)
            if _dir_has_files(snap):
                content_blocks.append('settings')
            else:
                logger.warning('Settings snapshot has no files (settings.py / .env missing?)')

        if not content_blocks:
            raise ValueError(
                'Backup would be empty: enable at least one component that has data '
                '(e.g. empty media folder, or settings files missing).'
            )

        _ensure_backups_dir()
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        schedule = getattr(backup_obj, 'schedule_type', 'manual')
        suffix = f'_{schedule}' if schedule != 'manual' else ''
        archive_name = f'backup{suffix}_{timestamp}.tar.gz'
        archive_path = BACKUPS_ROOT / archive_name

        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(tmpdir, arcname='backup')
        logger.info('Archive created: %s', archive_path)

        duration = time.time() - start_time
        file_size = archive_path.stat().st_size
        integrity = Backup.INTEGRITY_VERIFIED if _verify_tar_integrity(archive_path) else Backup.INTEGRITY_UNKNOWN
        backup_obj.status = Backup.STATUS_COMPLETED
        backup_obj.file_path = str(archive_path)
        backup_obj.file_size = file_size
        backup_obj.duration_seconds = round(duration, 1)
        backup_obj.integrity_status = integrity
        backup_obj.error_message = ''
        backup_obj.save(update_fields=[
            'status', 'file_path', 'file_size', 'duration_seconds',
            'integrity_status', 'error_message',
        ])

        logger.info('Backup completed: %s, size: %s', backup_obj.name, backup_obj.file_size_human)

        _cleanup_old_backups(backup_obj.schedule_type)

    except Exception as e:
        logger.exception('Backup failed: %s', e)
        backup_obj.status = Backup.STATUS_FAILED
        backup_obj.error_message = str(e)[:500]
        backup_obj.save(update_fields=['status', 'error_message'])
    finally:
        if tmpdir and tmpdir.exists():
            shutil.rmtree(tmpdir, ignore_errors=True)


def _cleanup_old_backups(schedule_type=None, exclude_pk=None):
    """Удаляет самые старые backup по лимитам: daily=7, weekly=4, monthly=12, manual=20."""
    from backups.models import Backup

    limits = {
        Backup.SCHEDULE_DAILY: BACKUP_DAILY_COUNT,
        Backup.SCHEDULE_WEEKLY: BACKUP_WEEKLY_COUNT,
        Backup.SCHEDULE_MONTHLY: BACKUP_MONTHLY_COUNT,
        Backup.SCHEDULE_MANUAL: MAX_BACKUPS,
    }
    st = schedule_type or Backup.SCHEDULE_MANUAL
    limit = limits.get(st, MAX_BACKUPS)
    qs = Backup.objects.filter(
        status=Backup.STATUS_COMPLETED,
        schedule_type=st,
    ).order_by('created_at')
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    count = qs.count()
    if count > limit:
        to_remove = list(qs[: count - limit])
    else:
        to_remove = []
    for b in to_remove:
        if b.file_path and Path(b.file_path).exists():
            try:
                Path(b.file_path).unlink()
                logger.info('Old backup file deleted: %s', b.file_path)
            except OSError as e:
                logger.warning('Could not delete backup file %s: %s', b.file_path, e)
        b.delete()
        logger.info('Old backup record deleted: %s', b.name)


def create_backup_scheduled(
    schedule='manual',
    user=None,
    include_database=True,
    include_media=True,
    include_settings=False,
):
    """
    Создаёт backup по расписанию (daily/weekly/monthly) или вручную.
    По умолчанию DB + media (как раньше); settings — опционально.
    Запускается асинхронно в отдельном потоке.
    """
    from backups.models import Backup

    suffix = f' ({schedule})' if schedule != Backup.SCHEDULE_MANUAL else ''
    local_now = timezone.localtime(timezone.now())
    backup = Backup.objects.create(
        name=f'Backup {local_now.strftime("%Y-%m-%d %H:%M:%S")}{suffix}',
        schedule_type=schedule,
        status=Backup.STATUS_PENDING,
        created_by=user,
        include_database=include_database,
        include_media=include_media,
        include_settings=include_settings,
    )
    logger.info('Backup created (pending): %s by %s', backup.name, user)
    thread = threading.Thread(target=_create_backup_archive, args=(backup,))
    thread.daemon = True
    thread.start()
    return backup


def create_backup_async(
    user=None,
    include_database=True,
    include_media=True,
    include_settings=False,
):
    """
    Создаёт backup асинхронно в отдельном потоке (ручное создание из админки).
    Возвращает созданный объект Backup.
    """
    return create_backup_scheduled(
        schedule='manual',
        user=user,
        include_database=include_database,
        include_media=include_media,
        include_settings=include_settings,
    )


def create_backup_sync(backup_type='pre_restore', user=None, timeout=3600):
    """
    Создаёт backup синхронно (ждёт завершения).
    Полный снимок DB + media (settings не включаем по умолчанию), как раньше для безопасности перед restore.
    """
    from backups.models import Backup

    local_now = timezone.localtime(timezone.now())
    backup = Backup.objects.create(
        name=f'Safety backup before restore {local_now.strftime("%Y-%m-%d %H:%M:%S")}',
        schedule_type=Backup.SCHEDULE_MANUAL,
        backup_type=backup_type,
        status=Backup.STATUS_PENDING,
        created_by=user,
        include_database=True,
        include_media=True,
        include_settings=False,
    )
    logger.info('Safety backup started (sync): %s', backup.name)
    _create_backup_archive(backup)
    backup.refresh_from_db()
    if backup.status != Backup.STATUS_COMPLETED:
        raise RuntimeError(f'Safety backup failed: {backup.error_message}')
    return backup
