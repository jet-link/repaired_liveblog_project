"""
Автоматическая деактивация пользователей, не заходивших на сайт более года.
Посты, комментарии и лайки остаются в БД (soft delete: is_active=False).

Запуск: python manage.py deactivate_inactive_users
Рекомендуется добавить в cron для ежедневного выполнения.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class Command(BaseCommand):
    help = 'Деактивирует пользователей, не заходивших более года (soft delete)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать, кого бы деактивировали, без изменений',
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=365)
        dry_run = options['dry_run']

        # last_login < cutoff ИЛИ (last_login пусто И date_joined < cutoff)
        to_deactivate = User.objects.filter(
            is_active=True,
        ).exclude(
            is_staff=True,
        ).exclude(
            is_superuser=True,
        ).filter(
            Q(last_login__lt=cutoff) | Q(last_login__isnull=True, date_joined__lt=cutoff)
        )

        count = to_deactivate.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('Нет пользователей для деактивации.'))
            return

        if dry_run:
            self.stdout.write(f'[DRY-RUN] Деактивировали бы {count} пользователей:')
            for u in to_deactivate[:20]:
                last = u.last_login.strftime('%Y-%m-%d') if u.last_login else 'никогда'
                self.stdout.write(f'  - {u.username} (last_login: {last})')
            if count > 20:
                self.stdout.write(f'  ... и ещё {count - 20}')
            return

        updated = to_deactivate.update(is_active=False)
        self.stdout.write(self.style.SUCCESS(f'Деактивировано пользователей: {updated}'))
