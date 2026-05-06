# Backup improvements: backup_type, content_type, duration_seconds, integrity_status

from django.db import migrations, models


def set_backup_type_from_schedule(apps, schema_editor):
    Backup = apps.get_model('backups', 'Backup')
    for b in Backup.objects.all():
        b.backup_type = 'auto' if b.schedule_type in ('daily', 'weekly', 'monthly') else 'manual'
        b.content_type = 'database_media'
        b.save(update_fields=['backup_type', 'content_type'])


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0002_backup_schedule_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='backup',
            name='backup_type',
            field=models.CharField(
                choices=[
                    ('manual', 'Manual'),
                    ('auto', 'Auto'),
                    ('pre_deploy', 'Pre-deploy'),
                    ('pre_restore', 'Pre-restore'),
                ],
                default='manual',
                max_length=20,
                verbose_name='Backup type',
            ),
        ),
        migrations.AddField(
            model_name='backup',
            name='content_type',
            field=models.CharField(
                choices=[
                    ('database', 'Database'),
                    ('media', 'Media'),
                    ('database_media', 'Database + Media'),
                    ('full', 'Full system'),
                ],
                default='database_media',
                max_length=20,
                verbose_name='Content',
            ),
        ),
        migrations.AddField(
            model_name='backup',
            name='duration_seconds',
            field=models.FloatField(blank=True, null=True, verbose_name='Duration (sec)'),
        ),
        migrations.AddField(
            model_name='backup',
            name='integrity_status',
            field=models.CharField(
                choices=[
                    ('unknown', 'Unknown'),
                    ('verified', 'Verified'),
                    ('corrupted', 'Corrupted'),
                ],
                default='unknown',
                max_length=20,
                verbose_name='Integrity',
            ),
        ),
        migrations.AddField(
            model_name='backup',
            name='restore_log',
            field=models.TextField(blank=True, verbose_name='Restore log'),
        ),
        migrations.RunPython(set_backup_type_from_schedule, migrations.RunPython.noop),
    ]
