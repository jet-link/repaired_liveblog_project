# Unique per item/comment only among non-deleted rows (soft-delete support)

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("admin_panel", "0007_deleteduserlog_user_violation_deleted_at"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="contentviolation",
            name="uq_violation_item",
        ),
        migrations.RemoveConstraint(
            model_name="contentviolation",
            name="uq_violation_comment",
        ),
        migrations.AddConstraint(
            model_name="contentviolation",
            constraint=models.UniqueConstraint(
                condition=Q(item__isnull=False, deleted_at__isnull=True),
                fields=("item",),
                name="uq_violation_item",
            ),
        ),
        migrations.AddConstraint(
            model_name="contentviolation",
            constraint=models.UniqueConstraint(
                condition=Q(comment__isnull=False, deleted_at__isnull=True),
                fields=("comment",),
                name="uq_violation_comment",
            ),
        ),
    ]
