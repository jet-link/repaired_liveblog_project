from django.core.management.base import BaseCommand
from django.db.models import Q

from smart_blog.image_utils import regenerate_item_image_variants
from smart_blog.models import ItemImage


class Command(BaseCommand):
    help = (
        "Regenerate ItemImage thumbnail, medium, and feed WebP variants from stored large images. "
        "Use after adding image_feed or when variants are missing."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--missing-feed-only",
            action="store_true",
            help="Only process rows without image_feed (default: also rows missing thumbnail or medium).",
        )
        parser.add_argument(
            "--item-id",
            type=int,
            default=None,
            help="Limit to a single post (Item.pk).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Max number of images to process.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List candidates without writing files.",
        )

    def handle(self, *args, **options):
        qs = ItemImage.objects.exclude(image="").filter(image__isnull=False)
        if options["item_id"]:
            qs = qs.filter(item_id=options["item_id"])

        if options["missing_feed_only"]:
            qs = qs.filter(Q(image_feed="") | Q(image_feed__isnull=True))
        else:
            qs = qs.filter(
                Q(image_feed="")
                | Q(image_feed__isnull=True)
                | Q(image_thumbnail="")
                | Q(image_thumbnail__isnull=True)
                | Q(image_medium="")
                | Q(image_medium__isnull=True)
            )

        qs = qs.order_by("pk")
        if options["limit"]:
            qs = qs[: int(options["limit"])]

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No ItemImage rows need regeneration."))
            return

        self.stdout.write(f"Candidates: {total}")
        ok = 0
        failed = 0
        skipped = 0

        for img in qs.iterator(chunk_size=50):
            if options["dry_run"]:
                self.stdout.write(f"  would regenerate ItemImage pk={img.pk} item_id={img.item_id}")
                ok += 1
                continue
            if regenerate_item_image_variants(img):
                ok += 1
                if ok % 25 == 0:
                    self.stdout.write(f"  … {ok}/{total}")
            else:
                failed += 1
                self.stderr.write(
                    self.style.WARNING(f"  failed ItemImage pk={img.pk} item_id={img.item_id}")
                )

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"Dry run: {ok} image(s) would be processed."))
            return

        self.stdout.write(
            self.style.SUCCESS(f"Done: {ok} regenerated, {failed} failed, {skipped} skipped.")
        )
