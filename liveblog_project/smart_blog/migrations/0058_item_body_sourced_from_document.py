# Post body sourced from PDF/DOCX import (create flow).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0057_notification_from_admin"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="body_sourced_from_document",
            field=models.BooleanField(
                default=False,
                help_text="True if post body HTML was first filled from a PDF/DOCX import on create.",
            ),
        ),
    ]
