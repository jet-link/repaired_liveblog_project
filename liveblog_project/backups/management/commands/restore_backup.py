"""
Восстановление из backup: опционально database.sql, media/, settings_snapshot/.

Запуск: python manage.py restore_backup /path/to/backup.tar.gz

Структура архива (префикс backup/):
  - backup/database.sql — дамп PostgreSQL (опционально)
  - backup/media/ — файлы MEDIA (опционально)
  - backup/settings_snapshot/liveblog_project/settings.py — копия settings (опционально)
  - backup/settings_snapshot/.env — копия .env из корня репозитория (опционально; секреты!)

ВНИМАНИЕ: восстановление может перезаписать БД, media и файлы настроек.
Рекомендуется остановить приложение перед восстановлением.
"""
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

logger = logging.getLogger('backups')


def _restore_settings_snapshot(backup_dir, log_lines):
    """Копирует файлы из backup/settings_snapshot/ в проект."""
    snap = backup_dir / 'settings_snapshot'
    if not snap.exists() or not snap.is_dir():
        return 0
    base = Path(settings.BASE_DIR)
    n = 0
    proj_settings = snap / 'liveblog_project' / 'settings.py'
    if proj_settings.is_file():
        dest = base / 'liveblog_project' / 'settings.py'
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(proj_settings, dest)
        log_lines.append(f'Settings restored: {dest}')
        logger.info('Restored settings.py to %s', dest)
        n += 1
    env_snap = snap / '.env'
    if env_snap.is_file():
        dest_env = base.parent / '.env'
        shutil.copy2(env_snap, dest_env)
        log_lines.append(f'.env restored to {dest_env}')
        logger.info('Restored .env to %s', dest_env)
        n += 1
    return n


def restore_backup(archive_path):
    """
    Восстанавливает backup из .tar.gz архива.
    Отсутствующие database.sql / media не считаются ошибкой (частичный архив).
    Возвращает dict с log, tables_count, media_count, settings_count, duration_seconds.
    """
    archive_path = Path(archive_path)
    if not archive_path.exists():
        raise FileNotFoundError(f'Backup file not found: {archive_path}')

    start_time = time.time()
    log_lines = []
    tables_count = 0
    media_count = 0
    settings_count = 0

    db_settings = settings.DATABASES['default']
    media_root = Path(settings.MEDIA_ROOT)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        with tarfile.open(archive_path, 'r:gz') as tar:
            tar.extractall(tmpdir)

        backup_dir = tmpdir / 'backup'
        if not backup_dir.exists():
            raise ValueError('Invalid backup: missing backup/ directory')

        db_sql = backup_dir / 'database.sql'
        media_src = backup_dir / 'media'

        # 1. БД (опционально)
        if db_sql.exists() and db_sql.is_file():
            sql_content = db_sql.read_text(errors='ignore')
            tables_count = sql_content.count('CREATE TABLE') or sql_content.count('create table')

            connection.close()
            log_lines.append('Database connections closed.')

            env = os.environ.copy()
            env['PGPASSWORD'] = db_settings.get('PASSWORD', '')
            cmd = [
                'psql',
                '-h', db_settings.get('HOST', 'localhost'),
                '-p', str(db_settings.get('PORT', '5432')),
                '-U', db_settings.get('USER', 'postgres'),
                '-d', db_settings.get('NAME', ''),
                '-f', str(db_sql),
                '-v', 'ON_ERROR_STOP=1',
            ]
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=3600)
            if result.returncode != 0:
                logger.error('psql restore failed: %s', result.stderr or result.stdout)
                raise RuntimeError(f'Database restore failed: {result.stderr or result.stdout}')

            log_lines.append(f'Database restored. Tables (approx): {tables_count}')
            logger.info('Database restored successfully')
        else:
            log_lines.append('No database.sql in archive — database restore skipped.')
            logger.warning('No database.sql in backup; skipping database restore')

        # 2. Media (опционально)
        if media_src.exists() and media_src.is_dir():
            if media_root.exists():
                for item in media_root.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                log_lines.append('Media cleared before restore.')
            media_root.mkdir(parents=True, exist_ok=True)
            media_count = sum(1 for _ in media_src.rglob('*') if _.is_file())
            for item in media_src.iterdir():
                dest = media_root / item.name
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
            log_lines.append(f'Media restored: {media_count} files')
            logger.info('Media restored to %s', media_root)
        else:
            log_lines.append('No media directory in backup — media restore skipped.')
            logger.warning('No media directory in backup')

        # 3. Settings snapshot
        settings_count = _restore_settings_snapshot(backup_dir, log_lines)
        if settings_count == 0:
            log_lines.append('No settings_snapshot in backup or empty.')

    duration = round(time.time() - start_time, 1)
    log_lines.append(f'Duration: {duration}s')
    return {
        'log': '\n'.join(log_lines),
        'tables_count': tables_count,
        'media_count': media_count,
        'settings_count': settings_count,
        'duration_seconds': duration,
    }


class Command(BaseCommand):
    help = (
        'Restore database, media, and/or settings from a backup .tar.gz '
        '(partial archives without database.sql or media are supported).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'archive_path',
            type=str,
            help='Path to backup .tar.gz file',
        )
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        archive_path = Path(options['archive_path']).resolve()
        if not archive_path.exists():
            self.stderr.write(self.style.ERROR(f'File not found: {archive_path}'))
            return

        if not options['no_input']:
            confirm = input(
                'This may OVERWRITE the current database, media, and settings files. '
                'Type "yes" to continue: '
            )
            if confirm.lower() != 'yes':
                self.stdout.write('Restore cancelled.')
                return

        try:
            result = restore_backup(archive_path)
            self.stdout.write(self.style.SUCCESS('Restore completed successfully.'))
            self.stdout.write(f'Tables (approx): {result["tables_count"]}')
            self.stdout.write(f'Media files: {result["media_count"]}')
            self.stdout.write(f'Settings files: {result["settings_count"]}')
            self.stdout.write(f'Duration: {result["duration_seconds"]}s')
        except Exception as e:
            logger.exception('Restore failed: %s', e)
            self.stderr.write(self.style.ERROR(f'Restore failed: {e}'))
