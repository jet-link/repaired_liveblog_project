# Generated manually for Reports Clear soft hide

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smart_blog', '0036_backfill_null_search_vector'),
    ]

    operations = [
        migrations.AddField(
            model_name='contentreport',
            name='admin_hidden',
            field=models.BooleanField(default=False),
        ),
    ]
