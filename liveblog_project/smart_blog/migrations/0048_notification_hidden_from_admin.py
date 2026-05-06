from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0047_add_trending_engagement_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="hidden_from_admin",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Hidden from the admin notifications list only; does not change recipient inbox.",
            ),
        ),
    ]
