from django.db import migrations, models
import django.db.models.deletion


def backfill_notification_types(apps, schema_editor):
    Notification = apps.get_model("smart_blog", "Notification")
    for n in Notification.objects.all():
        n.notif_type = "reply"
        if n.reply_comment_id:
            try:
                n.actor_id = n.reply_comment.author_id
            except Exception:
                n.actor_id = None
        n.save(update_fields=["notif_type", "actor"])


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0012_contentreport_reasons"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="actor",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sent_notifications", to="auth.user"),
        ),
        migrations.AddField(
            model_name="notification",
            name="notif_type",
            field=models.CharField(choices=[("reply", "Reply"), ("item_like", "Liked item"), ("comment_like", "Liked comment")], max_length=20, default="reply"),
        ),
        migrations.AlterField(
            model_name="notification",
            name="parent_comment",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="reply_notifications", to="smart_blog.comment"),
        ),
        migrations.AlterField(
            model_name="notification",
            name="reply_comment",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="smart_blog.comment"),
        ),
        migrations.RunPython(backfill_notification_types, migrations.RunPython.noop),
    ]
