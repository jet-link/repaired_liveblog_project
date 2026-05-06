# Add STATUS_IGNORED choice to ContentReport (no schema change - choices only)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0033_contentreport_reasons"),
    ]

    operations = [
        # No schema change - STATUS_CHOICES updated in model only.
        # The CharField accepts "ignored" as valid value.
    ]
