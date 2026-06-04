from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0062_alter_notification_notif_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="itemimage",
            name="image_feed",
            field=models.ImageField(blank=True, null=True, upload_to="items/"),
        ),
    ]
