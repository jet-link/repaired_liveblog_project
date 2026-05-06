# Generated manually for schedule_type field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='backup',
            name='schedule_type',
            field=models.CharField(
                choices=[
                    ('manual', 'Manual'),
                    ('daily', 'Daily'),
                    ('weekly', 'Weekly'),
                    ('monthly', 'Monthly'),
                ],
                default='manual',
                max_length=20,
                verbose_name='Schedule',
            ),
        ),
    ]
