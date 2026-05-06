# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0040_rename_smart_blog__hour_st_0a0b8c_idx_smart_blog__hour_st_d8e89f_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="cleared_from_inbox",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Hidden from the recipient inbox but kept for deduplication when likes/replies repeat.",
            ),
        ),
        migrations.AddField(
            model_name="item",
            name="deleted_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="comment",
            name="deleted_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="tag",
            name="deleted_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="category",
            name="deleted_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="contentreport",
            name="deleted_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
