# Generated for Reports system refactoring

from django.db import migrations, models
from django.db.models import Q


VALID_REASONS = {"spam", "abuse", "harassment", "copyright", "other"}


def migrate_reasons_to_reason(apps, schema_editor):
    """Copy reasons[0] to reason where reasons has values."""
    ContentReport = apps.get_model("smart_blog", "ContentReport")
    for obj in ContentReport.objects.all():
        reasons = getattr(obj, "reasons", None) or []
        if reasons and isinstance(reasons, list) and len(reasons) > 0:
            first = reasons[0]
            if first and first in VALID_REASONS:
                ContentReport.objects.filter(pk=obj.pk).update(reason=first)


def reverse_migrate(apps, schema_editor):
    """Reverse: reasons will be re-added as empty list; no data to restore."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0030_comment_is_draft"),
    ]

    operations = [
        migrations.AddField(
            model_name="contentreport",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.RunPython(migrate_reasons_to_reason, reverse_migrate),
        migrations.RemoveField(
            model_name="contentreport",
            name="reasons",
        ),
        migrations.AddConstraint(
            model_name="contentreport",
            constraint=models.UniqueConstraint(
                condition=Q(item__isnull=False),
                fields=("reporter", "item"),
                name="unique_user_item_report",
            ),
        ),
        migrations.AddConstraint(
            model_name="contentreport",
            constraint=models.UniqueConstraint(
                condition=Q(comment__isnull=False),
                fields=("reporter", "comment"),
                name="unique_user_comment_report",
            ),
        ),
        migrations.AddConstraint(
            model_name="contentreport",
            constraint=models.CheckConstraint(
                check=(
                    Q(item__isnull=False, comment__isnull=True)
                    | Q(item__isnull=True, comment__isnull=False)
                ),
                name="report_target_valid",
            ),
        ),
        migrations.AddIndex(
            model_name="contentreport",
            index=models.Index(fields=["item", "created_at"], name="smart_blog__item_id_8a1c95_idx"),
        ),
        migrations.AddIndex(
            model_name="contentreport",
            index=models.Index(fields=["comment", "created_at"], name="smart_blog__comment__b2e9f7_idx"),
        ),
        migrations.AddIndex(
            model_name="contentreport",
            index=models.Index(fields=["reporter", "created_at"], name="smart_blog__reporter_9d4c12_idx"),
        ),
    ]
