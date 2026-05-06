# Reporter+target uniqueness only for non-deleted reports (soft-delete)

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0041_notification_cleared_inbox_soft_delete"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="contentreport",
            name="unique_user_item_report",
        ),
        migrations.RemoveConstraint(
            model_name="contentreport",
            name="unique_user_comment_report",
        ),
        migrations.AddConstraint(
            model_name="contentreport",
            constraint=models.UniqueConstraint(
                condition=Q(item__isnull=False, deleted_at__isnull=True),
                fields=("reporter", "item"),
                name="unique_user_item_report",
            ),
        ),
        migrations.AddConstraint(
            model_name="contentreport",
            constraint=models.UniqueConstraint(
                condition=Q(comment__isnull=False, deleted_at__isnull=True),
                fields=("reporter", "comment"),
                name="unique_user_comment_report",
            ),
        ),
    ]
