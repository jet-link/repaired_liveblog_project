# Generated manually for Profile public visibility flags

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('login', '0008_alter_profile_trust_banned'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='public_username',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='public_first_name',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='public_last_name',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='public_email',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='public_avatar_url',
            field=models.BooleanField(default=True),
        ),
    ]
