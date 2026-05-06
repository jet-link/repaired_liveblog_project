"""
Content moderation analysis (for cron or manual run).

Usage:
  python manage.py content_analyze              # Check now (all content)
  python manage.py content_analyze --schedule hourly
  python manage.py content_analyze --schedule daily
  python manage.py content_analyze --no-ai      # Skip OpenAI layer (deterministic only)

Cron examples:
  0 * * * * cd /path && python manage.py content_analyze --schedule hourly
  0 2 * * * cd /path && python manage.py content_analyze --schedule daily
"""
from django.core.management.base import BaseCommand

from admin_panel.services.content_analyzer import run_content_analysis


class Command(BaseCommand):
    help = 'Run content moderation analysis. --schedule hourly|daily for time-filtered runs.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--schedule',
            type=str,
            choices=['now', 'hourly', 'daily'],
            default='now',
            help='Schedule: now (all), hourly (last 1h), daily (last 24h)',
        )
        parser.add_argument(
            '--no-ai',
            action='store_true',
            help='Disable OpenAI moderation layer; run only deterministic checks (words/regex/abuse).',
        )

    def handle(self, *args, **options):
        schedule = options.get('schedule', 'now')
        use_ai = None if not options.get('no_ai') else False

        def log(msg):
            self.stdout.write(msg)

        run = run_content_analysis(schedule=schedule, log_callback=log, use_ai=use_ai)
        self.stdout.write(
            self.style.SUCCESS(f'Analysis {run.status}: {run.progress}%')
        )
