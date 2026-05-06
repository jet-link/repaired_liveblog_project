# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("backups", "0004_backup_include_flags"),
    ]

    operations = [
        migrations.AddField(
            model_name="backup",
            name="deleted_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True, verbose_name="Deleted at"),
        ),
    ]
