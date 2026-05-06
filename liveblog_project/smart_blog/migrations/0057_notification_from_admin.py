# Admin-authored inbox notifications (no post attachment).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0056_item_excerpt_plain_850"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="admin_body",
            field=models.TextField(blank=True, help_text="Message body for from_admin notifications"),
        ),
        migrations.AddField(
            model_name="notification",
            name="admin_theme",
            field=models.CharField(blank=True, max_length=200, help_text="Optional subject for from_admin notifications"),
        ),
        migrations.AlterField(
            model_name="notification",
            name="item",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="notifications",
                to="smart_blog.item",
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="notif_type",
            field=models.CharField(
                choices=[
                    ("reply", "Reply"),
                    ("item_like", "Liked item"),
                    ("comment_like", "Liked comment"),
                    ("from_admin", "From admin"),
                ],
                max_length=20,
            ),
        ),
    ]
