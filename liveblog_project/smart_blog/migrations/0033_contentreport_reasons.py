# Add reasons JSONField to store multiple report reasons

from django.db import migrations, models


def populate_reasons_from_reason(apps, schema_editor):
    """Populate reasons from existing reason field."""
    ContentReport = apps.get_model("smart_blog", "ContentReport")
    for obj in ContentReport.objects.all():
        if obj.reason:
            ContentReport.objects.filter(pk=obj.pk).update(reasons=[obj.reason])


def reverse_populate(apps, schema_editor):
    """Reverse: reasons removed; no need to restore reason (it stays)."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0032_rename_smart_blog__item_id_8a1c95_idx_smart_blog__item_id_8200be_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="contentreport",
            name="reasons",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(populate_reasons_from_reason, reverse_populate),
    ]
