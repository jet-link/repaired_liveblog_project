# Generated manually for include_database / include_media / include_settings

from django.db import migrations, models


def forwards_set_flags(apps, schema_editor):
    Backup = apps.get_model('backups', 'Backup')
    Backup.objects.all().update(
        include_database=True,
        include_media=True,
        include_settings=False,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0003_backup_improvements'),
    ]

    operations = [
        migrations.AddField(
            model_name='backup',
            name='include_database',
            field=models.BooleanField(default=True, verbose_name='Include database'),
        ),
        migrations.AddField(
            model_name='backup',
            name='include_media',
            field=models.BooleanField(default=True, verbose_name='Include media'),
        ),
        migrations.AddField(
            model_name='backup',
            name='include_settings',
            field=models.BooleanField(default=False, verbose_name='Include settings'),
        ),
        migrations.AlterField(
            model_name='backup',
            name='content_type',
            field=models.CharField(
                choices=[
                    ('database', 'Database'),
                    ('media', 'Media'),
                    ('database_media', 'Database + Media'),
                    ('full', 'Full (DB + Media + Settings)'),
                    ('settings', 'Settings only'),
                    ('mixed', 'Mixed selection'),
                ],
                default='database_media',
                max_length=20,
                verbose_name='Content',
            ),
        ),
        migrations.RunPython(forwards_set_flags, migrations.RunPython.noop),
    ]
