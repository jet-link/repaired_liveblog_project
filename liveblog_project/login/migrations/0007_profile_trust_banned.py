from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('login', '0006_add_trust_score'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='trust_banned',
            field=models.BooleanField(default=False, db_index=True),
        ),
    ]
