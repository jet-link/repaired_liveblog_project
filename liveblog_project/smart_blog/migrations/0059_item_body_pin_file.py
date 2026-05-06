# Store original pinned PDF/DOCX and plain snapshot for item detail.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0058_item_body_sourced_from_document"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="body_pin_original",
            field=models.FileField(
                blank=True,
                help_text="Original PDF/DOCX attached at create (shown on post detail).",
                max_length=500,
                null=True,
                upload_to="item_body_pins/%Y/%m/",
            ),
        ),
        migrations.AddField(
            model_name="item",
            name="body_pin_plain_snapshot",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Plain-text snapshot of the pinned document for faithful display (esp. DOCX).",
            ),
        ),
    ]
