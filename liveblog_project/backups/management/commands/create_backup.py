"""
Создание backup через management command (для cron).

Запуск:
  python manage.py create_backup                    # manual backup
  python manage.py create_backup --schedule daily   # daily (для cron)
  python manage.py create_backup --schedule weekly   # weekly
  python manage.py create_backup --schedule monthly # monthly

Примеры cron (ежедневно в 2:00, еженедельно в воскресенье в 3:00, ежемесячно 1-го в 4:00):
  0 2 * * * cd /path/to/project && python manage.py create_backup --schedule daily
  0 3 * * 0 cd /path/to/project && python manage.py create_backup --schedule weekly
  0 4 1 * * cd /path/to/project && python manage.py create_backup --schedule monthly
"""
from django.core.management.base import BaseCommand

from backups.models import Backup
from backups.services import create_backup_scheduled


class Command(BaseCommand):
    help = 'Create a backup (for manual use or cron). Use --schedule daily|weekly|monthly for scheduled backups.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--schedule',
            type=str,
            choices=['daily', 'weekly', 'monthly'],
            default=None,
            help='Schedule type for cron: daily, weekly, or monthly',
        )

    def handle(self, *args, **options):
        schedule = options.get('schedule')
        if schedule:
            backup = create_backup_scheduled(schedule=schedule)
            self.stdout.write(self.style.SUCCESS(f'Scheduled backup started: {backup.name} ({schedule})'))
        else:
            backup = create_backup_scheduled(schedule=Backup.SCHEDULE_MANUAL)
            self.stdout.write(self.style.SUCCESS(f'Backup started: {backup.name}'))
