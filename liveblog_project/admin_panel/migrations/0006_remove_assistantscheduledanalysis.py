# Remove AssistantScheduledAnalysis (revert scheduled analysis feature)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("admin_panel", "0005_assistant_scheduled_analysis"),
    ]

    operations = [
        migrations.DeleteModel(
            name="AssistantScheduledAnalysis",
        ),
    ]
