# Remove public_avatar_url — avatar URL is not shown in public profile table

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('login', '0009_profile_public_visibility_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='public_avatar_url',
        ),
    ]
