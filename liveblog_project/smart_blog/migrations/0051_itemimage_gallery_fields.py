# Generated manually for editorial gallery: ordering, caption, orientation hint.

from collections import defaultdict

from django.db import migrations, models


def backfill_sort_and_orientation(apps, schema_editor):
    ItemImage = apps.get_model("smart_blog", "ItemImage")

    def kind(w, h):
        if not w or not h:
            return "landscape"
        try:
            w, h = int(w), int(h)
        except (TypeError, ValueError):
            return "landscape"
        if h <= 0:
            return "landscape"
        r = w / h
        if r >= 2.0:
            return "wide"
        if r <= 0.82:
            return "portrait"
        if 0.88 <= r <= 1.12:
            return "square"
        return "landscape"

    by_item = defaultdict(list)
    for img in ItemImage.objects.all().order_by("item_id", "pk"):
        by_item[img.item_id].append(img)
    for _item_id, imgs in by_item.items():
        for i, img in enumerate(imgs):
            ItemImage.objects.filter(pk=img.pk).update(
                sort_order=i,
                orientation_kind=kind(img.width, img.height),
            )


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0050_item_content_json"),
    ]

    operations = [
        migrations.AddField(
            model_name="itemimage",
            name="caption",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="itemimage",
            name="orientation_kind",
            field=models.CharField(
                choices=[
                    ("landscape", "Landscape"),
                    ("portrait", "Portrait"),
                    ("wide", "Ultra-wide"),
                    ("square", "Square"),
                ],
                default="landscape",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="itemimage",
            name="sort_order",
            field=models.PositiveSmallIntegerField(db_index=True, default=0),
        ),
        migrations.AlterModelOptions(
            name="itemimage",
            options={"ordering": ("sort_order", "pk")},
        ),
        migrations.RunPython(backfill_sort_and_orientation, migrations.RunPython.noop),
    ]
