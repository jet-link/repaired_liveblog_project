from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0010_contentreport"),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="smart_blog.item")),
                ("parent_comment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reply_notifications", to="smart_blog.comment")),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="auth.user")),
                ("reply_comment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="smart_blog.comment")),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
    ]
