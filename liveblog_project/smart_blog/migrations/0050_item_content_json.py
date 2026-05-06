# Generated manually for Post Studio (Editor.js) — additive field, legacy HTML `text` unchanged.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0049_alter_notification_hidden_from_admin_help"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="content_json",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
