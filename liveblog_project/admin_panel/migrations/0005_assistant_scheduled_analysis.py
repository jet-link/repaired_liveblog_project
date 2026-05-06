# Generated manually for AssistantScheduledAnalysis

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("admin_panel", "0004_add_started_by_to_analysis_run"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssistantScheduledAnalysis",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("run_at", models.DateTimeField()),
                (
                    "content_schedule",
                    models.CharField(default="now", max_length=20),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "scheduled_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assistant_scheduled_analyses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Assistant scheduled analysis",
                "verbose_name_plural": "Assistant scheduled analyses",
            },
        ),
    ]
