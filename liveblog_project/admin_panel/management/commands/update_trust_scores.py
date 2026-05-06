"""
Update User Trust Scores (for cron or manual run).

Only recalculates users with violations in the last 30 days.
Use --all to recalculate all users with profiles (run after migrations).

Cron example:
  0 3 * * * cd /path && python manage.py update_trust_scores
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Recalculate trust scores for users. Use --all to process all users.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Recalculate for all users with profiles (default: only users with violations in last 30 days)',
        )

    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model
        from admin_panel.models import ContentViolation
        from admin_panel.services.trust_score_service import update_user_trust_score

        User = get_user_model()

        if options.get('all'):
            users = User.objects.filter(profile__isnull=False).distinct()
            total = users.count()
        else:
            cutoff = timezone.now() - timedelta(days=30)
            recovery_cutoff = timezone.now() - timedelta(days=90)
            # Users with recent violations OR with last_violation_at (need recovery calculation)
            users = User.objects.filter(
                profile__isnull=False
            ).filter(
                Q(items__content_violations__created_at__gte=cutoff)
                | Q(comments__content_violations__created_at__gte=cutoff)
                | Q(profile__last_violation_at__isnull=False, profile__last_violation_at__gte=recovery_cutoff)
            ).distinct()
            total = users.count()

        updated = 0
        for user in users:
            try:
                update_user_trust_score(user)
                updated += 1
            except Exception as e:
                self.stderr.write(f'Failed user {user.pk}: {e}')

        self.stdout.write(self.style.SUCCESS(f'Updated {updated}/{total} user trust scores.'))
