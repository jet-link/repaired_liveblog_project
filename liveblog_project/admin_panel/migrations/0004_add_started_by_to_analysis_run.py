# Generated for started_by on AnalysisRun

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("admin_panel", "0003_add_violation_severity_confidence"),
    ]

    operations = [
        migrations.AddField(
            model_name="analysisrun",
            name="started_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="analysis_runs",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
