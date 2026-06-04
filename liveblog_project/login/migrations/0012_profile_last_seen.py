from django.conf import settings
from django.db import migrations, models


def backfill_last_seen_from_last_login(apps, schema_editor):
    Profile = apps.get_model("login", "Profile")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    for profile in Profile.objects.select_related("user").iterator(chunk_size=500):
        user = profile.user
        if user.last_login and not profile.last_seen:
            profile.last_seen = user.last_login
            profile.save(update_fields=["last_seen"])


class Migration(migrations.Migration):

    dependencies = [
        ("login", "0011_avatar_upload_path"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="last_seen",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text="Last site activity (updated while user is browsing; month shown in admin).",
                null=True,
            ),
        ),
        migrations.RunPython(
            backfill_last_seen_from_last_login,
            migrations.RunPython.noop,
        ),
    ]
