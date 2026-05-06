# Store Item IDs when a Category is soft-deleted so restore can re-link FK.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0043_tag_pending_restore_item_ids"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="pending_restore_item_ids",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
