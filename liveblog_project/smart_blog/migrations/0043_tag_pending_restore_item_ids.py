# Store Item IDs when a Tag is soft-deleted so restore can re-link M2M.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0042_contentreport_unique_active_only"),
    ]

    operations = [
        migrations.AddField(
            model_name="tag",
            name="pending_restore_item_ids",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
