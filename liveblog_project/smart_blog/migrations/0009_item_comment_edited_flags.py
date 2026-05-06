from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("smart_blog", "0008_comment_updated"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="edited",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="comment",
            name="edited",
            field=models.BooleanField(default=False),
        ),
    ]
