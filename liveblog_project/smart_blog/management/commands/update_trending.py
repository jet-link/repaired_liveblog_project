import signal
import time

from django.core.management.base import BaseCommand

from smart_blog.services.trending_service import (
    calculate_trending,
    rollup_item_stats_hourly_for_hour,
)


class Command(BaseCommand):
    help = (
        "Recalculate trending scores. Use --daemon to run on an interval without Celery "
        "(Ctrl+C to stop)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--rollup-hourly",
            action="store_true",
            help="Also run hourly rollup for the previous completed local hour (single run only).",
        )
        parser.add_argument(
            "--daemon",
            "-d",
            action="store_true",
            help="Keep running: recalculate trending every --interval seconds until stopped.",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=720,
            help="Seconds between runs in --daemon mode (default: 720 = 12 min, same as Celery beat).",
        )

    def handle(self, *args, **options):
        daemon = options["daemon"]
        interval = max(60, int(options["interval"]))

        def run_trending():
            written = calculate_trending()
            self.stdout.write(
                self.style.SUCCESS(f"TrendingItem rows updated: {written}")
            )
            return written

        if not daemon:
            if options["rollup_hourly"]:
                n = rollup_item_stats_hourly_for_hour()
                self.stdout.write(
                    self.style.SUCCESS(f"Hourly rollup rows upserted: {n}")
                )
            run_trending()
            return

        if options["rollup_hourly"]:
            self.stdout.write(
                "Running hourly rollup once at startup (--daemon loop only recalculates trending)."
            )
            n = rollup_item_stats_hourly_for_hour()
            self.stdout.write(
                self.style.SUCCESS(f"Hourly rollup rows upserted: {n}")
            )

        stop = False

        def _request_stop(*_args):
            nonlocal stop
            stop = True

        signal.signal(signal.SIGINT, _request_stop)
        signal.signal(signal.SIGTERM, _request_stop)

        self.stdout.write(
            self.style.WARNING(
                f"Daemon: trending every {interval}s (min 60). Ctrl+C to stop."
            )
        )

        while not stop:
            try:
                run_trending()
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"update_trending failed: {exc}"))

            for _ in range(interval):
                if stop:
                    break
                time.sleep(1)

        self.stdout.write(self.style.WARNING("Daemon stopped."))
