# Generated manually

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def forwards_link_deleted_logs(apps, schema_editor):
    DeletedUserLog = apps.get_model("admin_panel", "DeletedUserLog")
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(app_label, model_name)
    for log in DeletedUserLog.objects.filter(user__isnull=True).order_by("pk"):
        u = User.objects.filter(username=log.username).first()
        if not u:
            continue
        if DeletedUserLog.objects.filter(user=u).exclude(pk=log.pk).exists():
            continue
        log.user_id = u.pk
        log.save(update_fields=["user_id"])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("admin_panel", "0006_remove_assistantscheduledanalysis"),
    ]

    operations = [
        migrations.AddField(
            model_name="contentviolation",
            name="deleted_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="deleteduserlog",
            name="user",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="deleted_queue_entry",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(forwards_link_deleted_logs, migrations.RunPython.noop),
    ]
