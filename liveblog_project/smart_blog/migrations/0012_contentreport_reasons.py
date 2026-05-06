from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0011_notification"),
    ]

    operations = [
        migrations.AddField(
            model_name="contentreport",
            name="reasons",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
